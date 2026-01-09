#!/usr/bin/env python3
"""
Script to upload session file to Fly.io using base64 encoding
"""
import base64
import subprocess
import sys
import os

def upload_session_file():
    session_file = "telegram_listener.session"
    app_name = "tg-bot-lisener"
    remote_path = "/app/sessions/telegram_listener.session"
    
    if not os.path.exists(session_file):
        print(f"Error: Session file not found: {session_file}")
        print("Please authenticate locally first by running: python app.py")
        return False
    
    print(f"Reading session file: {session_file}")
    with open(session_file, 'rb') as f:
        file_content = f.read()
    
    print(f"File size: {len(file_content)} bytes")
    print(f"Encoding to base64...")
    encoded = base64.b64encode(file_content).decode('utf-8')
    
    # Save to temporary file
    temp_file = "session_base64.txt"
    with open(temp_file, 'w') as f:
        f.write(encoded)
    
    print(f"Base64 encoded content saved to: {temp_file}")
    print(f"\nTo upload, run this command:")
    print(f"  fly ssh console -a {app_name} -C \"base64 -d > {remote_path}\" < {temp_file}")
    print(f"\nOr manually:")
    print(f"  1. Run: fly ssh console -a {app_name}")
    print(f"  2. Run: base64 -d > {remote_path}")
    print(f"  3. Paste the content from {temp_file}")
    print(f"  4. Press Ctrl+D to finish")
    
    return True

if __name__ == "__main__":
    upload_session_file()
