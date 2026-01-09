"""
Script to check health endpoint and diagnose bot listener initialization issues.
Usage: python check_health.py [url]
Default URL: https://tg-bot-lisener.fly.dev
"""

import sys
import json
import requests
from urllib.parse import urlparse

def check_health(base_url="https://tg-bot-lisener.fly.dev"):
    """Check health endpoint and display diagnostics."""
    try:
        # Check health endpoint
        health_url = f"{base_url}/health"
        print(f"Checking health endpoint: {health_url}")
        response = requests.get(health_url, timeout=10)
        response.raise_for_status()
        health_data = response.json()
        
        print("\n" + "="*80)
        print("HEALTH CHECK RESULTS")
        print("="*80)
        print(json.dumps(health_data, indent=2))
        
        # Check status endpoint for more details
        status_url = f"{base_url}/api/status"
        print(f"\nChecking status endpoint: {status_url}")
        status_response = requests.get(status_url, timeout=10)
        status_response.raise_for_status()
        status_data = status_response.json()
        
        print("\n" + "="*80)
        print("DETAILED STATUS")
        print("="*80)
        print(json.dumps(status_data, indent=2))
        
        # Analyze and provide recommendations
        print("\n" + "="*80)
        print("DIAGNOSIS & RECOMMENDATIONS")
        print("="*80)
        
        if health_data.get("bot_initialized"):
            print("✓ Bot listener is initialized and working!")
            return True
        else:
            print("✗ Bot listener is NOT initialized")
            diagnostics = health_data.get("diagnostics", {})
            
            # Check session file
            session_file = health_data.get("session_file", {})
            if not session_file.get("exists"):
                print(f"\n⚠ ISSUE: Session file not found")
                print(f"   Path: {session_file.get('path', 'unknown')}")
                print(f"   SOLUTION: Upload session file to Fly.io")
                print(f"   Command: fly ssh sftp shell -a tg-bot-lisener")
            elif session_file.get("size", 0) == 0:
                print(f"\n⚠ ISSUE: Session file exists but is empty")
                print(f"   Path: {session_file.get('path', 'unknown')}")
                print(f"   SOLUTION: Upload a valid session file")
            else:
                print(f"\n✓ Session file exists: {session_file.get('path', 'unknown')}")
                print(f"   Size: {session_file.get('size', 0)} bytes")
                if session_file.get("modified"):
                    print(f"   Modified: {session_file.get('modified')}")
            
            # Check initialization error
            init_error = diagnostics.get("init_error")
            if init_error:
                print(f"\n⚠ INITIALIZATION ERROR:")
                print(f"   {init_error}")
                
                if "non-interactive" in init_error.lower() or "authentication required" in init_error.lower():
                    print(f"\n   SOLUTION: Session file may be invalid or expired")
                    print(f"   1. Authenticate locally and create a fresh session file")
                    print(f"   2. Upload the session file to Fly.io")
                elif "mongodb" in init_error.lower():
                    print(f"\n   SOLUTION: MongoDB connection issue")
                    print(f"   1. Check MONGODB_URI secret: fly secrets list -a tg-bot-lisener")
                    print(f"   2. Verify MongoDB is accessible from Fly.io IP")
                elif "bot" in init_error.lower() and "not found" in init_error.lower():
                    print(f"\n   SOLUTION: Bot username issue")
                    print(f"   1. Check BOT_USERNAME secret: fly secrets list -a tg-bot-lisener")
                    print(f"   2. Verify bot username is correct")
            
            # Check retry mechanism
            retry_active = diagnostics.get("retry_active", False)
            if retry_active:
                print(f"\n✓ Retry mechanism is active (will retry every 30 seconds)")
            else:
                print(f"\n⚠ Retry mechanism is NOT active")
                print(f"   SOLUTION: Restart the app to trigger retry mechanism")
                print(f"   Command: fly apps restart -a tg-bot-lisener")
            
            # Check last attempt
            last_attempt = diagnostics.get("last_init_attempt")
            if last_attempt:
                print(f"\n   Last initialization attempt: {last_attempt}")
            
            return False
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ ERROR: Could not connect to {base_url}")
        print(f"   {e}")
        print(f"\n   Make sure the app is deployed and running on Fly.io")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://tg-bot-lisener.fly.dev"
    check_health(url)
