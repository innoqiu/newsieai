"""
Database initialization and connection management for NewsieAI.
Uses SQLite for local storage of user profiles.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

# Get database path from environment or use default
BASE_DIR = Path(__file__).resolve().parent
DB_PATH_ENV = os.getenv("DATABASE_PATH")
if DB_PATH_ENV:
    DB_PATH = Path(DB_PATH_ENV)
else:
    # Default: store in backend/data directory
    DB_PATH = BASE_DIR / "data" / "newsieai.db"

# Ensure data directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Password hashing context
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    pwd_context = None
    print("Warning: passlib not installed. Password hashing will not work.")


def init_database():
    """
    Initialize the SQLite database and create tables if they don't exist.
    Enables WAL mode for better concurrent access.
    """
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # Set other performance optimizations
    cursor.execute("PRAGMA synchronous=NORMAL")  # Faster than FULL, still safe
    cursor.execute("PRAGMA cache_size=10000")  # Increase cache size
    cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
    
    # Create users table for authentication and credits
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            credits DECIMAL(10, 2) DEFAULT 0.00,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index on email for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
    """)
    
    # Create user_profiles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            timezone TEXT DEFAULT 'UTC',
            preferred_notification_times TEXT,  -- JSON array as string
            content_preferences TEXT,  -- JSON array as string
            x_usernames TEXT,  -- JSON array as string (e.g., ["@elonmusk", "@openai"])
            description TEXT,  -- JSON array of strings summarizing user preferences/comments
            schedua_list TEXT,  -- JSON array of schedule slots
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    
    # Add x_usernames column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE user_profiles ADD COLUMN x_usernames TEXT")
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass
    
    # Add description column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE user_profiles ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass
    
    # Add schedua_list column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE user_profiles ADD COLUMN schedua_list TEXT")
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass
    
    # Create index on email for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_email ON user_profiles(email)
    """)
    
    # Create news_reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_reports (
            report_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            report_date DATE NOT NULL,
            total_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
        )
    """)
    
    # Create news_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT NOT NULL,
            news_body TEXT NOT NULL,
            url TEXT,
            is_starred BOOLEAN DEFAULT 0,
            FOREIGN KEY (report_id) REFERENCES news_reports(report_id) ON DELETE CASCADE
        )
    """)
    
    # Create indexes for better query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_reports_user_date 
        ON news_reports(user_id, report_date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_items_report 
        ON news_items(report_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_items_starred 
        ON news_items(is_starred)
    """)
    
    # Create workflows table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            workflow_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            version TEXT DEFAULT '1.0.0',
            nodes TEXT NOT NULL,  -- JSON string
            edges TEXT NOT NULL,  -- JSON string
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    
    # Create indexes for workflows
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_workflows_user 
        ON workflows(user_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_workflows_user_active 
        ON workflows(user_id, is_active)
    """)
    
    # Create threads table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            thread_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            thread_data TEXT NOT NULL,  -- JSON string storing the thread structure (blocks)
            running BOOLEAN DEFAULT 0,  -- Whether the thread is currently running
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    
    # Add running column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE threads ADD COLUMN running BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass
    
    # Create indexes for threads
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_threads_user 
        ON threads(user_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_threads_user_updated 
        ON threads(user_id, updated_at)
    """)
    
    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH} (WAL mode enabled)")


