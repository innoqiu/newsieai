import asyncio
import json
import os
from typing import Any, Dict, Optional, List
from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

load_dotenv()


# Class-level storage for conversation history per user
# Key: (user_id, email) tuple, Value: List of messages
# A session is defined as: from the last successful tool call until the next successful tool call
_conversation_histories: Dict[tuple, List[BaseMessage]] = {}


class ProfileManagerAgent:
    """
    [Profile Manager Agent]: Manages and enriches user profile descriptions.
    
    Responsibilities:
    - Listen to user preferences and feedback
    - Determine when user input is clear and instructive enough to store
    - Add description items to user profiles via MCP tool
    - Ask for clarification when input is unclear or not directly storable
    """

    def __init__(self, user_input: str, user_id: Optional[str] = None, user_email: Optional[str] = None):
        """
        Initialize the profile manager agent.
        
        Args:
            user_input: The user's preference/feedback text
            user_id: Optional user identifier for profile lookup
            user_email: Optional user email for profile lookup
        """
        self.user_input = user_input
        self.user_id = user_id
        self.user_email = user_email
        
        # Standard LLM configuration
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3  # Lower temperature for more consistent decision-making
        )
        
        self.mcp_client = None
        self.agent_runnable = None  # LangGraph compiled runnable instance
        
        # Get conversation history key for this user
        self.history_key = (user_id or "", user_email or "")

    # ----------------------------------------------------------------
    # Core Function 1: MCP Connection Configuration (Required)
    # ----------------------------------------------------------------
    async def setup_mcp_client(self):
        """
        Connect to the Profile Manager MCP service.
        """
        profile_manager_port = os.getenv("PROFILE_MANAGER_HTTP_PORT", "8009")
        mcp_config = {
            "profile_manager_service": {
                "url": f"http://localhost:{profile_manager_port}/mcp",
                "transport": "streamable-http"
            }
        }
        self.mcp_client = MultiServerMCPClient(mcp_config)

    # ----------------------------------------------------------------
    # Core Function 2: Input Data Wrapper (Required)
    # ----------------------------------------------------------------
    def _wrap_context_to_prompt(self) -> str:
        """
        Wrap user input and profile identifiers into a prompt for the LLM.
        """
        context_parts = []
        
        if self.user_id:
            context_parts.append(f"User ID: {self.user_id}")
        if self.user_email:
            context_parts.append(f"User Email: {self.user_email}")
        
        context_str = "\n".join(context_parts) if context_parts else "User identifier not provided"
        
        return f"""
USER INPUT:
{self.user_input}

USER CONTEXT:
{context_str}

Please analyze the user's input and determine if it is clear and instructive enough to store as a preference description.
"""

    # ----------------------------------------------------------------
    # Core Function 3: Core Logic Construction (Required)
    # ----------------------------------------------------------------
    async def create_agent_graph(self):
        """
        Build LangGraph agent: Get tools + Define System Prompt + Compile graph.
        """
        if not self.mcp_client:
            await self.setup_mcp_client()
        
        try:
            # 1. Get tools (dynamically loaded from MCP service)
            tools = await self.mcp_client.get_tools()
        except Exception as e:
            print(f"❌ Error connecting to Profile Manager MCP Server: {e}")
            raise e
        
        # 2. Define System Prompt
        system_prompt = """You are a Profile Manager Agent. Your role is to help enrich user profiles by understanding and storing user preferences.

## YOUR TASK:
The user will talk to you about their preferences, interests, or feedback. You need to:
1. **Analyze the input**: Determine the user's intent:
   - **View Profile**: User wants to see their current preferences/profile
   - **Add Preference**: User wants to add a new preference (input is clear and instructive)
   - **Delete/Change Preference**: User wants to delete or modify an existing preference
   - **Unclear Input**: User's input is unclear or not directly storable → Ask for clarification

2. **Take appropriate action based on intent**:
   - **View Profile** → Call `get_user_descriptions` tool to retrieve and display their preferences
   - **Add Preference** (CLEAR and INSTRUCTIVE) → Call `add_user_description` tool to store it
   - **Delete Preference** → Call `delete_user_description` tool to remove the specified item
   - **Change Preference** → First call `delete_user_description` to remove the old one, then call `add_user_description` to add the updated version
   - **Unclear Input** → Ask the user to specify the unclear parts

## INTENT DETECTION:

### VIEW PROFILE (Use `get_user_descriptions`):
- "What's my profile?", "Show me my preferences", "What do you know about me?"
- "List my preferences", "What are my interests?", "Show my profile"
- "What preferences do I have?", "Tell me about my profile"

### ADD PREFERENCE (Use `add_user_description` - CLEAR and INSTRUCTIVE):
- Specific preferences: "I like technology news", "I'm interested in AI and machine learning"
- Clear interests: "I prefer morning notifications", "I want news about cryptocurrency"
- Concrete feedback: "I don't like sports news", "I want more financial updates"
- Actionable preferences: "Send me news at 9 AM", "Focus on tech startups instead of big tech like meta"

### DELETE PREFERENCE (Use `delete_user_description`):
- "Remove [specific preference]", "Delete [preference]", "I don't want [preference] anymore"
- "Remove my interest in [topic]", "Delete [item] from my profile"
- First, use `get_user_descriptions` to see what's in their profile, then delete the matching item

### CHANGE/UPDATE PREFERENCE (Use `delete_user_description` then `add_user_description`):
- "Change [old preference] to [new preference]", "Update [preference] to [new version]"
- "I used to like [X], but now I prefer [Y]", "Modify [preference] to [new preference]"
- First, delete the old preference, then add the new/updated one

### UNCLEAR or NOT directly storable (Should ask for clarification):
- Vague statements: "I want better news", "Make it good"
- Questions: "What should I do?", "How does this work?"
- Incomplete thoughts: "Maybe...", "I think..."
- Ambiguous requests: "Something about tech", "You know what I mean"
- Requests for information: "Tell me about...", "What is..."

## WORKFLOW:

1. **Read the user input carefully and determine intent**

2. **If VIEW PROFILE**:
   - Call `get_user_descriptions` tool to retrieve all preferences
   - Format and display the preferences in a user-friendly way
   - If the list is empty, inform the user: "You don't have any preferences saved yet. Would you like to add some?"

3. **If ADD PREFERENCE (CLEAR)**:
   - Extract the core preference/interest statement
   - Call `add_user_description` tool with:
     - `user_id` or `email` (use whichever is provided)
     - `description_item`: A clear, concise summary of the user's preference (1-2 sentences max)
   - After successful storage, confirm: "I've saved your preference: [summary]"

4. **If DELETE PREFERENCE**:
   - If the user mentions a specific item, try to match it with existing preferences
   - If unsure, first call `get_user_descriptions` to see what's available
   - Call `delete_user_description` tool with the exact item text to delete
   - Confirm deletion: "I've removed '[item]' from your preferences."

5. **If CHANGE/UPDATE PREFERENCE**:
   - Identify the old preference to remove and the new preference to add
   - If unsure about the exact old preference text, first call `get_user_descriptions` to see current preferences
   - Call `delete_user_description` to remove the old preference
   - Call `add_user_description` to add the updated/new preference
   - Confirm: "I've updated your preference from '[old]' to '[new]'."

6. **If UNCLEAR**:
   - Politely ask the user to clarify:
     - What specific aspect is unclear?
     - What additional information is needed?
     - Provide examples of what would be helpful
   - Example: "Could you be more specific about what type of news you prefer? For example, are you interested in technology, finance, sports, or something else?"

## IMPORTANT RULES:
- Always be helpful and conversational
- Don't store vague or unclear information
- When storing, create concise, actionable description items (1-2 sentences)
- If user_id or email is not provided, inform the user that you need their identifier to save preferences
- Be patient and guide users to provide clear preferences

## CRITICAL OUTPUT FORMAT:
**ONLY output the message you would directly say to the user. DO NOT include:**
- Your analysis or reasoning process
- Explanations of why the input is clear or unclear
- Internal thoughts or decision-making steps
- Meta-commentary about the user's input

**DO output:**
- Direct, conversational responses
- Questions asking for clarification (without explaining why you're asking)
- Confirmation messages after storing preferences

**Examples:**
❌ BAD: "The user's input 'I want better news' is vague and does not specify what type of news they prefer. Could you please clarify..."
✅ GOOD: "Could you be more specific about what type of news you prefer? For example, are you interested in technology, finance, sports, or something else?"

❌ BAD: "I've analyzed your input and determined it's clear. I've saved your preference: I'm interested in AI and machine learning."
✅ GOOD: "I've saved your preference: I'm interested in AI and machine learning."

## TOOL USAGE:
You have access to three tools:

1. **`get_user_descriptions`**: Retrieve all description items from the user's profile
   - Use when user wants to view their profile/preferences, user might ask: "What do you know about me?", "How do you know me?", "What info do you have?"
   - user might also ask: "Show me my data", "What are you tracking?", "Show me my preferences"
   - Returns a list of all saved preferences

2. **`add_user_description`**: Add a new description item to the user's profile
   - Use when user wants to add a new preference (CLEAR and INSTRUCTIVE input)
   - Requires: `user_id` or `email`, and `description_item` (the preference text)

3. **`delete_user_description`**: Delete a specific description item from the user's profile
   - Use when user wants to remove a preference
   - Requires: `user_id` or `email`, and `description_item` (must match exactly)
   - For changes: Delete old item first, then add new one

**Important Notes:**
- When deleting or changing, the `description_item` parameter must match the EXACT text from the profile
- If unsure about exact text, call `get_user_descriptions` first to see the current list
- For changes: Always delete the old preference first, then add the new/updated one
- All tools require either `user_id` OR `email` (at least one must be provided)
### VIEW PROFILE (Use `get_user_descriptions`):
- "What do you know about me?", "How do you know me?", "What info do you have?"
- "Show me my data", "What are you tracking?", "Show me my preferences"

Remember: Your goal is to help users build and manage a rich profile of their preferences. Always respond as if you're having a natural conversation - no analysis, just direct communication.
"""
        
        # 3. Create agent graph
        self.agent_runnable = create_agent(self.llm, tools, system_prompt=system_prompt)

    def _clean_response(self, raw_response: str) -> str:
        """
        Clean the agent's response to remove internal reasoning and keep only user-facing content.
        """
        if not raw_response:
            return raw_response
        
        # Split by common patterns that indicate analysis vs user message
        lines = raw_response.split('\n')
        cleaned_lines = []
        skip_until_question = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip lines that are clearly analysis/reasoning
            if any(phrase in line.lower() for phrase in [
                "the user's input",
                "is vague",
                "does not specify",
                "i've analyzed",
                "i've determined",
                "after analyzing",
                "the input is",
                "this is unclear",
                "this is clear"
            ]):
                # If we see analysis, skip until we find a question or direct statement
                skip_until_question = True
                continue
            
            # If we're skipping, look for questions or direct statements
            if skip_until_question:
                if line.startswith(('Could you', 'Can you', 'Would you', 'Please', 'I\'ve', 'I have')) or '?' in line:
                    skip_until_question = False
                    cleaned_lines.append(line)
                continue
            
            cleaned_lines.append(line)
        
        # If we have cleaned lines, join them; otherwise return original (might be tool output)
        if cleaned_lines:
            return '\n'.join(cleaned_lines)
        
        return raw_response

    # ----------------------------------------------------------------
    # Memory System: Session-based Conversation History
    # ----------------------------------------------------------------
    def _get_conversation_history(self) -> List[BaseMessage]:
        """
        Get conversation history for this user's current session.
        A session is from the last successful tool call until the next successful tool call.
        """
        return _conversation_histories.get(self.history_key, [])

    def _add_to_conversation_history(self, messages: List[BaseMessage]):
        """
        Add messages to conversation history for this user's current session.
        """
        if self.history_key not in _conversation_histories:
            _conversation_histories[self.history_key] = []
        _conversation_histories[self.history_key].extend(messages)

    def _clear_conversation_history(self):
        """
        Clear conversation history for this user's current session.
        Called after a successful tool call to start a new session.
        """
        if self.history_key in _conversation_histories:
            _conversation_histories[self.history_key] = []
            print(f"[ProfileManager] Cleared conversation history (new session started) for user: {self.history_key}")

    def _get_tool_call_info(self, result: Dict[str, Any]) -> tuple:
        """
        Check if any profile_manager tools were successfully called in the agent's response.
        
        Returns:
            Tuple of (tool_called_successfully: bool, tool_name: Optional[str])
            - tool_called_successfully: True if a tool was successfully called
            - tool_name: Name of the tool that was called ('add_user_description', 'delete_user_description', 'get_user_descriptions')
        """
        messages = result.get("messages", [])
        all_profile_manager_tools = ['add_user_description', 'delete_user_description', 'get_user_descriptions']
        update_tools = ['add_user_description', 'delete_user_description']  # Tools that update the profile
        
        # Look through messages for tool calls and their results
        for msg in messages:
            # Check if this is a ToolMessage (tool execution result)
            if isinstance(msg, ToolMessage):
                # ToolMessage has a 'name' attribute indicating which tool was called
                tool_name = getattr(msg, 'name', '')
                if tool_name in all_profile_manager_tools:
                    # Check the tool result content for success status
                    content = getattr(msg, 'content', '')
                    if isinstance(content, str):
                        try:
                            tool_result = json.loads(content)
                            if isinstance(tool_result, dict):
                                status = tool_result.get('status', '')
                                # Return True if tool was called and status is success
                                if status == 'success':
                                    print(f"[ProfileManager] Detected successful tool call: {tool_name}")
                                    return (True, tool_name)
                        except (json.JSONDecodeError, AttributeError):
                            # If not JSON, check if content indicates success
                            if any(indicator in content.lower() for indicator in [
                                'success', 'successfully', 'added', 'deleted', 'retrieved'
                            ]):
                                print(f"[ProfileManager] Detected successful tool call (non-JSON): {tool_name}")
                                return (True, tool_name)
        
        return (False, None)
    
    def _check_tool_calls_successful(self, result: Dict[str, Any]) -> bool:
        """
        Check if any profile_manager tools that UPDATE the profile were successfully called.
        Used to determine if we should clear conversation history (start new session).
        
        Returns True if add_user_description or delete_user_description was successfully called.
        """
        tool_called, tool_name = self._get_tool_call_info(result)
        if tool_called and tool_name in ['add_user_description', 'delete_user_description']:
            return True
        return False

    # ----------------------------------------------------------------
    # Core Function 4: Run Entry Point (Standard Logic)
    # ----------------------------------------------------------------
    async def run(self) -> tuple:
        """
        Execute the agent's main workflow with session-based memory.
        Maintains conversation history within a session (from last successful tool call to next).
        Clears history after successful tool calls to start a new session.
        
        Returns:
            Tuple of (response: str, tool_called: Optional[str])
            - response: The agent's cleaned response text
            - tool_called: Name of the tool that was called ('add_user_description', 'delete_user_description', 'get_user_descriptions'), or None
        """
        if not self.agent_runnable:
            await self.create_agent_graph()
        
        # Use wrapper to process input
        user_msg = self._wrap_context_to_prompt()
        
        # Get conversation history for this session
        conversation_history = self._get_conversation_history()
        
        # Construct messages: history + current user message
        messages = conversation_history + [HumanMessage(content=user_msg)]
        
        # Construct LangChain input
        inputs = {"messages": messages}
        
        # Asynchronously invoke the graph
        result = await self.agent_runnable.ainvoke(inputs)
        
        # Get all new messages (those not in our history)
        new_messages = result["messages"][len(conversation_history):]
        
        # Get tool call information
        tool_called, tool_name = self._get_tool_call_info(result)
        
        # Check if any profile_manager tools that UPDATE the profile were successfully called (add/delete operations)
        update_tool_called = self._check_tool_calls_successful(result)
        
        if update_tool_called:
            # Clear conversation history when a profile update tool is successfully called (start new session)
            self._clear_conversation_history()
            print(f"[ProfileManager] Profile update tool successfully called, starting new session for user: {self.history_key}")
        else:
            # Add new messages to conversation history to maintain context within the session
            self._add_to_conversation_history(new_messages)
            print(f"[ProfileManager] Added {len(new_messages)} messages to session history for user: {self.history_key}")
        
        # Get raw response (last message content)
        raw_response = result["messages"][-1].content
        
        # Clean response to remove internal reasoning
        cleaned_response = self._clean_response(raw_response)
        
        # Return cleaned response and tool call information
        return (cleaned_response, tool_name if tool_called else None)

    # ----------------------------------------------------------------
    # Core Function 5: Resource Cleanup (Standard Logic)
    # ----------------------------------------------------------------
    async def cleanup(self):
        """Disconnect MCP connection to prevent port conflicts or connection leaks."""
        if self.mcp_client:
            try:
                await self.mcp_client.disconnect()
            except:
                pass


