"""
Clear MongoDB collection to remove old data with line_number field
"""
from pymongo import MongoClient
import config

try:
    client = MongoClient(host=config.MONGODB_HOST, port=config.MONGODB_PORT)
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

