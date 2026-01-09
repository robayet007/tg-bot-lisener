# Session File Upload Guide

## Problem
Session file on Fly.io is invalid/expired. Need to upload a fresh session file.

## Solution

### Step 1: Verify Local Session File is Valid
```powershell
# Test if local session is valid
python api_server.py
# If it asks for authentication, authenticate locally first
# Then stop the server (Ctrl+C)
```

### Step 2: Upload Session File to Fly.io

**Method 1: Using SFTP (Recommended)**
```powershell
# Open SFTP shell
fly ssh sftp shell -a tg-bot-lisener

# In the SFTP shell, type:
put telegram_listener.session /app/sessions/telegram_listener.session

# Then type:
quit
```

**Method 2: Using Base64 (Alternative)**
```powershell
# Encode session file
$encoded = [Convert]::ToBase64String([IO.File]::ReadAllBytes("telegram_listener.session"))
$encoded | Out-File -FilePath "session_base64.txt" -NoNewline

# Upload to Fly.io
fly ssh console -a tg-bot-lisener -C "base64 -d > /app/sessions/telegram_listener.session" < session_base64.txt
```

### Step 3: Verify Upload
```powershell
# Check if file was uploaded
fly ssh console -a tg-bot-lisener -C "ls -lah /app/sessions/"

# Check file size (should be ~28KB)
fly ssh console -a tg-bot-lisener -C "stat /app/sessions/telegram_listener.session"
```

### Step 4: Restart App (if needed)
```powershell
fly apps restart -a tg-bot-lisener
```

### Step 5: Check Status
```powershell
# Check health
curl https://tg-bot-lisener.fly.dev/health

# Check detailed status
curl https://tg-bot-lisener.fly.dev/api/status
```

## Notes
- The retry mechanism will automatically try to initialize the bot listener every 30 seconds
- Once a valid session file is uploaded, the bot should initialize automatically
- No need to restart the app - the retry mechanism will pick it up
