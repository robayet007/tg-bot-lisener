"""
Clear MongoDB collection to remove old data with line_number field
"""
from pymongo import MongoClient
import config
import sys

try:
    # MONGODB_URI is required
    if not config.MONGODB_URI:
        print("ERROR: MONGODB_URI environment variable is required.")
        print("Please set it to your MongoDB connection string (e.g., mongodb+srv://user:pass@cluster.mongodb.net/).")
        sys.exit(1)
    
    print("Connecting to MongoDB using URI...")
    client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
    
    # Test connection
    client.server_info()
    
    db = client[config.MONGODB_DATABASE]
    collection = db[config.MONGODB_COLLECTION]
    
    # Count documents before deletion
    count_before = collection.count_documents({})
    
    # Delete all documents
    result = collection.delete_many({})
    
    print(f"✓ Cleared {result.deleted_count} documents from {config.MONGODB_DATABASE}.{config.MONGODB_COLLECTION}")
    print(f"  (Found {count_before} documents before clearing)")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

