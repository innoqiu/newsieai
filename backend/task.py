# tasks.py
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

# Import engine functions
from engine import process_general_search, process_x_from_user, process_x_from_topic

# Import retriv agent for smart mode
try:
    from agents.retriv import retriv_run_agent
except ImportError:
    print("Warning: retriv agent not available")
    retriv_run_agent = None

# Import database function to get user profile
try:
    from database import get_user_profile, get_user_profile_by_email
except ImportError:
    print("Warning: Database module not available")
    get_user_profile = None
    get_user_profile_by_email = None

# 定期执行的函数
'''
{
  "thread_id": "thread-example-1769499064",
  "name": "This is new",
  "notification_schedule": {
    "type": "daily",
    "times": [
      "17:58"
    ]
  },
  "interests": "asdwads",
  "blocks": [
    {
      "id": 1769499048938,
      "type": "x-from-user",
      "body": "@user",
      "ai": "newest"
    },
    {
      "id": 1769499050775,
      "type": "x-from-topic",
      "body": "this is ai",
      "ai": "selective"
    }
  ],
  "timezone": "America/Recife",
  "user_id": "example",
  "email": "example@example.com",
  "profile_data": {
    "name": "example",
    "email": "example@example.com",
    "preferred_notification_times": [
      "17:58"
    ],
    "content_preferences": [
      "asdwads"
    ],
    "x_usernames": [],
    "timezone": "America/Recife"
  }
}
'''


