import os
from datetime import datetime

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

