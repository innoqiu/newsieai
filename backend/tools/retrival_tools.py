from dotenv import load_dotenv
import requests
import os
import json
from fastmcp import FastMCP
import logging
from typing import Any, Dict, List, Optional
from sources import StockNews
from sources import BitcoinNews
from sources import PaymentRequiredException
from datetime import datetime, timedelta
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
BASE_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"
# Optional import for Web3News if it exists
try:
    from sources import Web3News
except ImportError:
    Web3News = None


logger = logging.getLogger(__name__)
mcp = FastMCP()
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

@mcp.tool()
def get_web3_news(
    query: Optional[str] = None,
    topics: Optional[str] = None
) -> str:
    """
    Search for web3 news articles from Alpha Vantage.
    """
    return "This is a test news tool"

@mcp.tool()
def get_bitcoin_news(
    query: Optional[str] = None,
    topics: Optional[str] = None,
    auth_token: Optional[str] = None
) -> str:
    """
    Search for bitcoin news articles from bitserver.
    Do not use this tool to search for news articles that are not related to bitcoin.
    
    Args:
        query: Optional search query description (for context)
        topics: Optional topics filter
        auth_token: Optional authorization token (transaction hash) for paid content
    
    Returns:
        Formatted string containing news articles, or JSON string with payment data if 402
    """
    try:
        bitcoin_news = BitcoinNews()
        news = bitcoin_news.retrive_news(auth_token=auth_token)
        
        if not news:
            return "No bitcoin news articles found for the given criteria."
        
        # Format the news articles
        result = f"Found {len(news)} bitcoin news articles:\n\n"
        for i, article in enumerate(news, 1):
            title = article.get("title", "No title")
            summary = article.get("summary", "No summary available")
            url = article.get("url", "")
            source = article.get("source", "Unknown")
            time_published = article.get("time_published", "")
            
            result += f"{i}. {title}\n"
            result += f"   Source: {source}\n"
            if time_published:
                result += f"   Published: {time_published}\n"
            result += f"   Summary: {summary}\n"
            if url:
                result += f"   URL: {url}\n"
            result += "\n"
        
        return result
    except PaymentRequiredException as e:
        # Return payment data as JSON string that can be detected
        # Include the URL so we can retry after payment
        payment_response = {
            "__402_payment_required__": True,
            "payment_data": e.payment_data,
            "source": "bitserver",
            "url": bitcoin_news.base_url  # Include URL for retry
        }
        return json.dumps(payment_response, ensure_ascii=False)
    except Exception as e:
        return f"Error fetching bitcoin news: {str(e)}"