def get_connection():
    """
    Get a database connection with WAL mode enabled for better concurrency.
    
    Returns:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    
    # Ensure WAL mode and foreign keys are enabled (in case they weren't set during init)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error:
        pass  # Ignore if already set or not supported
    
    return conn


def save_user_profile(profile: Dict[str, Any]) -> bool:
    """
    Save or update a user profile in the database.
    
    Args:
        profile: User profile dictionary with keys:
            - user_id: str
            - name: str
            - email: str
            - timezone: str (default: UTC)
            - preferred_notification_times: List[str]
            - content_preferences: List[str]
            - description: List[str] (optional, LLM summaries of user preferences/comments)
            - schedua_list: List[Any] (optional, schedule slots)
            - x_usernames: List[str] (optional, e.g., ["@elonmusk", "@openai"])
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Convert lists to JSON strings
        notification_times_json = json.dumps(profile.get("preferred_notification_times", []))
        content_prefs_json = json.dumps(profile.get("content_preferences", []))
        description_json = json.dumps(profile.get("description", []))
        schedua_list_json = json.dumps(profile.get("schedua_list", []))
        x_usernames_json = json.dumps(profile.get("x_usernames", []))
        
        # Check if user exists
        cursor.execute("SELECT user_id FROM user_profiles WHERE user_id = ?", (profile["user_id"],))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing profile
            cursor.execute("""
                UPDATE user_profiles
                SET name = ?,
                    email = ?,
                    timezone = ?,
                    preferred_notification_times = ?,
                    content_preferences = ?,
                    x_usernames = ?,
                    description = ?,
                    schedua_list = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (
                profile["name"],
                profile["email"],
                profile.get("timezone", "UTC"),
                notification_times_json,
                content_prefs_json,
                x_usernames_json,
                description_json,
                schedua_list_json,
                profile["user_id"]
            ))
        else:
            # Insert new profile
            cursor.execute("""
                INSERT INTO user_profiles 
                (user_id, name, email, timezone, preferred_notification_times, content_preferences, x_usernames, description, schedua_list)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile["user_id"],
                profile["name"],
                profile["email"],
                profile.get("timezone", "UTC"),
                notification_times_json,
                content_prefs_json,
                x_usernames_json,
                description_json,
                schedua_list_json
            ))
        
        conn.commit()
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error saving profile: {e}")
        return False


def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user profile by user_id.
    
    Args:
        user_id: User identifier
    
    Returns:
        Dict with user profile or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM user_profiles WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Convert row to dictionary
            profile = dict(row)
            # Parse JSON strings back to lists
            profile["preferred_notification_times"] = json.loads(
                profile.get("preferred_notification_times") or "[]"
            )
            profile["content_preferences"] = json.loads(
                profile.get("content_preferences") or "[]"
            )
            profile["x_usernames"] = json.loads(
                profile.get("x_usernames") or "[]"
            )
            profile["description"] = json.loads(
                profile.get("description") or "[]"
            )
            profile["schedua_list"] = json.loads(
                profile.get("schedua_list") or "[]"
            )
            return profile
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Error retrieving profile: {e}")
        return None


def get_user_profile_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user profile by email.
    
    Args:
        email: User email address
    
    Returns:
        Dict with user profile or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM user_profiles WHERE email = ?
        """, (email,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            profile = dict(row)
            profile["preferred_notification_times"] = json.loads(
                profile.get("preferred_notification_times") or "[]"
            )
            profile["content_preferences"] = json.loads(
                profile.get("content_preferences") or "[]"
            )
            profile["x_usernames"] = json.loads(
                profile.get("x_usernames") or "[]"
            )
            profile["description"] = json.loads(
                profile.get("description") or "[]"
            )
            profile["schedua_list"] = json.loads(
                profile.get("schedua_list") or "[]"
            )
            return profile
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Error retrieving profile: {e}")
        return None


def list_all_profiles() -> List[Dict[str, Any]]:
    """
    List all user profiles in the database.
    
    Returns:
        List of user profile dictionaries
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_profiles ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        profiles = []
        for row in rows:
            profile = dict(row)
            profile["preferred_notification_times"] = json.loads(
                profile.get("preferred_notification_times") or "[]"
            )
            profile["content_preferences"] = json.loads(
                profile.get("content_preferences") or "[]"
            )
            profile["description"] = json.loads(
                profile.get("description") or "[]"
            )
            profile["schedua_list"] = json.loads(
                profile.get("schedua_list") or "[]"
            )
            profiles.append(profile)
        
        return profiles
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    except Exception as e:
        print(f"Error listing profiles: {e}")
        return []