def execute_periodic_scan(thread_id, task_type, thread_structure, user_name=None):
    """
    Execute periodic scan for a thread, processing all blocks.
    
    Args:
        thread_id: 任务ID
        task_type: 'quick_scan', 'full_assistant', 'interval_mode', 'daily_mode', or 'manual_run'
        thread_structure: Complete thread structure dictionary
        user_name: Optional user name
    """
    print(f"[{datetime.now()}] [Worker] 唤醒! 执行任务: {thread_id} |user:{user_name}| 类型: {task_type}")
    
    # Get user profile from database for user_context
    user_context = None
    user_id = thread_structure.get('user_id')
    email = thread_structure.get('email')
    
    if get_user_profile and user_id:
        try:
            user_context = get_user_profile(user_id)
            if user_context:
                print(f"[Worker] Retrieved user profile for user_id: {user_id}")
        except Exception as e:
            print(f"[Worker] Warning: Failed to get user profile by user_id: {e}")
    
    if not user_context and get_user_profile_by_email and email:
        try:
            user_context = get_user_profile_by_email(email)
            if user_context:
                print(f"[Worker] Retrieved user profile for email: {email}")
        except Exception as e:
            print(f"[Worker] Warning: Failed to get user profile by email: {e}")
    
    if not user_context:
        print(f"[Worker] Warning: Could not retrieve user profile. Using empty context.")
        user_context = {}
    
    # Get blocks from thread structure
    blocks = thread_structure.get('blocks', [])
    
    if not blocks:
        print(f"[Worker] No blocks found in thread structure")
        return
    
    print(f"[Worker] Processing {len(blocks)} block(s)")
    
    # Iterate through all blocks and process each one
    results = []
    for block in blocks:
        block_type = block.get('type', '').lower()
        mode = block.get('ai', 'selective')  # Default mode if not specified
        
        # Handle tags (new format) or body (legacy format)
        tags = block.get('tags', [])
        body = block.get('body', '')
        
        # Convert tags list to body string for engine functions
        # If tags exist, use them; otherwise fall back to body
        if tags and isinstance(tags, list) and len(tags) > 0:
            # Convert tags list to comma-separated string
            if block_type == 'x-from-user':
                # For x-from-user, ensure @ prefix and join
                body = ', '.join([tag if tag.startswith('@') else f'@{tag}' for tag in tags])
            else:
                # For other types, just join with comma
                body = ', '.join(tags)
        elif not body:
            # No tags and no body, skip this block
            print(f"[Worker] Warning: Block {block_type} has no tags or body, skipping")
            continue
        
        print(f"[Worker] Processing block: type={block_type}, tags={tags}, body={body}, mode={mode}")
        
        try:
            # Normalize mode to lowercase for comparison
            mode_lower = mode.lower() if mode else "raw"
            
            # Check if mode is "smart" - use agent, otherwise use raw engine functions
            if mode_lower == "smart":
                # Smart mode: Use retriv agent for intelligent search
                if not retriv_run_agent:
                    print(f"[Worker] Error: Smart mode requested but retriv agent not available")
                    results.append({
                        "status": "error",
                        "block_type": block_type,
                        "error": "Smart mode not available - retriv agent not found"
                    })
                    continue
                
                # Convert tags to query_body string
                if isinstance(tags, list):
                    if block_type == 'x-from-user':
                        # For x-from-user, join usernames with commas
                        query_body = ', '.join([tag if tag.startswith('@') else f'@{tag}' for tag in tags])
                    else:
                        # For other types, join with commas
                        query_body = ', '.join(tags)
                else:
                    query_body = str(tags) if tags else ""
                
                if not query_body:
                    print(f"[Worker] Warning: No query body for smart mode, skipping")
                    results.append({
                        "status": "error",
                        "block_type": block_type,
                        "error": "No query body provided for smart mode"
                    })
                    continue
                
                print(f"[Worker] Smart mode: Calling retriv agent with query_body: {query_body}")
                
                # Call the agent asynchronously
                try:
                    agent_result = asyncio.run(retriv_run_agent(
                        user_context=user_context,
                        query_body=query_body,
                        user_profile=None
                    ))
                    
                    # Parse agent result (should be JSON string with items)
                    import json
                    try:
                        if isinstance(agent_result, str):
                            # Try to parse as JSON
                            parsed_result = json.loads(agent_result)
                        else:
                            parsed_result = agent_result
                        
                        # Extract items if available
                        items = parsed_result.get("items", []) if isinstance(parsed_result, dict) else []
                        
                        result = {
                            "status": "success",
                            "block_type": block_type,
                            "mode": "smart",
                            "query_body": query_body,
                            "user_context": user_context,
                            "items": items,
                            "raw_response": agent_result
                        }
                    except json.JSONDecodeError:
                        # If not JSON, return as text
                        result = {
                            "status": "success",
                            "block_type": block_type,
                            "mode": "smart",
                            "query_body": query_body,
                            "user_context": user_context,
                            "response": agent_result
                        }
                    
                    results.append(result)
                    print(f"[Worker] Smart mode: Agent returned {len(items) if 'items' in result else 0} items")
                    
                except Exception as e:
                    print(f"[Worker] Error in smart mode agent call: {e}")
                    import traceback
                    traceback.print_exc()
                    results.append({
                        "status": "error",
                        "block_type": block_type,
                        "mode": "smart",
                        "error": f"Agent call failed: {str(e)}"
                    })
            
            else:
                # Raw mode: Use original engine functions
                print(f"[Worker] Raw mode: Using engine functions")
                if block_type == 'general-search':
                    # process_general_search expects body as string, not tags as list
                    body_str = body if body else (', '.join(tags) if isinstance(tags, list) else str(tags))
                    result = process_general_search(user_context, body_str, mode)
                    results.append(result)
                elif block_type == 'x-from-user':
                    # process_x_from_user expects tags as list
                    tags_list = tags if isinstance(tags, list) else ([tags] if tags else [])
                    result = process_x_from_user(user_context, tags_list, mode)
                    results.append(result)
                elif block_type == 'x-from-topic':
                    # process_x_from_topic expects tags as list
                    tags_list = tags if isinstance(tags, list) else ([tags] if tags else [])
                    result = process_x_from_topic(user_context, tags_list, mode)
                    results.append(result)
                else:
                    print(f"[Worker] Warning: Unknown block type '{block_type}', skipping")
                    results.append({
                        "status": "error",
                        "block_type": block_type,
                        "error": f"Unknown block type: {block_type}"
                    })
        except Exception as e:
            print(f"[Worker] Error processing block {block_type}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "status": "error",
                "block_type": block_type,
                "error": str(e)
            })
    
    print(f"[Worker] Completed processing {len(results)} block(s)")
    print(f"[{datetime.now()}] [Worker] 任务 {thread_id} 完成")
    
    return results