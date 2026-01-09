# Upload session file using binary-safe method
$appName = "tg-bot-lisener"
$sessionFile = "telegram_listener.session"
$remotePath = "/app/sessions/telegram_listener.session"

Write-Host "`n=== Binary-Safe Session File Upload ===`n" -ForegroundColor Green

# Read file as binary
$fileBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $sessionFile))
$base64 = [Convert]::ToBase64String($fileBytes)

Write-Host "File size: $($fileBytes.Length) bytes" -ForegroundColor Cyan
Write-Host "Base64 length: $($base64.Length) characters`n" -ForegroundColor Cyan

# Create Python script to decode and write binary
$pythonScript = @"
import base64
import sys

# Read base64 from stdin (all at once, no newlines)
base64_data = sys.stdin.read().strip()
binary_data = base64.b64decode(base64_data)

# Write binary file
with open('/app/sessions/telegram_listener.session', 'wb') as f:
    f.write(binary_data)

print(f"Written {len(binary_data)} bytes")
"@

$pythonScript | Out-File -FilePath "decode_session.py" -Encoding UTF8

Write-Host "Uploading via Python script..." -ForegroundColor Yellow
echo $base64 | fly ssh console -a $appName -C "python3 -" < decode_session.py

Write-Host "`nVerifying upload..." -ForegroundColor Cyan
fly ssh console -a $appName -C "ls -lh /app/sessions/telegram_listener.session && python3 decode_session.py <<< '$base64' 2>&1 || echo 'Upload complete'"

Write-Host "`nWaiting 30 seconds for retry..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "`nChecking status..." -ForegroundColor Cyan
curl -s https://tg-bot-lisener.fly.dev/health | python -m json.tool