# ----------------------------------------------------------------
# Utility Functions for Conversation History Management
# ----------------------------------------------------------------
def clear_user_conversation_history(user_id: Optional[str] = None, user_email: Optional[str] = None):
    """
    Clear conversation history for a specific user.
    Useful for manual cleanup or when user logs out.
    
    Args:
        user_id: User identifier
        user_email: User email
    """
    history_key = (user_id or "", user_email or "")
    if history_key in _conversation_histories:
        _conversation_histories[history_key] = []
        print(f"[ProfileManager] Manually cleared conversation history for user: {history_key}")


# ----------------------------------------------------------------
# Core Function 6: External Convenience Entry Point (Module Level Function)
# ----------------------------------------------------------------
async def run_profile_manager(user_input: str, user_id: Optional[str] = None, user_email: Optional[str] = None) -> tuple:
    """
    External system's unified entry point to call this agent.
    Automatically handles lifecycle (Init -> Run -> Cleanup).
    
    Args:
        user_input: The user's preference/feedback text
        user_id: Optional user identifier
        user_email: Optional user email
    
    Returns:
        Tuple of (response: str, tool_called: Optional[str])
        - response: The agent's cleaned response text
        - tool_called: Name of the tool that was called ('add_user_description', 'delete_user_description', 'get_user_descriptions'), or None
    """
    agent = ProfileManagerAgent(user_input, user_id, user_email)
    try:
        return await agent.run()
    finally:
        await agent.cleanup()


# ----------------------------------------------------------------
# Local Test Stub (Main)
# ----------------------------------------------------------------
if __name__ == "__main__":
    # Test with mock data
    test_input = "I'm really interested in artificial intelligence and machine learning news"
    test_user_id = "test_user_123"
    test_email = "test@example.com"
    
    print("Testing Profile Manager Agent...")
    print(f"Input: {test_input}")
    print(f"User ID: {test_user_id}")
    print("\n" + "="*50)
    
    response, tool_called = asyncio.run(run_profile_manager(test_input, test_user_id, test_email))
    
    print("\n" + "="*50)
    print("Agent Response:")
    print(response)
    if tool_called:
        print(f"\nTool Called: {tool_called}")

