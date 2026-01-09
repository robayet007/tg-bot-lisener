# PowerShell script to upload session file to Fly.io
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

# Read and encode file
Write-Host "Encoding session file to base64..." -ForegroundColor Yellow
$fileBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $sessionFile))
$base64Content = [Convert]::ToBase64String($fileBytes)

Write-Host "Uploading via fly ssh console..." -ForegroundColor Yellow

# Create a temporary script file for the remote command
$remoteScript = @"
#!/bin/bash
echo '$base64Content' | base64 -d > $remotePath
ls -lah $remotePath
"@

# Save to temp file
$tempScript = "upload_temp.sh"
$remoteScript | Out-File -FilePath $tempScript -Encoding ASCII -NoNewline

Write-Host "`nExecuting upload command..." -ForegroundColor Yellow
Get-Content $tempScript | fly ssh console -a $appName -C "bash -s"

# Cleanup
Remove-Item $tempScript -ErrorAction SilentlyContinue

Write-Host "`n✓ Upload complete!`n" -ForegroundColor Green
Write-Host "Waiting 30 seconds for retry mechanism to pick up the new session file..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "`nChecking health status..." -ForegroundColor Cyan
curl -s https://tg-bot-lisener.fly.dev/health | python -m json.tool
