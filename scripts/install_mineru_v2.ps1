# MinerU V2 一键安装脚本（在 F:\GD 下以管理员/普通用户运行均可）
# 用法: powershell -ExecutionPolicy Bypass -File scripts\install_mineru_v2.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== 案件归档 V2 — MinerU 环境安装 ===" -ForegroundColor Cyan
Write-Host "工作目录: $Root"

$venv = Join-Path $Root ".venv-mineru"
if (-not (Test-Path $venv)) {
    py -m venv $venv
}
& "$venv\Scripts\Activate.ps1"
py -m pip install -U pip

Write-Host "`n[1/2] 安装 CUDA PyTorch（请确认本机 CUDA 版本，默认 cu124 索引）..." -ForegroundColor Yellow
py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

Write-Host "`n[2/2] 安装 MinerU [all]..." -ForegroundColor Yellow
py -m pip install -U "mineru[all]"

Write-Host "`n验证 mineru CLI..." -ForegroundColor Green
& "$venv\Scripts\mineru.exe" --version

if (-not (Test-Path "config.json")) {
    Copy-Item "config.json.example" "config.json"
    Write-Host "已生成 config.json（请填写 deepseek.api_key）"
}

Write-Host "`n完成。运行 GUI: py legal_archive_gui.py" -ForegroundColor Green
Write-Host "自检: py tools\check_mineru_env.py"
