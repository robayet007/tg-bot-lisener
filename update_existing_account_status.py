"""
Update existing MongoDB documents with parsed account_status
Run this script to parse and add account_status to existing messages
"""

from pymongo import MongoClient
import config
import re
import sys


def parse_account_status(text):
    """Parse account status from bot response."""
    if not text:
        return None
    
    # More robust patterns that handle Unicode characters
    name_pattern = r'[➪➤►]\s*N.*?[aA].*?[mM].*?[eE]\s*[:：]\s*(.+?)(?:\n|$)'
    due_pattern = r'[➪➤►]\s*D.*?[uU].*?[eE]\s*[:：]\s*([\d.]+)\s*([Tt][Kk]|[Tt]aka)?'
    balance_pattern = r'[➪➤►]\s*B.*?[aA].*?[lL].*?[aA].*?[nN].*?[cC].*?[eE]\s*[:：]\s*([\d.]+)\s*([Tt][Kk]|[Tt]aka)?'
    due_limit_pattern = r'[➪➤►]\s*D.*?[uU].*?[eE]\s*L.*?[iI].*?[mM].*?[iI].*?[tT]\s*[:：]\s*([\d.]+)\s*([Tt][Kk]|[Tt]aka)?'
    
    name_match = re.search(name_pattern, text, re.IGNORECASE | re.MULTILINE)
    due_match = re.search(due_pattern, text, re.IGNORECASE | re.MULTILINE)
    balance_match = re.search(balance_pattern, text, re.IGNORECASE | re.MULTILINE)
    due_limit_match = re.search(due_limit_pattern, text, re.IGNORECASE | re.MULTILINE)
    
    if not name_match:
        return None
    
    currency = "Tk"
    if due_match and len(due_match.groups()) > 1 and due_match.group(2):
        currency = due_match.group(2).strip()
    elif balance_match and len(balance_match.groups()) > 1 and balance_match.group(2):
        currency = balance_match.group(2).strip()
    elif due_limit_match and len(due_limit_match.groups()) > 1 and due_limit_match.group(2):
        currency = due_limit_match.group(2).strip()
    
    account_status = {
        "user": {
            "name": name_match.group(1).strip()
        },
        "wallet": {},
        "currency": currency
    }
    
    if due_match:
        try:
            account_status["wallet"]["due"] = float(due_match.group(1))
        except (ValueError, IndexError):
            pass
    
    if balance_match:
        try:
            account_status["wallet"]["balance"] = float(balance_match.group(1))
        except (ValueError, IndexError):
            pass
    
    if due_limit_match:
        try:
            account_status["wallet"]["dueLimit"] = float(due_limit_match.group(1))
        except (ValueError, IndexError):
            pass
    
    if account_status["wallet"]:
        return account_status
    
    return None


def main():
    """Update existing documents with account_status."""
    try:
        # MONGODB_URI is required
        if not config.MONGODB_URI:
            print("ERROR: MONGODB_URI environment variable is required.")
            print("Please set it to your MongoDB connection string (e.g., mongodb+srv://user:pass@cluster.mongodb.net/).")
            sys.exit(1)
        
        print("Connecting to MongoDB using URI...")
        client = MongoClient(
            config.MONGODB_URI,
            serverSelectionTimeoutMS=5000
        )
        client.server_info()
        
        db = client[config.MONGODB_DATABASE]
        collection = db[config.MONGODB_COLLECTION]
        
        print(f"Connected to MongoDB: {config.MONGODB_DATABASE}.{config.MONGODB_COLLECTION}")
        
        # Find all documents without account_status
        documents = collection.find({"account_status": {"$exists": False}})
        total = collection.count_documents({"account_status": {"$exists": False}})
        
        print(f"\nFound {total} documents without account_status")
        print("Processing...\n")
        
        updated = 0
        parsed = 0
        
        for doc in documents:
            text = doc.get("text", "")
            if not text:
                continue
            
            account_status = parse_account_status(text)
            
            if account_status:
                result = collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"account_status": account_status}}
                )
                if result.modified_count > 0:
                    updated += 1
                    parsed += 1
                    print(f"✓ Updated message_id {doc.get('message_id')}: {account_status['user']['name']}")
            else:
                # Check if it looks like account status format but didn't parse
                if "➪" in text and ("N" in text or "n" in text) and ("D" in text or "d" in text):
                    print(f"⚠ Could not parse message_id {doc.get('message_id')} (might need manual review)")
        
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Total documents checked: {total}")
        print(f"  Successfully parsed: {parsed}")
        print(f"  Updated: {updated}")
        print(f"{'='*60}\n")
        
        client.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


