# Start Feishu <-> Cursor bridge (keep this window open).
# First run opens a QR wizard - scan with Feishu app to bind the bot app.

$ErrorActionPreference = "Stop"

$agentPath = Join-Path $env:LOCALAPPDATA "cursor-agent"
if ($env:PATH -notlike "*$agentPath*") {
    $env:PATH = "$agentPath;$env:PATH"
}

Write-Host "Cursor agent: $(agent --version 2>&1)" -ForegroundColor DarkGray

$login = agent about 2>&1 | Out-String
if ($login -match "Not logged in") {
    Write-Host ""
    Write-Host "Cursor CLI is not logged in yet." -ForegroundColor Yellow
    Write-Host "Run in another terminal:  agent login" -ForegroundColor Yellow
    Write-Host "Complete browser auth, then restart this script." -ForegroundColor Yellow
    Write-Host ""
}

$configPath = Join-Path $env:USERPROFILE ".lark-channel\config.json"
if (-not (Test-Path $configPath)) {
    Write-Host "First run: scan the QR code with Feishu to create the bot app." -ForegroundColor Cyan
} else {
    Write-Host "Config found. Starting bridge..." -ForegroundColor Green
    $configured = Get-Content $configPath -Raw | ConvertFrom-Json
    if (-not $configured.preferences.defaultBackend) {
        Write-Host "Tip: run scripts/configure_feishu_bridge.ps1 to set Cursor + F:\GD defaults." -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host '=== Feishu bridge (path B) ===' -ForegroundColor Cyan
Write-Host '  1. Open private chat with bot in Feishu'
Write-Host '  2. Send:  /ws use gd   (or  /cd F:\GD)'
Write-Host '  3. Send your task, e.g. run loop_metrics and report'
Write-Host '  4. Replies appear in that chat (not webhook group)'
Write-Host ""
Write-Host '  Commands:  /model auto   /ws use gd   /new'
$logDir = Join-Path $env:USERPROFILE '.lark-channel\logs'
Write-Host "  Logs:  $logDir"
Write-Host ""
Write-Host "Press Ctrl+C to stop the bridge." -ForegroundColor DarkGray
Write-Host ""

lark-agent-bridge start
