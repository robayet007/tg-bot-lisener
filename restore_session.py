#!/usr/bin/env python3
"""
Script to restore session file on Fly.io from base64
Usage: python restore_session.py < base64_file.txt | fly ssh console -a tg-bot-lisener -C "python3 -"
"""
import base64
import sys

# Read base64 from stdin
base64_data = sys.stdin.read().strip().replace('\n', '').replace('\r', '')

try:
    # Decode base64
    binary_data = base64.b64decode(base64_data)
    
    # Write to session file
    session_path = "/app/sessions/telegram_listener.session"
    with open(session_path, 'wb') as f:
        f.write(binary_data)
    
    print(f"Successfully wrote {len(binary_data)} bytes to {session_path}")
    
    # Verify
    import os
    if os.path.exists(session_path):
        size = os.path.getsize(session_path)
        print(f"Verified: File exists, size: {size} bytes")
    else:
        print("ERROR: File was not created!")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
