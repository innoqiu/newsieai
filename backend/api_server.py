"""
FastAPI server for NewsieAI backend API.
Handles user profile management and agent interactions.
"""

from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime
from pathlib import Path
import traceback # Add this at the top of api_server.py
# Import agents
from agents.personal_assistant import run_personal_assistant
from agents.retriv import retriv_run_agent
from agents.profile_manager import run_profile_manager

# Import thread functions
from thread import handle_request


# Import database functions
try:
    from database import (
        save_user_profile, get_user_profile, get_user_profile_by_email,
        save_workflow, get_workflow, get_user_workflows, delete_workflow,
        create_user, authenticate_user, get_user_by_id, get_user_by_email,
        update_user_credits, add_user_credits,
        save_thread, get_thread, get_user_threads, delete_thread, update_thread_running,
        get_connection, DB_PATH
    )
    import sqlite3
except ImportError as e:
    print(f"Database import error: {e}")
    print("Database functions may not be available")

# Import authentication functions
try:
    from auth import create_access_token, verify_token, get_user_from_token
except ImportError as e:
    print(f"Auth import error: {e}")
    print("Authentication functions may not be available")

app = FastAPI(title="NewsieAI API", version="1.0.0", debug=True)

# Security scheme for JWT tokens
security = HTTPBearer()

# Logging configuration
LOG_DIR = Path(__file__).parent / "datalog"
LOG_DIR.mkdir(parents=True, exist_ok=True)
REQUEST_LOG_FILE = LOG_DIR / "request.txt"


def log_user_profile_request(user_profile: Dict[str, Any], endpoint: str = "personal-assistant"):
    """
    Log user profile request to request.txt file.
    
    Args:
        user_profile: User profile dictionary
        endpoint: API endpoint name where the request was received
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = {
            "timestamp": timestamp,
            "endpoint": endpoint,
            "user_profile": user_profile
        }
        
        # Append to log file
        with open(REQUEST_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, indent=2, ensure_ascii=False))
            f.write("\n" + "="*80 + "\n\n")
            
    except Exception as e:
        print(f"Warning: Failed to log user profile request: {e}")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database when API server starts"""
    try:
        from database import init_database
        init_database()
        print("Database initialized on API server startup")
    except ImportError:
        print("Warning: Database module not available")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
    try:
        from scheduler_config import scheduler
        if not scheduler.running:
            scheduler.start()
            print("Scheduler started successfully")
        else:
            print("Scheduler is already running")
    except Exception as e:
        print(f"Warning: Failed to start scheduler: {e}")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =================================================================
# Pydantic Models
# =================================================================

class UserProfileRequest(BaseModel):
    """User profile data from frontend"""
    name: str  # What should I call you
    email: EmailStr  # Where to send your news
    notification_time: str  # When to receive news (format: "HH:MM" or "HH:MM,HH:MM" for multiple)
    interests: str  # User interests (comma-separated or free text)
    x_usernames: Optional[str] = ""  # X (Twitter) usernames (comma-separated, e.g., "@elonmusk,@openai")
    thread_structure: Optional[Dict[str, Any]] = None  # Full thread structure for full assistant

class UserProfileResponse(BaseModel):
    """Response after profile creation"""
    status: str
    message: str
    user_id: str
    profile: dict

class NewsRequestRequest(BaseModel):
    """Request to get news based on profile"""
    user_id: Optional[str] = None
    content_query: Optional[str] = None
    thread_structure: Optional[Dict[str, Any]] = None  # Full thread structure for quick scan

class NewsItem(BaseModel):
    """Individual news item structure"""
    url: Optional[str] = None
    author: Optional[str] = None
    text: Optional[str] = None
    created_at: Optional[str] = None
    quoted_author: Optional[str] = None
    quoted_text: Optional[str] = None
    media_urls: List[str] = []

class NewsRequestResponse(BaseModel):
    """Response with news content"""
    status: str
    items: Optional[List[NewsItem]] = None  # Changed from content: str to items: List[NewsItem]
    content: Optional[str] = None  # Keep for backward compatibility, but deprecated
    message: Optional[str] = None

class CheckProfileRequest(BaseModel):
    """Request to check user profile"""
    email: EmailStr

