# Run after configuring feishu.config.json:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .cursor/hooks/test_feishu.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $scriptDir "feishu.config.json"

if (-not (Test-Path $configPath)) {
    Write-Host "Missing feishu.config.json - copy from feishu.config.example.json first." -ForegroundColor Yellow
    exit 1
}

& (Join-Path $scriptDir "notify_feishu.ps1") -Event test
Write-Host "Test message sent. Check your Feishu group." -ForegroundColor Green
