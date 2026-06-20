# One-time Cursor CLI login (opens browser). Required before bridge can run tasks.

$ErrorActionPreference = "Stop"

$agentPath = Join-Path $env:LOCALAPPDATA "cursor-agent"
if ($env:PATH -notlike "*$agentPath*") {
    $env:PATH = "$agentPath;$env:PATH"
}

Write-Host "Opening Cursor login in browser..." -ForegroundColor Cyan
agent login
Write-Host ""
Write-Host "Verify:" -ForegroundColor Green
agent about