class WorkflowSaveRequest(BaseModel):
    """Request to save a workflow with email"""
    workflow_id: Optional[str] = None  # If None, will generate new ID
    name: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    version: str = "1.0.0"
    email: EmailStr

class WorkflowResponse(BaseModel):
    """Response after workflow operation"""
    status: str
    message: str
    workflow_id: str
    workflow: Optional[Dict[str, Any]] = None

class WorkflowListRequest(BaseModel):
    """Request to list workflows for a user"""
    email: EmailStr

class WorkflowDeleteRequest(BaseModel):
    """Request to delete a workflow"""
    email: EmailStr

class RegisterRequest(BaseModel):
    """Request to register a new user"""
    email: EmailStr
    password: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    """Request to login"""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Response with access token"""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

# =================================================================
# Authentication Dependency
# =================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency to get current user from JWT token.
    """
    try:
        token = credentials.credentials
        user_info = get_user_from_token(token)
        
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Get full user data from database
        user = get_user_by_id(user_info["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except NameError:
        raise HTTPException(status_code=503, detail="Authentication not available")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

# =================================================================
# API Endpoints
# =================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "NewsieAI API is running"}

# =================================================================
# Authentication Endpoints
# =================================================================

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """
    Register a new user account.
    
    Receives:
    - email: User email address
    - password: Plain text password
    - name: Optional user name
    """
    try:
        # Create user account
        user = create_user(
            email=request.email,
            password=request.password,
            user_id=None  # Will be auto-generated
        )
        
        if not user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user profile if name provided
        if request.name:
            try:
                user_profile = {
                    "user_id": user["user_id"],
                    "name": request.name,
                    "email": request.email,
                    "timezone": "UTC",
                    "preferred_notification_times": [],
                    "content_preferences": [],
                    "x_usernames": [],
                }
                save_user_profile(user_profile)
            except Exception as e:
                print(f"Warning: Could not create user profile: {e}")
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user["user_id"], "email": user["email"]}
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        )
        
    except HTTPException:
        raise
    except NameError:
        raise HTTPException(status_code=503, detail="Authentication not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering user: {str(e)}")

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.
    
    Receives:
    - email: User email address
    - password: Plain text password
    """
    try:
        # Authenticate user
        user = authenticate_user(request.email, request.password)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user["user_id"], "email": user["email"]}
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        )
        
    except HTTPException:
        raise
    except NameError:
        raise HTTPException(status_code=503, detail="Authentication not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging in: {str(e)}")

@app.get("/api/auth/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current user information from token.
    """
    return {
        "status": "success",
        "user": current_user
    }

class AddCreditsRequest(BaseModel):
    """Request to add credits"""
    amount: int