# =================================================================
# News History Functions
# =================================================================

def save_news_report(report_id: str, user_id: str, report_date: str, total_summary: str) -> bool:
    """
    Insert or update a news_report.
    If report_id already exists, update its total_summary.
    
    Args:
        report_id: Unique identifier for the news report
        user_id: User identifier (must exist in user_profiles)
        report_date: Date of the report (format: YYYY-MM-DD)
        total_summary: Summary text for the entire report
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if report exists
        cursor.execute("SELECT report_id FROM news_reports WHERE report_id = ?", (report_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing report
            cursor.execute("""
                UPDATE news_reports
                SET total_summary = ?,
                    report_date = ?
                WHERE report_id = ?
            """, (total_summary, report_date, report_id))
        else:
            # Insert new report
            cursor.execute("""
                INSERT INTO news_reports (report_id, user_id, report_date, total_summary)
                VALUES (?, ?, ?, ?)
            """, (report_id, user_id, report_date, total_summary))
        
        conn.commit()
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Database error saving news report: {e}")
        return False
    except Exception as e:
        print(f"Error saving news report: {e}")
        return False


def save_news_items(report_id: str, items: List[Dict[str, Any]]) -> bool:
    """
    Insert multiple news_items for the given report_id.
    
    Args:
        report_id: Report identifier (must exist in news_reports)
        items: List of dictionaries, each containing:
            - news_body: str (required)
            - url: str (optional)
            - is_starred: bool (optional, default False)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        for item in items:
            news_body = item.get("news_body", "")
            url = item.get("url")
            is_starred = 1 if item.get("is_starred", False) else 0
            
            cursor.execute("""
                INSERT INTO news_items (report_id, news_body, url, is_starred)
                VALUES (?, ?, ?, ?)
            """, (report_id, news_body, url, is_starred))
        
        conn.commit()
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Database error saving news items: {e}")
        return False
    except Exception as e:
        print(f"Error saving news items: {e}")
        return False


