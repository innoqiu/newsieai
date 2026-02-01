import asyncio
import json
import os
from typing import Any, Dict, List, Optional
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any



from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage

# MCP & Model Imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from .accountant import run_accountant_service
# Import accountant agent for payment handling
# from accountant import run_accountant_service
TWITTER_API_KEY = "new1_e035362729464976a75a6630453aab76"
BASE_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"

load_dotenv()




def extract_media_urls(tweet: Dict[str, Any]) -> List[str]:
    """
    从 tweet 中提取可直链下载的媒体 URL
    """
    media_urls = []

    entities = tweet.get("extendedEntities", {})
    for media in entities.get("media", []):
        url = media.get("media_url_https")
        if url:
            media_urls.append(url)

    return media_urls


def extract_tweet_items(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    遍历 raw["results"]["tweets"]，提取 tweet + quoted_tweet 信息
    """
    items = []
    print(f"+" *50)
    print(f"getting now")
    tweets = raw.get("results", {}).get("tweets", [])
    print(f"=" *50)
    print(f"\nTweets: {tweets}")
    for tweet in tweets:
        try:
            # 原 tweet
            url = tweet.get("twitterUrl")
            author = tweet.get("author", {}).get("name")
            text = tweet.get("text")
            created_at = tweet.get("createdAt")

            # quoted tweet（可能不存在 or 是字符串 "None"）
            quoted = tweet.get("quoted_tweet")
            if isinstance(quoted, dict):
                quoted_text = quoted.get("text")
                quoted_author = quoted.get("author", {}).get("name")
            else:
                quoted_text = None
                quoted_author = None

            # 媒体（主 tweet + quoted tweet）
            media_urls = extract_media_urls(tweet)
            if isinstance(quoted, dict):
                media_urls.extend(extract_media_urls(quoted))

            item = {
                "url": url,
                "author": author,
                "text": text,
                "created_at": created_at,
                "quoted_author": quoted_author,
                "quoted_text": quoted_text,
                "media_urls": media_urls,
            }

            items.append(item)

        except Exception as e:
            print(f"Error parsing tweet {tweet.get('id')}: {e}")
            continue

    return items

class NewsRetrievalAgent:
    """
    Agent for retrieving news based on query and user context using MCP tools.
    """
    
    def __init__(self, user_context: Dict[str, Any], query_body: str):
        """
        Initialize the news retrieval agent.
        
        Args:
            user_context: User profile data containing preferences, interests, etc.
            query_body: The search query/topic to retrieve news for
        """
        self.user_context = user_context
        self.query_body = query_body
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7
        )
        # self.mcp_client: Optional[MultiServerMCPClient] = None
        self.mcp_client = None
        self.agent_runnable = None # Renamed from agent_executor
        
    async def setup_mcp_client(self):
        """Setup MCP client connection to the retrieval tools"""
        mcp_servers = {
            "retrieval_tools": {
                "url": f"http://localhost:{os.getenv('SEARCH_HTTP_PORT', '8001')}/mcp",
                "transport": "streamable-http"
            }
        }
        
        self.mcp_client = MultiServerMCPClient(mcp_servers)
        
    async def create_news_agent(self):
        """Create the LangGraph agent with MCP tools"""
        if not self.mcp_client:
            await self.setup_mcp_client()
        
        # Get tools from MCP client
        tools = await self.mcp_client.get_tools()
        
        # Create the system prompt
        # Note: In LangGraph, we pass this as 'state_modifier' or 'messages_modifier'
        system_prompt = """
            You are a news retrieval and structuring agent with access to multiple news sources.

            Your task is NOT to write prose summaries.
            Your task is to COLLECT, NORMALIZE, FILTER, and STRUCTURE news items.

            ## AVAILABLE TOOLS:
            You have access to the following MCP tools for news retrieval:

            1. **`twitter_advanced_search`**: Search X (Twitter) for tweets matching specific criteria
               - Use for: Real-time social media content, trending topics, user mentions
               - Parameters: keywords, exact_phrase, from_accounts, excluded_keywords, language, date ranges, engagement metrics
               - Returns: Structured tweet items with url, author, text, created_at, quoted_author, quoted_text, media_urls

            2. **`get_market_news`**: Search for market/financial news from Alpha Vantage
               - Use for: Stock market news, financial updates, company news, economic indicators
               - Parameters: query (context), tickers (stock symbols like "AAPL"), topics (e.g., "technology", "ipo")
               - Returns: Formatted news articles with title, summary, url, source, time_published

            3. **`get_bitcoin_news`**: Search for Bitcoin-specific news from bitserver
               - Use for: Bitcoin news, cryptocurrency updates, blockchain developments
               - Parameters: query (context), topics, auth_token (for paid content)
               - Returns: Formatted news articles or payment required JSON if 402

            4. **`get_web3_news`**: Search for Web3 news (if available)
               - Use for: Web3, DeFi, NFT, blockchain ecosystem news
               - Parameters: query, topics

            ## YOUR WORKFLOW:

            1. **Analyze the Query**: Understand what news the user is requesting based on `query_body`.
               - Extract key topics, keywords, entities, and search intent
               - Determine which tools are most appropriate for this query

            2. **Consider User Context**: Review `user_context` for strong preferences that should influence filtering:
               - User interests (e.g., "interested in AI and crypto")
               - Content preferences (e.g., "prefers technology news", "doesn't like sports")
               - Notification preferences, timezone, X usernames they follow
               - Description items that indicate strong preferences
               - **IMPORTANT**: Only apply filtering if user_context STRONGLY suggests a clear preference
               - If user_context is vague or neutral, don't over-filter - return relevant results

            3. **Execute Search Automatically**:
               - Call the appropriate tool(s) based on the query
               - You may call multiple tools if the query spans different news sources
               - Use tool parameters to refine the search based on query_body
               - If user_context suggests strong preferences, use excluded_keywords or topic filters

            4. **Filter Results** (if user_context strongly suggests preferences):
               - If user_context indicates strong dislikes (e.g., "doesn't like sports news"), exclude those topics
               - If user_context indicates strong interests (e.g., "interested in AI"), prioritize or filter to those topics
               - Only filter if the preference is CLEAR and STRONG - don't filter on vague preferences
               - If filtering, you can use excluded_keywords in twitter_advanced_search or topic filters in other tools

            5. **Structure Results**: Convert all retrieved news into structured item objects.
               - Each distinct news piece = one item
               - Follow the exact schema below
               - Append all items to a single list

            ## ITEM SCHEMA:

            Each item MUST strictly follow this schema:

            item = {
                "url": string,                     # link to the original tweet or article
                "author": string | null,            # author name if available
                "text": string | null,              # main text/content (title + summary for articles, text for tweets)
                "created_at": string | null,        # publication time
                "quoted_author": string | null,     # quoted author's name (if applicable, mainly for tweets)
                "quoted_text": string | null,       # quoted content (if applicable, mainly for tweets)
                "media_urls": list[string]          # direct media URLs (may be empty)
            }

            ## RULES:
            - One news piece = one item.
            - DO NOT merge multiple news into one item.
            - DO NOT invent fields or add extra keys.
            - Missing data MUST be set to null or an empty list.
            - DO NOT output explanations, markdown, or commentary.
            - DO NOT output summaries in natural language.
            - For articles from get_market_news or get_bitcoin_news: Use title as text, include summary if available
            - For tweets from twitter_advanced_search: Use the tweet text directly

            ## FINAL OUTPUT REQUIREMENTS:
            - Your final response MUST be a single JSON object:
            {
                "items": [ item, item, ... ]
            }

            ## CRITICAL EXCEPTION HANDLING:
            If ANY tool returns a JSON string containing "__402_payment_required__",
            YOU MUST STOP IMMEDIATELY.
            Do NOT summarize.
            Do NOT explain.
            Your final response must be EXACTLY the JSON string returned by the tool.

            ## EXAMPLES:

            Example 1: Query = "AI developments", User Context = {"interests": ["technology", "AI"]}
            - Call twitter_advanced_search with keywords=["AI", "artificial intelligence"]
            - Call get_market_news with topics="technology"
            - Filter: None needed (user already interested in AI)
            - Return all relevant AI news

            Example 2: Query = "latest news", User Context = {"description": ["doesn't like sports news"]}
            - Call appropriate tools for general news
            - Use excluded_keywords=["sports", "football", "basketball"] in twitter_advanced_search
            - Filter out sports-related results

            Example 3: Query = "cryptocurrency updates", User Context = {"interests": ["crypto"]}
            - Call get_bitcoin_news with topics related to crypto
            - Call twitter_advanced_search with keywords=["crypto", "bitcoin", "ethereum"]
            - Return all crypto-related news
            """
        
        # --- FIXED: Use LangGraph Prebuilt Agent ---
        # This replaces the old create_react_agent + AgentExecutor pattern
        self.agent_runnable = create_agent(
            self.llm, 
            tools, 
            system_prompt=system_prompt
        )
        
    async def run(self, user_profile: Optional[Dict[str, Any]] = None) -> str:
        """
        Run the agent with the provided query and user context.
        
        Args:
            user_profile: Optional user profile for payment decisions if 402 is encountered
        """
        if not self.agent_runnable:
            await self.create_news_agent()
        
        # Format user context for the prompt
        user_context_str = json.dumps(self.user_context, indent=2) if self.user_context else "No user context provided"
        
        # Create the input message with query and user context
        user_input = f"""Search for news based on the following query:

QUERY: {self.query_body}

USER CONTEXT (for filtering preferences):
{user_context_str}

Please automatically search for relevant news using the available tools and return structured results.
If the user context strongly suggests clear preferences (e.g., strong dislikes or specific interests), apply appropriate filtering.
Otherwise, return all relevant results for the query."""
        
        # --- FIXED: Run the Graph ---
        # LangGraph takes a dictionary with "messages" key
        inputs = {"messages": [HumanMessage(content=user_input)]}
        
        # ainvoke returns the final state of the graph
        result = await self.agent_runnable.ainvoke(inputs)
        agent_response = result["messages"][-1].content
        
        print(f"DEBUG: Raw Agent Response: {agent_response}")

        payment_info = agent_response.strip()
        

        # 1) 先把 response 归一化成 dict
        # if isinstance(agent_response, dict):
        #     data = agent_response
        # elif isinstance(agent_response, str):
        #     s = agent_response.strip()
        #     while s.endswith("}}"):
        #         s = s[:-1]
        #     try:
        #         data = json.loads(s)   # JSON -> dict
        #         print(f"DEBUG: JSON decode successful\n")
        #         print(f"DEBUG: JSON data: {data}")
        #     except json.JSONDecodeError as e:
        #         print(f"DEBUG: JSONDecodeError at pos={e.pos}, lineno={e.lineno}, colno={e.colno}: {e.msg}")
        #         start = max(0, e.pos - 60)
        #         end = min(len(s), e.pos + 60)
        #         print("DEBUG: Context around error:")
        #         print(s[start:end])
        #         raise
        # else:
        #     print(f"DEBUG:⚠Unknown response type: {type(agent_response)}")
        #     data = None

        # # 2) 从 dict 里取 payment_info
        # if isinstance(data, dict):
        #     payment_info = data.get("payment_data", {}).get("payment_info")
        #     print(f"DEBUG: Payment info: {payment_info}")
      
        # Check if we successfully extracted payment info
        if payment_info:
            print("DEBUG: 402 Flag Detected. Triggering Payment Handler.")
            return await self._handle_payment_required(payment_info, user_profile)
        return agent_response
    
    async def _handle_payment_required(
        self, payment_info: str,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Handle 402 Payment Required response by delegating to accountant agent.
        
        Args:
            payment_data: Payment data from the 402 response
            user_profile: User profile for payment decision
            url: Original URL that requires payment
        
        Returns:
            Content retrieved by accountant agent, or rejection message
        """
        print("\n" + "="*50)
        print("402 PAYMENT REQUIRED DETECTED")
        print("="*50)        
        # Default user profile if not provided
        if not user_profile:
            user_profile = {
                "user_id": "default_guest",
                "tier": "standard",
                "custom_budget_limit": 0.1,  # Default 0.1 SOL
                "preference": "user has a neutral preference for news content"
            }
        # Delegate entire payment and content retrieval to accountant agent
        print("\nDelegating payment evaluation and content retrieval to Accountant Agent...")
        result = await run_accountant_service(payment_info, user_profile)
        
        return result
    
    async def cleanup(self):
        """Cleanup MCP client connection"""
        if self.mcp_client:
            # MultiServerMCPClient may not have a disconnect method
            # Try to clean up gracefully if the method exists
            try:
                await self.mcp_client.disconnect()
            except AttributeError:
                # disconnect() method doesn't exist - this is fine, cleanup happens automatically
                pass
            except Exception:
                # Ignore any other cleanup errors
                pass

def search_x_usernames(x_usernames: List[str]) -> str:
    print(f"checking time...")
    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)
    since_str = since_24h.strftime("%Y-%m-%d_%H:%M:%S_UTC")
    print(f"Full query: {since_str}")
    

    #  构造 query 子句，例如：from:elonmusk OR from:another
    # 移除开头的 '@'
    users = [u.lstrip("@") for u in x_usernames]
    user_query = " OR ".join([f"from:{u}" for u in users])

    full_query = f"{user_query} since:{since_str}"
    print(f"Full query: {full_query}")
    # 发起请求
    try:
        headers = {"X-API-Key": TWITTER_API_KEY}
        params = {"query": full_query, "queryType": "Latest"}
        print(f"Params: {params},base_url: {BASE_URL},headers: {headers}")
        response = requests.get(BASE_URL, headers=headers, params=params)
        print(f"Got Response: {response.json()}")
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

    # 4️⃣ 结构化输出
    # API 原样返回 tweets[], has_next_page 等字段。
    return {
        "queried_users": x_usernames,
        "query": full_query,
        "results": data,
    }
#外界调用函数，调用retriv_run_agent时，传入user_context，query_body，user_profile
async def retriv_run_agent(
    user_context: Dict[str, Any],
    query_body: str,
    user_profile: Optional[Dict[str, Any]] = None
) -> str:
    """
    Convenience function to run the news retrieval agent.
    
    Args:
        user_context: User profile data containing preferences, interests, etc. (for filtering)
        query_body: The search query/topic to retrieve news for
        user_profile: Optional user profile for payment decisions if 402 is encountered
    """
    # Create and run the agent
    agent = NewsRetrievalAgent(user_context, query_body)
    try:
        result = await agent.run(user_profile=user_profile)
        return result
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    # Example usage
    user_context = {
        "interests": ["technology", "AI"],
        "description": ["interested in artificial intelligence and machine learning"]
    }
    query_body = "Search for news about Apple Inc. (AAPL) and recent technology developments"
    result = asyncio.run(retriv_run_agent(user_context, query_body))
    print("\n" + "="*50)
    print("AGENT RESPONSE:")
    print("="*50)
    print(result)