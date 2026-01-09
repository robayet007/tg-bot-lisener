# Session File Upload Guide - Fly.io

## Problem
Session file on Fly.io is invalid/expired. Need to upload a fresh, valid session file.

## Solution - Choose One Method

### Method 1: SFTP (Recommended - Easiest)

1. **Open SFTP shell:**
   ```powershell
   fly ssh sftp shell -a tg-bot-lisener
   ```

2. **When you see the `»` prompt, type:**
   ```
   put telegram_listener.session /app/sessions/telegram_listener.session
   ```

3. **Wait for upload, then type:**
   ```
   quit
   ```

### Method 2: Using Base64 + Python (If SFTP doesn't work)

1. **The base64 file is already created:** `session_base64.txt`

2. **Open Fly.io console:**
   ```powershell
   fly ssh console -a tg-bot-lisener
   ```

3. **In the console, run:**
   ```python
   import base64
   with open('session_base64.txt', 'r') as f:
       data = base64.b64decode(f.read().strip())
   with open('/app/sessions/telegram_listener.session', 'wb') as f:
       f.write(data)
   print("Done!")
   ```

   **But wait** - you need to upload session_base64.txt first! So use Method 1 instead.

### Method 3: Manual Copy-Paste (For small files)

1. **Encode session file:**
   ```powershell
   python upload_session.py
   ```

2. **Open Fly.io console:**
   ```powershell
   fly ssh console -a tg-bot-lisener
   ```

3. **In console, create the file:**
   ```bash
   cat > /tmp/session_b64.txt
   ```
   (Then paste the entire content from `session_base64.txt`, press Ctrl+D)

4. **Decode and copy:**
   ```bash
   base64 -d /tmp/session_b64.txt > /app/sessions/telegram_listener.session
   ```

## After Upload

1. **Wait 30-60 seconds** for the retry mechanism to pick up the new session file

2. **Check status:**
   ```powershell
   curl https://tg-bot-lisener.fly.dev/health
   ```

3. **Check detailed status:**
   ```powershell
   curl https://tg-bot-lisener.fly.dev/api/status
   ```

4. **If still not working, check logs:**
   ```powershell
   fly logs -a tg-bot-lisener --no-tail | Select-String -Pattern "Retry|initialized"
   ```

## Important Notes

- The session file MUST be valid and authorized locally before uploading
- Test local session: `python test_session.py`
- If local session is invalid, authenticate locally first: `python api_server.py`
- The retry mechanism will automatically try to initialize every 30 seconds
- No need to restart the app after uploading
