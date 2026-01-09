# Simple PowerShell script to upload session file via SFTP
$appName = "tg-bot-lisener"
$sessionFile = "telegram_listener.session"
$remotePath = "/app/sessions/telegram_listener.session"

if (-not (Test-Path $sessionFile)) {
    Write-Host "Error: Session file not found: $sessionFile" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Uploading Session File to Fly.io ===`n" -ForegroundColor Green
Write-Host "Session file: $sessionFile" -ForegroundColor Cyan
Write-Host "Remote path: $remotePath`n" -ForegroundColor Cyan

# Create SFTP commands file
$sftpCommands = @"
put $sessionFile $remotePath
quit
"@

$sftpCommands | Out-File -FilePath "sftp_commands.txt" -Encoding ASCII

Write-Host "SFTP commands saved to: sftp_commands.txt" -ForegroundColor Yellow
Write-Host "`nNow run this command:" -ForegroundColor Yellow
Write-Host "Get-Content sftp_commands.txt | fly ssh sftp shell -a $appName" -ForegroundColor White
Write-Host "`nOr manually:" -ForegroundColor Yellow
Write-Host "1. Run: fly ssh sftp shell -a $appName" -ForegroundColor White
Write-Host "2. Type: put telegram_listener.session /app/sessions/telegram_listener.session" -ForegroundColor White
Write-Host "3. Type: quit" -ForegroundColor White
