import os
import sys
import json
from fastmcp import FastMCP
from typing import Optional, List

# --- 路径配置 ---
# Import database functions
try:
    # Add parent directory to path to import database module
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import get_user_profile, get_user_profile_by_email, save_user_profile, get_connection
except ImportError as e:
    print(f"❌ Error: Could not import database module: {e}")
    get_user_profile = None
    get_user_profile_by_email = None
    save_user_profile = None
    get_connection = None


# --- 初始化 MCP 服务 ---
# 定义服务名称
mcp = FastMCP("Profile Manager Service")


# --- 定义工具 (Tool) ---
@mcp.tool()
def add_user_description(user_id: Optional[str] = None, email: Optional[str] = None, description_item: str = "") -> str:
    """
    Add a new description item to a user's profile in the user_profiles table.
    
    The description field stores a list of strings summarizing user preferences/comments.
    This tool appends a new item to that list.
    
    Args:
        user_id: The user identifier (optional, if not provided, email will be used)
        email: The user's email address (optional, if not provided, user_id will be used)
        description_item: The new description item to add to the user's description list
    
    Returns:
        A JSON string containing the operation status and updated profile information.
    """
    if not save_user_profile or not get_user_profile or not get_user_profile_by_email:
        return json.dumps({
            "status": "error",
            "message": "Database module not available. Cannot manage user profiles."
        }, ensure_ascii=False)
    
    if not description_item or not description_item.strip():
        return json.dumps({
            "status": "error",
            "message": "description_item cannot be empty."
        }, ensure_ascii=False)
    
    if not user_id and not email:
        return json.dumps({
            "status": "error",
            "message": "Either user_id or email must be provided."
        }, ensure_ascii=False)
    
    print(f"[MCP Tool] Adding description item for user_id: {user_id}, email: {email}")
    print(f"[MCP Tool] New description item: {description_item[:100]}...")
    
    try:
        # Get existing user profile
        profile = None
        if user_id:
            profile = get_user_profile(user_id)
        elif email:
            profile = get_user_profile_by_email(email)
        
        if not profile:
            return json.dumps({
                "status": "error",
                "message": f"User profile not found for user_id: {user_id}, email: {email}"
            }, ensure_ascii=False)
        
        # Get current description list
        current_description = profile.get("description", [])
        
        # Ensure description is a list
        if not isinstance(current_description, list):
            # If it's a string (JSON), try to parse it
            if isinstance(current_description, str):
                try:
                    current_description = json.loads(current_description)
                except json.JSONDecodeError:
                    # If parsing fails, start with empty list
                    current_description = []
            else:
                # If it's not a list or string, start with empty list
                current_description = []
        
        # Add new description item
        new_item = description_item.strip()
        
        # Avoid duplicates (optional - you might want to allow duplicates)
        if new_item not in current_description:
            current_description.append(new_item)
        else:
            return json.dumps({
                "status": "warning",
                "message": "Description item already exists in user profile.",
                "user_id": profile.get("user_id"),
                "email": profile.get("email"),
                "description": current_description
            }, ensure_ascii=False)
        
        # Update profile with new description
        profile["description"] = current_description
        
        # Save updated profile
        success = save_user_profile(profile)
        
        if success:
            result = {
                "status": "success",
                "message": "Description item successfully added to user profile.",
                "user_id": profile.get("user_id"),
                "email": profile.get("email"),
                "description": current_description,
                "added_item": new_item
            }
            print(f"[MCP Tool] Successfully added description item for user: {profile.get('user_id')}")
            return json.dumps(result, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "error",
                "message": "Failed to save updated profile to database."
            }, ensure_ascii=False)
            
    except json.JSONDecodeError as e:
        result = {
            "status": "error",
            "message": f"Failed to parse description JSON: {str(e)}"
        }
        print(f"[MCP Tool] JSON decode error: {e}")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        result = {
            "status": "error",
            "message": f"Unexpected error while adding description: {str(e)}"
        }
        print(f"[MCP Tool] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_user_descriptions(user_id: Optional[str] = None, email: Optional[str] = None) -> str:
    """
    Retrieve the full list of description items from a user's profile in the user_profiles table.
    
    Args:
        user_id: The user identifier (optional, if not provided, email will be used)
        email: The user's email address (optional, if not provided, user_id will be used)
    
    Returns:
        A JSON string containing the operation status and the list of description items.
    """
    if not get_user_profile or not get_user_profile_by_email:
        return json.dumps({
            "status": "error",
            "message": "Database module not available. Cannot retrieve user profiles."
        }, ensure_ascii=False)
    
    if not user_id and not email:
        return json.dumps({
            "status": "error",
            "message": "Either user_id or email must be provided."
        }, ensure_ascii=False)
    
    print(f"[MCP Tool] Retrieving descriptions for user_id: {user_id}, email: {email}")
    
    try:
        # Get user profile
        profile = None
        if user_id:
            profile = get_user_profile(user_id)
        elif email:
            profile = get_user_profile_by_email(email)
        
        if not profile:
            return json.dumps({
                "status": "error",
                "message": f"User profile not found for user_id: {user_id}, email: {email}"
            }, ensure_ascii=False)
        
        # Get current description list
        current_description = profile.get("description", [])
        
        # Ensure description is a list
        if not isinstance(current_description, list):
            # If it's a string (JSON), try to parse it
            if isinstance(current_description, str):
                try:
                    current_description = json.loads(current_description)
                except json.JSONDecodeError:
                    # If parsing fails, start with empty list
                    current_description = []
            else:
                # If it's not a list or string, start with empty list
                current_description = []
        
        result = {
            "status": "success",
            "message": "Description items retrieved successfully.",
            "user_id": profile.get("user_id"),
            "email": profile.get("email"),
            "description": current_description,
            "count": len(current_description)
        }
        print(f"[MCP Tool] Successfully retrieved {len(current_description)} description items for user: {profile.get('user_id')}")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        result = {
            "status": "error",
            "message": f"Unexpected error while retrieving descriptions: {str(e)}"
        }
        print(f"[MCP Tool] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def delete_user_description(user_id: Optional[str] = None, email: Optional[str] = None, description_item: str = "") -> str:
    """
    Delete a specific description item from a user's profile in the user_profiles table.
    
    Args:
        user_id: The user identifier (optional, if not provided, email will be used)
        email: The user's email address (optional, if not provided, user_id will be used)
        description_item: The description item to delete from the user's description list (must match exactly)
    
    Returns:
        A JSON string containing the operation status and updated profile information.
    """
    if not save_user_profile or not get_user_profile or not get_user_profile_by_email:
        return json.dumps({
            "status": "error",
            "message": "Database module not available. Cannot manage user profiles."
        }, ensure_ascii=False)
    
    if not description_item or not description_item.strip():
        return json.dumps({
            "status": "error",
            "message": "description_item cannot be empty."
        }, ensure_ascii=False)
    
    if not user_id and not email:
        return json.dumps({
            "status": "error",
            "message": "Either user_id or email must be provided."
        }, ensure_ascii=False)
    
    print(f"[MCP Tool] Deleting description item for user_id: {user_id}, email: {email}")
    print(f"[MCP Tool] Description item to delete: {description_item[:100]}...")
    
    try:
        # Get existing user profile
        profile = None
        if user_id:
            profile = get_user_profile(user_id)
        elif email:
            profile = get_user_profile_by_email(email)
        
        if not profile:
            return json.dumps({
                "status": "error",
                "message": f"User profile not found for user_id: {user_id}, email: {email}"
            }, ensure_ascii=False)
        
        # Get current description list
        current_description = profile.get("description", [])
        
        # Ensure description is a list
        if not isinstance(current_description, list):
            # If it's a string (JSON), try to parse it
            if isinstance(current_description, str):
                try:
                    current_description = json.loads(current_description)
                except json.JSONDecodeError:
                    # If parsing fails, start with empty list
                    current_description = []
            else:
                # If it's not a list or string, start with empty list
                current_description = []
        
        # Item to delete
        item_to_delete = description_item.strip()
        
        # Check if item exists
        if item_to_delete not in current_description:
            return json.dumps({
                "status": "error",
                "message": f"Description item not found in user profile: '{item_to_delete}'",
                "user_id": profile.get("user_id"),
                "email": profile.get("email"),
                "description": current_description
            }, ensure_ascii=False)
        
        # Remove the item
        current_description.remove(item_to_delete)
        
        # Update profile with updated description
        profile["description"] = current_description
        
        # Save updated profile
        success = save_user_profile(profile)
        
        if success:
            result = {
                "status": "success",
                "message": "Description item successfully deleted from user profile.",
                "user_id": profile.get("user_id"),
                "email": profile.get("email"),
                "description": current_description,
                "deleted_item": item_to_delete
            }
            print(f"[MCP Tool] Successfully deleted description item for user: {profile.get('user_id')}")
            return json.dumps(result, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "error",
                "message": "Failed to save updated profile to database."
            }, ensure_ascii=False)
            
    except Exception as e:
        result = {
            "status": "error",
            "message": f"Unexpected error while deleting description: {str(e)}"
        }
        print(f"[MCP Tool] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps(result, ensure_ascii=False)


# --- 启动服务 ---
if __name__ == "__main__":
    # 从环境变量获取端口，默认 8009 (避免与 API server 8008 和 Pay service 8007 冲突)
    port = int(os.getenv("PROFILE_MANAGER_HTTP_PORT", "8009"))
    print(f"Profile Manager MCP Service starting on port {port}")
    
    # 使用 mcp.run() 启动，FastMCP 会自动处理 HTTP/SSE 协议
    mcp.run(transport="streamable-http", port=port)