@mcp.tool()
def twitter_advanced_search(
    keywords: Optional[List[str]] = None,
    exact_phrase: Optional[str] = None,
    excluded_keywords: Optional[List[str]] = None,
    from_accounts: Optional[List[str]] = None,
    to_accounts: Optional[List[str]] = None,
    mentioning_accounts: Optional[List[str]] = None,
    language: Optional[str] = None,
    since_date: Optional[str] = None,
    until_date: Optional[str] = None,
    min_replies: Optional[int] = None,
    min_likes: Optional[int] = None,
    min_retweets: Optional[int] = None,
    has_links: Optional[bool] = None,
    has_media: Optional[bool] = None,
    query_type: str = "Latest",
    cursor: str = ""
) -> Dict[str, Any]:
    """
    Execute a sophisticated search on X (Twitter) using the Advanced Search API.
    You don't have to use all the parameters, The tool works fine even only one parameter is provided. you can use only the ones that are relevant to the query.
    INSTRUCTIONS FOR THE AGENT:
    - keywords: A list of words where tweets must contain all or any. Use this for general topics.
    - exact_phrase: A specific string that must appear exactly as written.
    - excluded_keywords: Tweets containing these words will be filtered out.
    - from_accounts: List of usernames (with or without '@') whose tweets you want to retrieve.
    - to_accounts: List of usernames to whom the tweets were addressed.
    - mentioning_accounts: List of usernames mentioned in the tweets.
    - language: ISO 639-1 code (e.g., 'en', 'zh', 'ja').
    - since_date / until_date: Format 'YYYY-MM-DD' or 'YYYY-MM-DD_HH:MM:SS_UTC'. 
    - min_replies / min_likes / min_retweets: Minimum engagement thresholds (integer).
    - has_links: Set True to only show tweets with URLs, False to exclude them.
    - has_media: Set True to only show tweets with images or videos.
    - query_type: Choose 'Latest' for recent tweets or 'Top' for popular tweets.
    
    USAGE STRATEGY
    1. this tool handles the query in 'AND' logic. if you input a list of keywords, the tweets return will contain all the keywords. if you input a keyword and a from_username, the tweets return will only from that user and related to the keyword.
    2. If you want search multiple users or topics that are not related to each other, you can use the tool multiple times. Each as a separate query.
    """

    if not TWITTER_API_KEY:
        return {"error": "TWITTER_API_KEY not found in environment variables."}

    query_parts = []

    # 1. Exact Phrase (e.g., "artificial intelligence")
    if exact_phrase:
        query_parts.append(f'"{exact_phrase.strip()}"')

    # 2. Keywords (AND logic by default in Twitter search)
    if keywords:
        # Filter out empty strings and handle multi-word keywords with quotes
        valid_keywords = []
        for k in keywords:
            k = k.strip()
            if " " in k and not k.startswith('"'):
                valid_keywords.append(f'"{k}"')
            else:
                valid_keywords.append(k)
        if valid_keywords:
            query_parts.append(" ".join(valid_keywords))

    # 3. Excluded Keywords (-keyword)
    if excluded_keywords:
        for ek in excluded_keywords:
            ek = ek.strip()
            if ek:
                query_parts.append(f"-{ek}")

    # 4. Accounts (From, To, Mentioning)
    if from_accounts:
        users = " OR ".join([f"from:{u.lstrip('@').strip()}" for u in from_accounts if u.strip()])
        query_parts.append(f"({users})")
    
    if to_accounts:
        users = " OR ".join([f"to:{u.lstrip('@').strip()}" for u in to_accounts if u.strip()])
        query_parts.append(f"({users})")

    if mentioning_accounts:
        users = " OR ".join([f"@{u.lstrip('@').strip()}" for u in mentioning_accounts if u.strip()])
        query_parts.append(f"({users})")

    # 5. Filters (Links, Media, Language)
    if language:
        query_parts.append(f"lang:{language.strip()}")
    
    if has_links is True:
        query_parts.append("filter:links")
    elif has_links is False:
        query_parts.append("-filter:links")
    
    if has_media:
        query_parts.append("filter:media")

    # 6. Engagement Metrics
    if min_replies is not None and min_replies > 0:
        query_parts.append(f"min_replies:{min_replies}")
    if min_likes is not None and min_likes > 0:
        query_parts.append(f"min_faves:{min_likes}")
    if min_retweets is not None and min_retweets > 0:
        query_parts.append(f"min_retweets:{min_retweets}")

    # 7. Time Constraints
    if since_date:
        query_parts.append(f"since:{since_date}")
    if until_date:
        query_parts.append(f"until:{until_date}")

    # Final Query Assembly
    full_query = " ".join(query_parts).strip()

    print(full_query)
    if not full_query:
        return {"error": "The generated query is empty. Please provide at least one search criterion."}

    # API Request
    try:
        headers = {"X-API-Key": TWITTER_API_KEY}
        params = {
            "query": full_query,
            "queryType": query_type,
            "cursor": cursor
        }
        
        response = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data:
            tweets = extract_tweet_items(data)
            print(f"Extracted tweets: {tweets}")
            return {
                "status": "success",
                "tweets": tweets
            }
        else:
            print(f"[Engine] No results from searching")
            return {
                "status": "error",
                "error": "Failed to retrieve tweets"
            }
        # return {
        #     "status": "success",
        #     "search_metadata": {
        #         "query": full_query,
        #         "type": query_type,
        #         "timestamp_utc": datetime.utcnow().isoformat()
        #     },
        #     "results": data
        # }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"HTTP Request failed: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}


@mcp.tool()
def get_market_news(
    query: Optional[str] = None,
    tickers: Optional[str] = None,
    topics: Optional[str] = None
) -> str:
    """
    Search for market news articles from Alpha Vantage.

    Args:
        query: Optional search query description (for context, not used in API call)
        tickers: Stock/crypto/forex symbols (e.g., "AAPL" or "COIN,CRYPTO:BTC,FOREX:USD")
        topics: News topics (e.g., "technology" or "technology,ipo")

    Returns:
        Formatted string containing news articles with titles, summaries, and URLs
    """
    try:
        retrive_news = StockNews()
        news = retrive_news.retrive_news(tickers=tickers, topics=topics)

        if not news:
            return "No news articles found for the given criteria."

        # Format the news articles
        result = f"Found {len(news)} news articles:\n\n"
        for i, article in enumerate(news, 1):
            title = article.get("title", "No title")
            summary = article.get("summary", "No summary available")
            url = article.get("url", "")
            source = article.get("source", "Unknown")
            time_published = article.get("time_published", "")

            result += f"{i}. {title}\n"
            result += f"   Source: {source}\n"
            if time_published:
                result += f"   Published: {time_published}\n"
            result += f"   Summary: {summary}\n"
            if url:
                result += f"   URL: {url}\n"
            result += "\n"

        return result
    except Exception as e:
        return f"Error fetching news: {str(e)}"


if __name__ == "__main__":
    # 打印当前 CWD 和 PYTHONPATH 帮助 debug
    import sys
    print(f"Current Working Directory: {os.getcwd()}")
    print(f"Python Path: {sys.path}")

    port = int(os.getenv("SEARCH_HTTP_PORT", "8001"))
    print(f"Try Running Alpha Vantage News Tool as search tool on port {port}")
    
    try:
        # 建议换个端口试试，比如 8011，看是否还报错
        mcp.run(transport="streamable-http", port=port)
    except Exception as e:
        print(f"Fatal error: {e}")