@app.post("/api/user/add-credits")
async def add_credits_endpoint(
    request: AddCreditsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add credits to user account.
    
    Receives:
    - amount: Number of credits to add
    """
    try:
        user_id = current_user["user_id"]
        
        # Add credits to user account
        add_user_credits(user_id, request.amount)
        
        # Get updated user info
        updated_user = get_user_by_id(user_id)
        
        return {
            "success": True,
            "message": f"Successfully added {request.amount} credits",
            "user": updated_user
        }
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding credits: {str(e)}")

@app.post("/api/profile", response_model=UserProfileResponse)
async def create_user_profile(profile: UserProfileRequest):
    """
    Create or update user profile.
    
    Receives:
    - name: What to call the user
    - email: Where to send news
    - notification_time: When to receive news (HH:MM format, comma-separated for multiple)
    - interests: User interests (comma-separated or free text)
    """
    try:
        # Parse notification times
        notification_times = []
        if profile.notification_time:
            times = [t.strip() for t in profile.notification_time.split(",") if t.strip()]
            notification_times = times
        
        # Parse interests
        interests_list = []
        if profile.interests:
            # Try comma-separated first, otherwise treat as single interest
            if "," in profile.interests:
                interests_list = [i.strip() for i in profile.interests.split(",") if i.strip()]
            else:
                interests_list = [profile.interests.strip()]
        
        # Parse X usernames
        x_usernames_list = []
        if profile.x_usernames:
            # Remove @ symbols if present, we'll add them back if needed
            usernames = [u.strip() for u in profile.x_usernames.split(",") if u.strip()]
            for username in usernames:
                # Ensure username starts with @
                if not username.startswith("@"):
                    username = "@" + username
                x_usernames_list.append(username)
        
        # Generate user_id from email (simple hash or use email as ID)
        user_id = profile.email.split("@")[0]  # Use email prefix as user_id
        
        # Create user profile structure
        user_profile = {
            "user_id": user_id,
            "name": profile.name,
            "email": profile.email,
            "timezone": "UTC",  # Default, can be enhanced later
            "preferred_notification_times": notification_times,
            "content_preferences": interests_list,
            "x_usernames": x_usernames_list,
        }
        
        # Check if user already exists in database
        try:
            existing_profile = get_user_profile_by_email(profile.email)
            
            if existing_profile:
                # User already registered
                return UserProfileResponse(
                    status="already_registered",
                    message=f"User {profile.name} ({profile.email}) has already been registered.",
                    user_id=existing_profile["user_id"],
                    profile=existing_profile
                )
            
            # User doesn't exist, save to database
            success = save_user_profile(user_profile)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to save profile to database")
            
            return UserProfileResponse(
                status="success",
                message=f"Profile created successfully for {profile.name}",
                user_id=user_id,
                profile=user_profile
            )
            
        except NameError:
            # Database functions not available
            print("Warning: Database functions not available, profile not saved")
            return UserProfileResponse(
                status="warning",
                message=f"Profile created but not saved (database unavailable). User: {profile.name}",
                user_id=user_id,
                profile=user_profile
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating profile: {str(e)}")

@app.post("/api/news/request", response_model=NewsRequestResponse)
async def request_news(request: NewsRequestRequest):
    """
    Request news based on user profile or custom query.
    
    If user_id is provided, uses stored profile preferences and X usernames.
    If content_query is provided, uses that for news search.
    """
    try:
        # Pass complete thread structure to handler
        if request.thread_structure:
            handle_request(request.thread_structure)
        
        # For now, use content_query if provided, otherwise default
        # content_query = request.content_query or "today's key market and technology news"
        # print(f"Content query: {content_query}")
        
        # # Get X usernames from user profile if user_id is provided
        # x_usernames = []
        # if request.user_id:
        #     try:
        #         user_profile = get_user_profile(request.user_id)
        #         if user_profile and user_profile.get("x_usernames"):
        #             x_usernames = user_profile["x_usernames"]
        #             print(f"Found X usernames for user {request.user_id}: {x_usernames}")
        #     except Exception as e:
        #         print(f"Warning: Could not retrieve user profile: {e}")
        
        # # Run news retrieval agent with X usernames
        # try:
        #     result = await retriv_run_agent(
        #         context=content_query,
        #         user_profile=None,  # Can be enhanced later
        #         x_usernames=x_usernames if x_usernames else None
        #     )
        # except Exception as e:
        #     print("--- FULL ERROR TRACEBACK ---")
        #     traceback.print_exc() 
        #     print("----------------------------")
        #     return NewsRequestResponse(
        #         status="error",
        #         items=None,
        #         content=None,
        #         message=f"Error retrieving news: {str(e)}"
        #     )
        
        # # Convert result (list of dicts) to list of NewsItem objects
        # news_items = []
        # if result and isinstance(result, list) and len(result) > 0:
        #     for item_dict in result:
        #         if isinstance(item_dict, dict):
        #             try:
        #                 news_items.append(NewsItem(**item_dict))
        #             except Exception as e:
        #                 print(f"Warning: Failed to parse news item: {e}, item: {item_dict}")
        #                 continue
        # If result is None or empty, news_items remains empty list
        
        return NewsRequestResponse(
            status="success",
            # items=news_items,
            content=None,  # Deprecated, use items instead
            # message=f"News retrieved successfully ({len(news_items)} items)"
        )
        
    except Exception as e:
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"Error retrieving news: {str(e)}")

@app.post("/api/personal-assistant/run")
async def run_personal_assistant_endpoint(profile: UserProfileRequest, request: Request):
    """
    Run Personal Assistant Agent with user profile.
    This will gather news based on user preferences and schedule delivery.
    Automatically extracts user IP from the request for location/timezone detection.
    """
    try:
        # Pass complete thread structure to handler
        if profile.thread_structure:
            handle_request(profile.thread_structure)
        
        # Extract client IP address from request
        # Check for forwarded IP (if behind proxy/load balancer)
        # client_ip = request.headers.get("X-Forwarded-For")
        # if client_ip:
        #     # X-Forwarded-For can contain multiple IPs, take the first one
        #     client_ip = client_ip.split(",")[0].strip()
        # elif request.headers.get("X-Real-IP"):
        #     client_ip = request.headers.get("X-Real-IP")
        # else:
        #     # Fallback to direct client IP
        #     client_ip = request.client.host if request.client else None
        
        # # Parse notification times
        # notification_times = []
        # if profile.notification_time:
        #     times = [t.strip() for t in profile.notification_time.split(",") if t.strip()]
        #     notification_times = times
        
        # # Parse interests
        # interests_list = []
        # if profile.interests:
        #     if "," in profile.interests:
        #         interests_list = [i.strip() for i in profile.interests.split(",") if i.strip()]
        #     else:
        #         interests_list = [profile.interests.strip()]
        
        # # Parse X usernames
        # x_usernames_list = []
        # if profile.x_usernames:
        #     usernames = [u.strip() for u in profile.x_usernames.split(",") if u.strip()]
        #     for username in usernames:
        #         # Ensure username starts with @
        #         if not username.startswith("@"):
        #             username = "@" + username
        #         x_usernames_list.append(username)
        
        # # Create user profile
        # user_profile = {
        #     "user_id": profile.email.split("@")[0],
        #     "name": profile.name,
        #     "email": profile.email,
        #     "timezone": "UTC",
        #     "preferred_notification_times": notification_times,
        #     "content_preferences": interests_list,
        #     "x_usernames": x_usernames_list,
        # }
        
        # # Log user profile request
        # log_user_profile_request(user_profile, endpoint="personal-assistant/run")
        
        # # Run personal assistant with extracted IP
        # result = await run_personal_assistant(
        #     user_profile=user_profile,
        #     schedule_log=[],
        #     input_time=None,
        #     input_content="daily briefing based on user preferences",
        #     user_ip=client_ip,
        # )
        
        
        return {
            "status": "success",
            "result": "Personal assistant completed successfully",        
            # "result": result,
            "message": "Personal assistant completed successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running personal assistant: {str(e)}")

@app.get("/api/profile/{user_id}")
async def get_user_profile_endpoint(user_id: str):
    """Get user profile by user_id"""
    try:
        profile = get_user_profile(user_id)
        if profile:
            return {
                "status": "success",
                "profile": profile
            }
        else:
            raise HTTPException(status_code=404, detail=f"Profile not found for user_id: {user_id}")
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving profile: {str(e)}")

@app.get("/api/profile/email/{email}")
async def get_user_profile_by_email_endpoint(email: str):
    """Get user profile by email (GET endpoint)"""
    try:
        profile = get_user_profile_by_email(email)
        if profile:
            return {
                "status": "success",
                "profile": profile
            }
        else:
            raise HTTPException(status_code=404, detail=f"Profile not found for email: {email}")
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving profile: {str(e)}")

@app.post("/api/profile/check")
async def check_user_profile(request: CheckProfileRequest):
    """
    Check if a user profile exists by email.
    Returns the full profile if found.
    """
    try:
        profile = get_user_profile_by_email(request.email)
        if profile:
            return {
                "status": "found",
                "message": f"Profile found for {profile.get('name', 'User')}",
                "profile": profile
            }
        else:
            return {
                "status": "not_found",
                "message": f"No profile found for email: {request.email}",
                "profile": None
            }
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking profile: {str(e)}")

class ProfileManagerChatRequest(BaseModel):
    """Request for profile manager chat"""
    message: str  # User's chat message
    user_id: Optional[str] = None  # Optional user ID
    email: Optional[str] = None  # Optional email

@app.post("/api/profile/chat")
async def profile_manager_chat_endpoint(
    request: ProfileManagerChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Chat with the Profile Manager Agent to update user preferences.
    The agent will analyze the user's input and either store preferences or ask for clarification.
    """
    try:
        # Use authenticated user's info if not provided
        user_id = request.user_id or current_user.get("user_id") or current_user.get("email", "").split("@")[0]
        email = request.email or current_user.get("email")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        # Call the profile manager agent
        agent_response, tool_called = await run_profile_manager(
            user_input=request.message,
            user_id=user_id,
            user_email=email
        )
        
        # Determine notification type based on tool called
        notification_type = None
        if tool_called == 'add_user_description':
            notification_type = 'preference_saved'
        elif tool_called == 'delete_user_description':
            notification_type = 'preference_deleted'
        elif tool_called == 'get_user_descriptions':
            notification_type = 'profile_viewed'
        
        return {
            "status": "success",
            "response": agent_response,
            "tool_called": tool_called,
            "notification_type": notification_type,
            # Backward compatibility
            "preference_saved": (notification_type == 'preference_saved'),
            "message": "Profile manager responded successfully"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error in profile manager chat: {str(e)}")

@app.put("/api/profile", response_model=UserProfileResponse)
async def update_user_profile(profile: UserProfileRequest):
    """
    Update an existing user profile.
    
    Receives:
    - name: What to call the user
    - email: Where to send news (used to find the profile)
    - notification_time: When to receive news (HH:MM format, comma-separated for multiple)
    - interests: User interests (comma-separated or free text)
    - x_usernames: X (Twitter) usernames (comma-separated)
    """
    try:
        # Check if user exists
        existing_profile = get_user_profile_by_email(profile.email)
        if not existing_profile:
            raise HTTPException(status_code=404, detail=f"Profile not found for email: {profile.email}")
        
        # Parse notification times
        notification_times = []
        if profile.notification_time:
            times = [t.strip() for t in profile.notification_time.split(",") if t.strip()]
            notification_times = times
        else:
            # Keep existing notification times if not provided
            notification_times = existing_profile.get("preferred_notification_times", [])
        
        # Parse interests (empty string means clear the list)
        interests_list = []
        if profile.interests and profile.interests.strip():
            if "," in profile.interests:
                interests_list = [i.strip() for i in profile.interests.split(",") if i.strip()]
            else:
                interests_list = [profile.interests.strip()]
        # else: empty string means clear the list (interests_list remains empty)
        
        # Parse X usernames (empty string means clear the list)
        x_usernames_list = []
        if profile.x_usernames and profile.x_usernames.strip():
            usernames = [u.strip() for u in profile.x_usernames.split(",") if u.strip()]
            for username in usernames:
                if not username.startswith("@"):
                    username = "@" + username
                x_usernames_list.append(username)
        # else: empty string means clear the list (x_usernames_list remains empty)
        
        # Create updated user profile structure
        user_profile = {
            "user_id": existing_profile["user_id"],
            "name": profile.name or existing_profile.get("name", ""),
            "email": profile.email,
            "timezone": existing_profile.get("timezone", "UTC"),
            "preferred_notification_times": notification_times,
            "content_preferences": interests_list,
            "x_usernames": x_usernames_list,
        }
        
        # Update profile in database
        success = save_user_profile(user_profile)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update profile in database")
        
        return UserProfileResponse(
            status="success",
            message=f"Profile updated successfully for {user_profile['name']}",
            user_id=user_profile["user_id"],
            profile=user_profile
        )
        
    except HTTPException:
        raise
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

# =================================================================
# Workflow API Endpoints
# =================================================================

class WorkflowSaveRequest(BaseModel):
    """Request to save a workflow with email"""
    workflow_id: Optional[str] = None
    name: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    version: str = "1.0.0"
    email: EmailStr

class WorkflowSaveRequestToken(BaseModel):
    """Request to save a workflow (token-based)"""
    workflow_id: Optional[str] = None
    name: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    version: str = "1.0.0"

@app.post("/api/workflow/save", response_model=WorkflowResponse)
async def save_workflow_endpoint(
    request: WorkflowSaveRequestToken,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Save or update a workflow for a user (token-based).
    
    Receives:
    - workflow_id: Optional, if None a new ID will be generated
    - name: Workflow name
    - nodes: List of node dictionaries
    - edges: List of edge dictionaries
    - version: Workflow version
    """
    try:
        user_id = current_user["user_id"]
        
        # Generate workflow_id if not provided
        workflow_id = request.workflow_id or f"workflow-{user_id}-{int(datetime.now().timestamp())}"
        
        # Save workflow to database
        success = save_workflow(
            workflow_id=workflow_id,
            user_id=user_id,
            name=request.name,
            nodes=request.nodes,
            edges=request.edges,
            version=request.version
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save workflow to database")
        
        # Retrieve saved workflow
        workflow = get_workflow(workflow_id)
        
        return WorkflowResponse(
            status="success",
            message=f"Workflow '{request.name}' saved successfully",
            workflow_id=workflow_id,
            workflow=workflow
        )
        
    except HTTPException:
        raise
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving workflow: {str(e)}")

@app.post("/api/workflow/upload", response_model=WorkflowResponse)
async def upload_workflow_endpoint(
    request: WorkflowSaveRequestToken,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Upload/save a workflow (alias for save endpoint for backward compatibility).
    """
    return await save_workflow_endpoint(request, current_user)

@app.get("/api/workflow/{workflow_id}")
async def get_workflow_endpoint(workflow_id: str):
    """
    Get a workflow by workflow_id.
    """
    try:
        workflow = get_workflow(workflow_id)
        if workflow:
            return {
                "status": "success",
                "workflow": workflow
            }
        else:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving workflow: {str(e)}")

@app.get("/api/workflow/list")
async def list_workflows_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all workflows for the current user (token-based).
    """
    try:
        user_id = current_user["user_id"]
        workflows = get_user_workflows(user_id, include_inactive=False)
        
        return {
            "status": "success",
            "workflows": workflows,
            "count": len(workflows)
        }
    except HTTPException:
        raise
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing workflows: {str(e)}")

class WorkflowDeleteRequest(BaseModel):
    """Request to delete a workflow"""
    email: EmailStr

@app.delete("/api/workflow/{workflow_id}")
async def delete_workflow_endpoint(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a workflow by workflow_id (token-based).
    """
    try:
        user_id = current_user["user_id"]
        
        # Delete workflow (with user verification)
        success = delete_workflow(workflow_id, user_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Workflow {workflow_id} deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Workflow not found or permission denied: {workflow_id}")
    except HTTPException:
        raise
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting workflow: {str(e)}")

# =================================================================
# Thread API Endpoints
# =================================================================

class ThreadSaveRequest(BaseModel):
    """Request to save a thread"""
    thread_id: Optional[str] = None
    name: str
    thread_data: Dict[str, Any]  # The thread structure (blocks, etc.)
    running: Optional[bool] = False  # Whether the thread is running

class ThreadResponse(BaseModel):
    """Response after thread operation"""
    status: str
    message: str
    thread_id: str
    thread: Optional[Dict[str, Any]] = None

@app.post("/api/thread/save", response_model=ThreadResponse)
async def save_thread_endpoint(
    request: ThreadSaveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Save or update a thread for a user (token-based).
    
    Receives:
    - thread_id: Optional, if None a new ID will be generated
    - name: Thread name
    - thread_data: Thread structure dictionary (blocks, notification_time, interests, x_usernames, etc.)
    """
    try:
        user_id = current_user["user_id"]
        
        # Generate thread_id if not provided
        thread_id = request.thread_id or f"thread-{user_id}-{int(datetime.now().timestamp())}"
        
        # Save thread to database
        success = save_thread(
            thread_id=thread_id,
            user_id=user_id,
            name=request.name,
            thread_data=request.thread_data,
            running=request.running if request.running is not None else False
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save thread to database")
        
        # Retrieve saved thread
        thread = get_thread(thread_id)
        
        return ThreadResponse(
            status="success",
            message=f"Thread '{request.name}' saved successfully",
            thread_id=thread_id,
            thread=thread
        )
        
    except HTTPException:
        raise
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving thread: {str(e)}")

@app.get("/api/thread/list")
async def list_threads_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all threads for the current user (token-based).
    """
    try:
        user_id = current_user["user_id"]
        threads = get_user_threads(user_id)
        
        return {
            "status": "success",
            "threads": threads,
            "count": len(threads)
        }
    except HTTPException:
        raise
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing threads: {str(e)}")

@app.get("/api/thread/{thread_id}")
async def get_thread_endpoint(
    thread_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a thread by thread_id (token-based, verifies ownership).
    """
    try:
        user_id = current_user["user_id"]
        thread = get_thread(thread_id)
        
        if not thread:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        
        # Verify user owns the thread
        if thread["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied: thread belongs to another user")
        
        return {
            "status": "success",
            "thread": thread
        }
    except HTTPException:
        raise
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving thread: {str(e)}")

class ThreadRunningRequest(BaseModel):
    """Request to update thread running status"""
    running: bool

@app.put("/api/thread/{thread_id}/running")
async def update_thread_running_endpoint(
    thread_id: str,
    request: ThreadRunningRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update the running status of a thread (token-based).
    """
    try:
        user_id = current_user["user_id"]
        
        # Update thread running status (with user verification)
        success = update_thread_running(thread_id, request.running, user_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Thread running status updated to {request.running}",
                "thread_id": thread_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"Thread not found or permission denied: {thread_id}")
    except HTTPException:
        raise
    except NameError:
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating thread running status: {str(e)}")

@app.post("/api/thread/{thread_id}/start")
async def start_thread_endpoint(
    thread_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Start a thread: save it to database, set running=true, and load into scheduler.
    """
    try:
        user_id = current_user["user_id"]
        
        # Get the thread to verify ownership
        thread = get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        
        # Verify user owns the thread
        if thread.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied: thread belongs to another user")
        
        # Update running status to true
        success = update_thread_running(thread_id, True, user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update thread running status")
        
        # Load thread into scheduler using handle_request
        thread_data = thread.get("thread_data", {})
        # Get timezone from thread_data, or from notification_schedule if nested there
        schedule_info = thread_data.get("notification_schedule", {})
        timezone = thread_data.get("timezone") or schedule_info.get("timezone") or "UTC"
        
        thread_structure = {
            "thread_id": thread_id,
            "name": thread.get("name", "Unnamed Thread"),
            "notification_schedule": schedule_info,
            "interests": thread_data.get("interests", ""),
            "blocks": thread_data.get("blocks", []),
            "timezone": timezone,
            "user_id": user_id,
            "email": current_user.get("email", "")
        }
        
        # Load into scheduler
        handle_request(thread_structure)
        
        return {
            "status": "success",
            "message": f"Thread {thread_id} started and loaded into scheduler",
            "thread_id": thread_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting thread: {str(e)}")

@app.post("/api/thread/{thread_id}/stop")
async def stop_thread_endpoint(
    thread_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Stop a thread: set running=false and remove from scheduler.
    """
    try:
        user_id = current_user["user_id"]
        
        # Update running status to false
        success = update_thread_running(thread_id, False, user_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Thread not found or permission denied: {thread_id}")
        
        # Remove from scheduler
        from thread import _clear_previous_jobs
        _clear_previous_jobs(thread_id)
        
        return {
            "status": "success",
            "message": f"Thread {thread_id} stopped and removed from scheduler",
            "thread_id": thread_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping thread: {str(e)}")

@app.delete("/api/thread/{thread_id}")
async def delete_thread_endpoint(
    thread_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a thread by thread_id (token-based).
    Also removes the thread from scheduler if it's running.
    """
    try:
        user_id = current_user["user_id"]
        
        print(f"\n[DELETE] Initiating deletion for thread_id: {thread_id}, user_id: {user_id}")
        
        # First, check if thread exists and get its running status
        thread = get_thread(thread_id)
        if thread:
            # Verify ownership
            if thread.get("user_id") != user_id:
                print(f"[DELETE] Access denied: thread {thread_id} belongs to another user")
                raise HTTPException(status_code=403, detail="Access denied: thread belongs to another user")
            
            # If thread is running, remove from scheduler first
            if thread.get("running", False):
                print(f"[DELETE] Thread {thread_id} is running. Removing from scheduler...")
                try:
                    from thread import _clear_previous_jobs
                    _clear_previous_jobs(thread_id)
                    print(f"[DELETE] Successfully removed thread {thread_id} from scheduler")
                except Exception as e:
                    print(f"[DELETE] Warning: Failed to remove from scheduler: {e}")
            else:
                print(f"[DELETE] Thread {thread_id} is not running, skipping scheduler cleanup")
        else:
            print(f"[DELETE] Thread {thread_id} not found in database")
        
        # Delete thread from database (with user verification)
        success = delete_thread(thread_id, user_id)
        
        if success:
            print(f"[DELETE] Successfully deleted thread {thread_id} from database")
            return {
                "status": "success",
                "message": f"Thread {thread_id} deleted successfully"
            }
        else:
            print(f"[DELETE] Failed to delete thread {thread_id} from database")
            raise HTTPException(status_code=404, detail=f"Thread not found or permission denied: {thread_id}")
    except HTTPException:
        raise
    except NameError:
        print(f"[DELETE] Error: Database not available")
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        print(f"[DELETE] Error deleting thread {thread_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting thread: {str(e)}")

# =================================================================
# Database Operations Endpoints
# =================================================================

@app.get("/api/db/tables")
async def get_database_tables():
    """
    Get list of all tables in the database.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return {
            "status": "success",
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tables: {str(e)}")

@app.get("/api/db/table/{table_name}/schema")
async def get_table_schema(table_name: str):
    """
    Get schema information for a specific table.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Get indexes
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = cursor.fetchall()
        
        conn.close()
        
        # Format column info
        column_info = []
        for col in columns:
            column_info.append({
                "cid": col[0],
                "name": col[1],
                "type": col[2],
                "notnull": bool(col[3]),
                "default_value": col[4],
                "pk": bool(col[5])
            })
        
        # Format index info
        index_info = []
        for idx in indexes:
            index_info.append({
                "seq": idx[0],
                "name": idx[1],
                "unique": bool(idx[2]),
                "origin": idx[3],
                "partial": bool(idx[4])
            })
        
        return {
            "status": "success",
            "table_name": table_name,
            "columns": column_info,
            "indexes": index_info
        }
    except sqlite3.OperationalError as e:
        raise HTTPException(status_code=404, detail=f"Table not found: {table_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching schema: {str(e)}")

@app.get("/api/db/table/{table_name}/data")
async def get_table_data(
    table_name: str,
    page: int = 1,
    limit: int = 100,
    order_by: Optional[str] = None,
    order_dir: str = "ASC"
):
    """
    Get data from a specific table with pagination.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Validate table name to prevent SQL injection
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name = ?
        """, (table_name,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail=f"Table not found: {table_name}")
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]
        
        # Build query
        offset = (page - 1) * limit
        order_clause = ""
        if order_by:
            # Validate order_by column name
            cursor.execute(f"PRAGMA table_info({table_name})")
            valid_columns = [col[1] for col in cursor.fetchall()]
            if order_by in valid_columns:
                order_dir = "DESC" if order_dir.upper() == "DESC" else "ASC"
                order_clause = f"ORDER BY {order_by} {order_dir}"
        
        query = f"SELECT * FROM {table_name} {order_clause} LIMIT ? OFFSET ?"
        cursor.execute(query, (limit, offset))
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Fetch data
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        data = []
        for row in rows:
            row_dict = {}
            for i, col_name in enumerate(column_names):
                value = row[i]
                # Convert bytes to string if needed
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='ignore')
                # Handle JSON strings
                elif isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
                    try:
                        value = json.loads(value)
                    except:
                        pass
                row_dict[col_name] = value
            data.append(row_dict)
        
        conn.close()
        
        return {
            "status": "success",
            "table_name": table_name,
            "data": data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            },
            "columns": column_names
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

@app.delete("/api/db/table/{table_name}/row")
async def delete_table_row(
    table_name: str,
    primary_key: str = Query(..., description="Primary key column name"),
    primary_key_value: str = Query(..., description="Primary key value")
):
    """
    Delete a row from a table by primary key.
    Query parameters: primary_key, primary_key_value
    """
    try:
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Validate table name
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name = ?
        """, (table_name,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail=f"Table not found: {table_name}")
        
        # Get primary key column
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        pk_column = None
        for col in columns:
            if col[1] == primary_key or col[5]:  # col[5] is pk flag
                pk_column = col[1]
                break
        
        if not pk_column:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Primary key column '{primary_key}' not found")
        
        # Delete row
        query = f"DELETE FROM {table_name} WHERE {pk_column} = ?"
        cursor.execute(query, (primary_key_value,))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Row not found")
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "message": f"Row deleted from {table_name}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting row: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)

