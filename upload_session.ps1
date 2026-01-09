# PowerShell script to upload session file to Fly.io
# Usage: .\upload_session.ps1

$sessionFile = "telegram_listener.session"
$remotePath = "/app/sessions/telegram_listener.session"
$appName = "tg-bot-lisener"

if (-not (Test-Path $sessionFile)) {
    Write-Host "Error: Session file not found: $sessionFile" -ForegroundColor Red
    Write-Host "Please authenticate locally first by running: python app.py" -ForegroundColor Yellow
    exit 1
}

Write-Host "Uploading session file to Fly.io..." -ForegroundColor Green
Write-Host "Local file: $sessionFile" -ForegroundColor Cyan
Write-Host "Remote path: $remotePath" -ForegroundColor Cyan

# Create a temporary script file for fly ssh sftp
$sftpScript = @"
put $sessionFile $remotePath
quit
"@

$sftpScript | Out-File -FilePath "sftp_upload.txt" -Encoding ASCII

Write-Host "`nTo upload, run this command:" -ForegroundColor Yellow
Write-Host "Get-Content sftp_upload.txt | fly ssh sftp shell -a $appName" -ForegroundColor White
Write-Host "`nOr manually:" -ForegroundColor Yellow
Write-Host "1. Run: fly ssh sftp shell -a $appName" -ForegroundColor White
Write-Host "2. Type: put telegram_listener.session /app/sessions/telegram_listener.session" -ForegroundColor White
Write-Host "3. Type: quit" -ForegroundColor White
