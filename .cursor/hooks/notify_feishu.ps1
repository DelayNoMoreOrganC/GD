param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("stop", "subagentStop", "sessionEnd", "test")]
    [string]$Event
)

$ErrorActionPreference = "SilentlyContinue"

$configPath = Join-Path $PSScriptRoot "feishu.config.json"
$messagesPath = Join-Path $PSScriptRoot "messages.zh-CN.json"

function Read-HookInput {
    try {
        $raw = [Console]::In.ReadToEnd()
        if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
        return $raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Get-FeishuSign {
    param([string]$Secret, [string]$Timestamp)
    $hmac = New-Object System.Security.Cryptography.HMACSHA256
    $hmac.Key = [Text.Encoding]::UTF8.GetBytes($Secret)
    $msg = "{0}`n{1}" -f $Timestamp, $Secret
    $hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($msg))
    return [Convert]::ToBase64String($hash)
}

function Send-FeishuText {
    param([string]$WebhookUrl, [string]$Secret, [string]$Text)

    $body = [ordered]@{
        msg_type = "text"
        content  = @{ text = $Text }
    }

    if (-not [string]::IsNullOrWhiteSpace($Secret)) {
        $ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString()
        $body.timestamp = $ts
        $body.sign = Get-FeishuSign -Secret $Secret -Timestamp $ts
    }

    $json = $body | ConvertTo-Json -Depth 5 -Compress
    Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body ([Text.Encoding]::UTF8.GetBytes($json)) -ContentType "application/json; charset=utf-8" | Out-Null
}

function Format-Message {
    param([string]$Template, [hashtable]$Vars)
    $result = $Template
    foreach ($key in $Vars.Keys) {
        $result = $result.Replace("{$key}", [string]$Vars[$key])
    }
    return $result
}

if (-not (Test-Path $configPath)) {
    exit 0
}

$config = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($config.enabled -eq $false) { exit 0 }
if ([string]::IsNullOrWhiteSpace($config.webhook_url)) { exit 0 }

$messages = Get-Content $messagesPath -Raw -Encoding UTF8 | ConvertFrom-Json
$project = if ($config.project_name) { $config.project_name } else { $messages.default_project }
$input = if ($Event -ne "test") { Read-HookInput } else { $null }
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

switch ($Event) {
    "test" {
        $text = Format-Message -Template $messages.test -Vars @{ project = $project; now = $now }
    }
    "stop" {
        $status = if ($input.status) { $input.status } else { "completed" }
        $text = Format-Message -Template $messages.stop -Vars @{ project = $project; status = $status; now = $now }
    }
    "subagentStop" {
        $task = if ($input.task) { $input.task } else { $messages.no_task }
        $status = if ($input.status) { $input.status } else { "completed" }
        $duration = if ($input.duration_ms) { [math]::Round($input.duration_ms / 1000, 1) } else { "?" }
        $text = Format-Message -Template $messages.subagentStop -Vars @{
            project = $project; task = $task; status = $status; duration = $duration; now = $now
        }
    }
    "sessionEnd" {
        $reason = if ($input.reason) { $input.reason } else { "completed" }
        $duration = if ($input.duration_ms) { [math]::Round($input.duration_ms / 1000, 1) } else { "?" }
        $text = Format-Message -Template $messages.sessionEnd -Vars @{
            project = $project; reason = $reason; duration = $duration; now = $now
        }
    }
}

try {
    Send-FeishuText -WebhookUrl $config.webhook_url -Secret $config.secret -Text $text
} catch {
    # Hook failures must not block Cursor
}

exit 0
