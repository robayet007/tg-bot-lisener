import os
import json
import time
from datetime import datetime

# Debug logging helper
def debug_log(location, message, data=None, hypothesis_id=None):
    """Write debug log to file"""
    try:
        log_path = r"c:\Users\mroba\OneDrive\Desktop\tg-bot-lisener\.cursor\debug.log"
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "location": location,
            "message": message,
            "data": data or {},
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": hypothesis_id
        }
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        # Print to console if file logging fails
        print(f"[DEBUG LOG ERROR] {e}")

# Telegram API Credentials
API_ID = int(os.getenv("API_ID", "37118739"))
API_HASH = os.getenv("API_HASH", "d02baf67c4f5d2e0586236c24e1248d1")

# Bot username to listen to and send messages to (without @)
BOT_USERNAME = os.getenv("BOT_USERNAME", "roboucbot")  # Change this to your target bot username

# Session file name (will be created automatically)
# Use sessions directory if mounted, otherwise current directory
# Check if we're on Fly.io (has /app/sessions) or local (use current directory)
if os.getenv("SESSION_DIR"):
    SESSION_DIR = os.getenv("SESSION_DIR")
elif os.path.exists("/app/sessions"):
    # Fly.io environment
    SESSION_DIR = "/app/sessions"
else:
    # Local development - use current directory
    SESSION_DIR = "."

SESSION_NAME = os.path.join(SESSION_DIR, os.getenv("SESSION_NAME", "telegram_listener"))

# MongoDB Configuration
# MONGODB_URI is required for production (MongoDB Atlas or remote MongoDB)
# Format: mongodb+srv://username:password@cluster.mongodb.net/?appName=Cluster
# Default URI (can be overridden by MONGODB_URI environment variable)
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://robayet:8WVzWixH4rS1uwBX@cluster0.lrzc2.mongodb.net/?appName=Cluster")

# Legacy MongoDB settings (deprecated - use MONGODB_URI instead)
# These are kept for backward compatibility but should not be used
MONGODB_HOST = os.getenv("MONGODB_HOST", None)
MONGODB_PORT = os.getenv("MONGODB_PORT", None)
if MONGODB_PORT:
    MONGODB_PORT = int(MONGODB_PORT)

MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "telegram_bot")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "bot_messages")


# Helper functions
def get_session_file_path():
    """Get the full path to the session file."""
    return SESSION_NAME + ".session"


def session_file_exists():
    """Check if the session file exists."""
    session_path = get_session_file_path()
    return os.path.exists(session_path)


def get_session_file_info():
    """Get information about the session file."""
    session_path = get_session_file_path()
    info = {
        "path": session_path,
        "exists": False,
        "size": 0,
        "modified": None
    }
    
    if os.path.exists(session_path):
        info["exists"] = True
        try:
            stat = os.stat(session_path)
            info["size"] = stat.st_size
            info["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except Exception as e:
            info["error"] = str(e)
    
    return info


def delete_session_file():
    """Delete the session file.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    session_path = get_session_file_path()
    if not os.path.exists(session_path):
        return False, f"Session file does not exist: {session_path}"
    
    try:
        # Get file size before deletion for logging
        file_size = os.path.getsize(session_path)
        os.remove(session_path)
        return True, f"Deleted session file: {session_path} ({file_size} bytes)"
    except Exception as e:
        return False, f"Error deleting session file {session_path}: {e}"


def delete_session_file_safe():
    """Safely delete the session file and its journal file if it exists.
    
    This function handles errors gracefully and also deletes the session journal file.
    
    Returns:
        tuple: (success: bool, deleted_files: list, errors: list)
    """
    # #region agent log
    debug_log("config.py:95", "delete_session_file_safe() called", {}, "E")
    # #endregion
    deleted_files = []
    errors = []
    
    # Delete main session file
    session_path = get_session_file_path()
    # #region agent log
    file_exists = os.path.exists(session_path)
    file_age = None
    if file_exists:
        try:
            mod_time = os.path.getmtime(session_path)
            file_age = (time.time() - mod_time) if 'time' in globals() else None
        except:
            pass
    debug_log("config.py:108", "Before deleting session file", {
        "session_path": session_path,
        "file_exists": file_exists,
        "file_age_seconds": file_age
    }, "E")
    # #endregion
    if os.path.exists(session_path):
        try:
            file_size = os.path.getsize(session_path)
            os.remove(session_path)
            deleted_files.append(f"{session_path} ({file_size} bytes)")
            # #region agent log
            debug_log("config.py:111", "Session file deleted", {"file_size": file_size, "path": session_path}, "E")
            # #endregion
        except Exception as e:
            errors.append(f"Error deleting {session_path}: {e}")
            # #region agent log
            debug_log("config.py:114", "Error deleting session file", {"error": str(e), "error_type": type(e).__name__}, "E")
            # #endregion
    
    # Delete session journal file if it exists
    journal_path = session_path + "-journal"
    if os.path.exists(journal_path):
        try:
            journal_size = os.path.getsize(journal_path)
            os.remove(journal_path)
            deleted_files.append(f"{journal_path} ({journal_size} bytes)")
        except Exception as e:
            errors.append(f"Error deleting {journal_path}: {e}")
    
    success = len(deleted_files) > 0 and len(errors) == 0
    # #region agent log
    debug_log("config.py:127", "delete_session_file_safe() completed", {
        "success": success,
        "deleted_count": len(deleted_files),
        "error_count": len(errors)
    }, "E")
    # #endregion
    return success, deleted_files, errors

