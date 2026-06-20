# Apply Cursor backend + GD workspace defaults after QR wizard creates config.
# Run once after: lark-agent-bridge start (scan QR to finish app setup)

$ErrorActionPreference = "Stop"

$configDir = Join-Path $env:USERPROFILE ".lark-channel"
$configPath = Join-Path $configDir "config.json"
$workspacesPath = Join-Path $configDir "workspaces.json"

if (-not (Test-Path $configPath)) {
    Write-Host "Missing $configPath" -ForegroundColor Yellow
    Write-Host "Run scripts/start_feishu_bridge.ps1 first and complete the QR wizard." -ForegroundColor Yellow
    exit 1
}

function Get-CursorAgentLaunch {
    $agentRoot = Join-Path $env:LOCALAPPDATA "cursor-agent"
    $versionsDir = Join-Path $agentRoot "versions"
    if (-not (Test-Path $versionsDir)) {
        throw "Cursor agent not installed. Run: irm 'https://cursor.com/install?win32=true' | iex"
    }

    $versionDir = Get-ChildItem -Path $versionsDir -Directory |
        Where-Object { $_.Name -match '^\d{4}\.\d{1,2}\.\d{1,2}-.+$' } |
        Sort-Object Name -Descending |
        Select-Object -First 1

    if (-not $versionDir) {
        throw "No Cursor agent version directory found under $versionsDir"
    }

    $nodeExe = Join-Path $versionDir.FullName "node.exe"
    $indexJs = Join-Path $versionDir.FullName "index.js"
    if (-not (Test-Path $nodeExe) -or -not (Test-Path $indexJs)) {
        throw "Cursor agent files missing in $($versionDir.FullName)"
    }

    return @{
        command = $nodeExe
        args    = @($indexJs, "-f", "--trust")
    }
}

$configText = [IO.File]::ReadAllText($configPath)
if ($configText.Length -gt 0 -and [int][char]$configText[0] -eq 0xFEFF) {
    $configText = $configText.Substring(1)
}
$config = $configText | ConvertFrom-Json

if (-not $config.preferences) {
    $config | Add-Member -NotePropertyName preferences -NotePropertyValue ([pscustomobject]@{})
}

$launch = Get-CursorAgentLaunch

$prefs = @{
    defaultBackend           = "cursor"
    agentCursorRuntime       = "cli"
    agentCursorLocalSettings = "all"
    defaultCwd               = "F:\GD"
    agentCursorModel         = "auto"
    agentCommand             = @{
        backend = "cursor"
        command = $launch.command
        args    = $launch.args
    }
    agentBackends            = @{
        cursor = @{
            backend = "cursor"
            command = $launch.command
            args    = $launch.args
        }
    }
}

foreach ($key in $prefs.Keys) {
    $config.preferences | Add-Member -NotePropertyName $key -NotePropertyValue $prefs[$key] -Force
}

$json = $config | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($configPath, $json, (New-Object System.Text.UTF8Encoding $false))

$workspaces = @{
    chats = @{}
    named = @{ gd = "F:/GD" }
}
$wsJson = $workspaces | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($workspacesPath, $wsJson, (New-Object System.Text.UTF8Encoding $false))

Write-Host "Bridge configured:" -ForegroundColor Green
Write-Host "  backend  = cursor (CLI via node.exe)"
Write-Host "  command  = $($launch.command)"
Write-Host "  default  = F:\GD"
Write-Host "  workspace alias: gd -> F:\GD"
Write-Host ""
Write-Host "Next: restart bridge (Ctrl+C then re-run), then in Feishu: /ws use gd" -ForegroundColor Cyan