def get_latest_news_for_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Query the most recent news_report for this user and return a structured dict
    including total_summary and a list of news_items.
    
    Args:
        user_id: User identifier
    
    Returns:
        Dict with keys: report_id, user_id, report_date, total_summary, 
        created_at, items (list of news_items), or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get the most recent report for this user
        cursor.execute("""
            SELECT report_id, user_id, report_date, total_summary, created_at
            FROM news_reports
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        report_row = cursor.fetchone()
        
        if not report_row:
            conn.close()
            return None
        
        # Convert report row to dict
        report = {
            "report_id": report_row["report_id"],
            "user_id": report_row["user_id"],
            "report_date": report_row["report_date"],
            "total_summary": report_row["total_summary"],
            "created_at": report_row["created_at"],
            "items": []
        }
        
        # Get all news items for this report
        cursor.execute("""
            SELECT id, news_body, url, is_starred
            FROM news_items
            WHERE report_id = ?
            ORDER BY id
        """, (report["report_id"],))
        
        item_rows = cursor.fetchall()
        
        for item_row in item_rows:
            report["items"].append({
                "id": item_row["id"],
                "news_body": item_row["news_body"],
                "url": item_row["url"],
                "is_starred": bool(item_row["is_starred"])
            })
        
        conn.close()
        return report
        
    except sqlite3.Error as e:
        print(f"Database error retrieving latest news: {e}")
        return None
    except Exception as e:
        print(f"Error retrieving latest news: {e}")
        return None


def get_news_by_date(user_id: str, report_date: str) -> Optional[Dict[str, Any]]:
    """
    Query a news report for a given user on a specific date, including its items.
    
    Args:
        user_id: User identifier
        report_date: Date in format YYYY-MM-DD
    
    Returns:
        Dict with keys: report_id, user_id, report_date, total_summary,
        created_at, items (list of news_items), or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get the report for this user and date
        cursor.execute("""
            SELECT report_id, user_id, report_date, total_summary, created_at
            FROM news_reports
            WHERE user_id = ? AND report_date = ?
        """, (user_id, report_date))
        
        report_row = cursor.fetchone()
        
        if not report_row:
            conn.close()
            return None
        
        # Convert report row to dict
        report = {
            "report_id": report_row["report_id"],
            "user_id": report_row["user_id"],
            "report_date": report_row["report_date"],
            "total_summary": report_row["total_summary"],
            "created_at": report_row["created_at"],
            "items": []
        }
        
        # Get all news items for this report
        cursor.execute("""
            SELECT id, news_body, url, is_starred
            FROM news_items
            WHERE report_id = ?
            ORDER BY id
        """, (report["report_id"],))
        
        item_rows = cursor.fetchall()
        
        for item_row in item_rows:
            report["items"].append({
                "id": item_row["id"],
                "news_body": item_row["news_body"],
                "url": item_row["url"],
                "is_starred": bool(item_row["is_starred"])
            })
        
        conn.close()
        return report
        
    except sqlite3.Error as e:
        print(f"Database error retrieving news by date: {e}")
        return None
    except Exception as e:
        print(f"Error retrieving news by date: {e}")
        return None


def update_starred(item_id: int, is_starred: bool) -> Optional[Dict[str, Any]]:
    """
    Update the is_starred flag for a news_item and return the updated item.
    
    Args:
        item_id: News item identifier
        is_starred: Boolean value to set
    
    Returns:
        Dict with the updated news item (id, report_id, news_body, url, is_starred),
        or None if item not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Update the starred status
        starred_value = 1 if is_starred else 0
        cursor.execute("""
            UPDATE news_items
            SET is_starred = ?
            WHERE id = ?
        """, (starred_value, item_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return None
        
        # Fetch the updated item
        cursor.execute("""
            SELECT id, report_id, news_body, url, is_starred
            FROM news_items
            WHERE id = ?
        """, (item_id,))
        
        item_row = cursor.fetchone()
        conn.commit()
        conn.close()
        
        if item_row:
            return {
                "id": item_row["id"],
                "report_id": item_row["report_id"],
                "news_body": item_row["news_body"],
                "url": item_row["url"],
                "is_starred": bool(item_row["is_starred"])
            }
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error updating starred status: {e}")
        return None
    except Exception as e:
        print(f"Error updating starred status: {e}")
        return None


def get_starred_news_for_user(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all starred news items for a specific user.
    
    Args:
        user_id: User identifier
    
    Returns:
        List of dictionaries, each containing:
        - id: News item identifier
        - report_id: Report identifier
        - news_body: News headline/summary
        - url: Link to the news
        - is_starred: Boolean (always True for starred items)
        - report_date: Date of the report
        - total_summary: Summary of the report (optional)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Join news_items with news_reports to filter by user_id and get starred items
        cursor.execute("""
            SELECT 
                ni.id,
                ni.report_id,
                ni.news_body,
                ni.url,
                ni.is_starred,
                nr.report_date,
                nr.total_summary
            FROM news_items ni
            INNER JOIN news_reports nr ON ni.report_id = nr.report_id
            WHERE nr.user_id = ? AND ni.is_starred = 1
            ORDER BY nr.report_date DESC, ni.id
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        starred_items = []
        for row in rows:
            starred_items.append({
                "id": row["id"],
                "report_id": row["report_id"],
                "news_body": row["news_body"],
                "url": row["url"],
                "is_starred": bool(row["is_starred"]),
                "report_date": row["report_date"],
                "total_summary": row["total_summary"]
            })
        
        return starred_items
        
    except sqlite3.Error as e:
        print(f"Database error retrieving starred news: {e}")
        return []
    except Exception as e:
        print(f"Error retrieving starred news: {e}")
        return []


# =================================================================
# Workflow Functions
# =================================================================

def save_workflow(workflow_id: str, user_id: str, name: str, nodes: List[Dict[str, Any]], 
                 edges: List[Dict[str, Any]], version: str = "1.0.0") -> bool:
    """
    Save or update a workflow in the database.
    
    Args:
        workflow_id: Unique identifier for the workflow
        user_id: User identifier (must exist in user_profiles)
        name: Workflow name
        nodes: List of node dictionaries
        edges: List of edge dictionaries
        version: Workflow version (default: "1.0.0")
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Convert nodes and edges to JSON strings
        nodes_json = json.dumps(nodes)
        edges_json = json.dumps(edges)
        
        # Check if workflow exists
        cursor.execute("SELECT workflow_id FROM workflows WHERE workflow_id = ?", (workflow_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing workflow
            cursor.execute("""
                UPDATE workflows
                SET name = ?,
                    nodes = ?,
                    edges = ?,
                    version = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE workflow_id = ?
            """, (name, nodes_json, edges_json, version, workflow_id))
        else:
            # Insert new workflow
            cursor.execute("""
                INSERT INTO workflows (workflow_id, user_id, name, version, nodes, edges)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (workflow_id, user_id, name, version, nodes_json, edges_json))
        
        conn.commit()
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Database error saving workflow: {e}")
        return False
    except Exception as e:
        print(f"Error saving workflow: {e}")
        return False


def get_workflow(workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a workflow by workflow_id.
    
    Args:
        workflow_id: Workflow identifier
    
    Returns:
        Dict with workflow data or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM workflows WHERE workflow_id = ?
        """, (workflow_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            workflow = dict(row)
            # Parse JSON strings back to lists
            workflow["nodes"] = json.loads(workflow["nodes"])
            workflow["edges"] = json.loads(workflow["edges"])
            return workflow
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error retrieving workflow: {e}")
        return None
    except Exception as e:
        print(f"Error retrieving workflow: {e}")
        return None


def get_user_workflows(user_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
    """
    Get all workflows for a specific user.
    
    Args:
        user_id: User identifier
        include_inactive: Whether to include inactive workflows
    
    Returns:
        List of workflow dictionaries
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if include_inactive:
            cursor.execute("""
                SELECT workflow_id, user_id, name, version, created_at, updated_at, is_active
                FROM workflows
                WHERE user_id = ?
                ORDER BY updated_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT workflow_id, user_id, name, version, created_at, updated_at, is_active
                FROM workflows
                WHERE user_id = ? AND is_active = 1
                ORDER BY updated_at DESC
            """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        workflows = []
        for row in rows:
            workflows.append(dict(row))
        
        return workflows
        
    except sqlite3.Error as e:
        print(f"Database error retrieving user workflows: {e}")
        return []
    except Exception as e:
        print(f"Error retrieving user workflows: {e}")
        return []


def delete_workflow(workflow_id: str, user_id: Optional[str] = None) -> bool:
    """
    Delete a workflow by workflow_id. Optionally verify user_id for security.
    
    Args:
        workflow_id: Workflow identifier
        user_id: Optional user identifier for verification
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if user_id:
            # Verify user owns the workflow
            cursor.execute("""
                DELETE FROM workflows 
                WHERE workflow_id = ? AND user_id = ?
            """, (workflow_id, user_id))
        else:
            cursor.execute("""
                DELETE FROM workflows 
                WHERE workflow_id = ?
            """, (workflow_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
        
    except sqlite3.Error as e:
        print(f"Database error deleting workflow: {e}")
        return False
    except Exception as e:
        print(f"Error deleting workflow: {e}")
        return False


def deactivate_workflow(workflow_id: str, user_id: Optional[str] = None) -> bool:
    """
    Deactivate a workflow instead of deleting it.
    
    Args:
        workflow_id: Workflow identifier
        user_id: Optional user identifier for verification
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                UPDATE workflows
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE workflow_id = ? AND user_id = ?
            """, (workflow_id, user_id))
        else:
            cursor.execute("""
                UPDATE workflows
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE workflow_id = ?
            """, (workflow_id,))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
        
    except sqlite3.Error as e:
        print(f"Database error deactivating workflow: {e}")
        return False
    except Exception as e:
        print(f"Error deactivating workflow: {e}")
        return False


# =================================================================
# Authentication Functions
# =================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password
    """
    if not pwd_context:
        raise ImportError("passlib is not installed. Please install it to use password hashing.")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
    
    Returns:
        bool: True if password matches, False otherwise
    """
    if not pwd_context:
        raise ImportError("passlib is not installed. Please install it to use password verification.")
    return pwd_context.verify(plain_password, hashed_password)


def create_user(email: str, password: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Create a new user account with hashed password.
    
    Args:
        email: User email address
        password: Plain text password
        user_id: Optional user ID (if None, generated from email)
    
    Returns:
        Dict with user data or None if creation failed
    """
    try:
        if not pwd_context:
            raise ImportError("passlib is not installed.")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Generate user_id if not provided
        if not user_id:
            user_id = email.split("@")[0]
        
        # Check if user already exists
        cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return None  # User already exists
        
        # Hash password
        print(f"Hashing password: {password}")
        password_hash = hash_password(password)
        
        # Insert new user
        cursor.execute("""
            INSERT INTO users (user_id, email, password_hash, credits)
            VALUES (?, ?, ?, ?)
        """, (user_id, email, password_hash, 0.00))
        
        conn.commit()
        
        # Retrieve created user
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            user = dict(row)
            # Remove password hash from returned data
            user.pop("password_hash", None)
            return user
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error creating user: {e}")
        return None
    except Exception as e:
        print(f"Error creating user: {e}")
        return None


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user by email and password.
    
    Args:
        email: User email address
        password: Plain text password
    
    Returns:
        Dict with user data (without password_hash) or None if authentication failed
    """
    try:
        if not pwd_context:
            raise ImportError("passlib is not installed.")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user by email
        cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        user = dict(row)
        password_hash = user["password_hash"]
        
        # Verify password
        if not verify_password(password, password_hash):
            return None
        
        # Remove password hash from returned data
        user.pop("password_hash", None)
        return user
        
    except sqlite3.Error as e:
        print(f"Database error authenticating user: {e}")
        return None
    except Exception as e:
        print(f"Error authenticating user: {e}")
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by user_id.
    
    Args:
        user_id: User identifier
    
    Returns:
        Dict with user data (without password_hash) or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ? AND is_active = 1", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            user = dict(row)
            user.pop("password_hash", None)
            return user
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error getting user: {e}")
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email.
    
    Args:
        email: User email address
    
    Returns:
        Dict with user data (without password_hash) or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            user = dict(row)
            user.pop("password_hash", None)
            return user
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error getting user: {e}")
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def update_user_credits(user_id: str, credits: float) -> bool:
    """
    Update user credits.
    
    Args:
        user_id: User identifier
        credits: New credits amount
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users
            SET credits = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (credits, user_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
        
    except sqlite3.Error as e:
        print(f"Database error updating credits: {e}")
        return False
    except Exception as e:
        print(f"Error updating credits: {e}")
        return False


def add_user_credits(user_id: str, amount: float) -> bool:
    """
    Add credits to user account.
    
    Args:
        user_id: User identifier
        amount: Amount to add
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get current credits
        cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        current_credits = float(row["credits"])
        new_credits = current_credits + amount
        
        # Update credits
        cursor.execute("""
            UPDATE users
            SET credits = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (new_credits, user_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
        
    except sqlite3.Error as e:
        print(f"Database error adding credits: {e}")
        return False
    except Exception as e:
        print(f"Error adding credits: {e}")
        return False


# =================================================================
# Thread Functions
# =================================================================

def save_thread(thread_id: str, user_id: str, name: str, thread_data: Dict[str, Any], running: bool = False) -> bool:
    """
    Save or update a thread in the database.
    
    Args:
        thread_id: Unique identifier for the thread
        user_id: User identifier (must exist in users)
        name: Thread name
        thread_data: Thread structure dictionary (will be stored as JSON string)
        running: Whether the thread is currently running (default: False)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Convert thread_data to JSON string
        thread_data_json = json.dumps(thread_data)
        running_value = 1 if running else 0
        
        # Check if thread exists
        cursor.execute("SELECT thread_id FROM threads WHERE thread_id = ?", (thread_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing thread (preserve running status unless explicitly set)
            cursor.execute("""
                UPDATE threads
                SET name = ?,
                    thread_data = ?,
                    running = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ?
            """, (name, thread_data_json, running_value, thread_id))
        else:
            # Insert new thread
            cursor.execute("""
                INSERT INTO threads (thread_id, user_id, name, thread_data, running)
                VALUES (?, ?, ?, ?, ?)
            """, (thread_id, user_id, name, thread_data_json, running_value))
        
        conn.commit()
        conn.close()
        print(f"Thread saved: {thread_id}, {user_id}, {name}, {thread_data_json}, {running_value}")
        return True
        
    except sqlite3.Error as e:
        print(f"Database error saving thread: {e}")
        return False
    except Exception as e:
        print(f"Error saving thread: {e}")
        return False


def get_thread(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a thread by thread_id.
    
    Args:
        thread_id: Thread identifier
    
    Returns:
        Dict with thread data or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM threads WHERE thread_id = ?
        """, (thread_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            thread = dict(row)
            # Parse JSON string back to dict
            thread["thread_data"] = json.loads(thread["thread_data"])
            # Convert running from integer (0/1) to boolean
            thread["running"] = bool(thread.get("running", 0))
            return thread
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error retrieving thread: {e}")
        return None
    except Exception as e:
        print(f"Error retrieving thread: {e}")
        return None


def get_user_threads(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all threads for a specific user.
    
    Args:
        user_id: User identifier
    
    Returns:
        List of thread dictionaries
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT thread_id, user_id, name, running, created_at, updated_at
            FROM threads
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        threads = []
        for row in rows:
            thread = dict(row)
            # Convert running from integer (0/1) to boolean
            thread["running"] = bool(thread.get("running", 0))
            threads.append(thread)
        
        return threads
        
    except sqlite3.Error as e:
        print(f"Database error retrieving user threads: {e}")
        return []
    except Exception as e:
        print(f"Error retrieving user threads: {e}")
        return []


def update_thread_running(thread_id: str, running: bool, user_id: Optional[str] = None) -> bool:
    """
    Update the running status of a thread.
    
    Args:
        thread_id: Thread identifier
        running: Whether the thread is running
        user_id: Optional user identifier for verification
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        running_value = 1 if running else 0
        
        if user_id:
            # Verify user owns the thread
            cursor.execute("""
                UPDATE threads
                SET running = ?, updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ?
            """, (running_value, thread_id, user_id))
        else:
            cursor.execute("""
                UPDATE threads
                SET running = ?, updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ?
            """, (running_value, thread_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
        
    except sqlite3.Error as e:
        print(f"Database error updating thread running status: {e}")
        return False
    except Exception as e:
        print(f"Error updating thread running status: {e}")
        return False


def delete_thread(thread_id: str, user_id: Optional[str] = None) -> bool:
    """
    Delete a thread by thread_id. Optionally verify user_id for security.
    
    Args:
        thread_id: Thread identifier
        user_id: Optional user identifier for verification
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if user_id:
            # Verify user owns the thread
            cursor.execute("""
                DELETE FROM threads 
                WHERE thread_id = ? AND user_id = ?
            """, (thread_id, user_id))
        else:
            cursor.execute("""
                DELETE FROM threads 
                WHERE thread_id = ?
            """, (thread_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
        
    except sqlite3.Error as e:
        print(f"Database error deleting thread: {e}")
        return False
    except Exception as e:
        print(f"Error deleting thread: {e}")
        return False


if __name__ == "__main__":
    # Initialize database when run directly
    print("Initializing NewsieAI database...")
    init_database()
    print("Database initialization complete!")

