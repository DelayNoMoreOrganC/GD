# 目标电脑 PC：补装 MinerU pipeline + CUDA PyTorch（修复 hybrid/pipeline 缺 torch 报错）
# 用法: powershell -ExecutionPolicy Bypass -File scripts\fix_mineru_target_pc.ps1

$ErrorActionPreference = "Stop"
$Py = "C:\Users\PC\AppData\Local\Programs\Python\Python313\python.exe"

if (-not (Test-Path $Py)) {
    Write-Host "[FAIL] 未找到 $Py ，请修改本脚本中的 `$Py 路径" -ForegroundColor Red
    exit 1
}

Write-Host "=== 补装 MinerU[pipeline] + PyTorch (CUDA) ===" -ForegroundColor Cyan
Write-Host "Python: $Py"

& $Py -m pip install -U pip
& $Py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
& $Py -m pip install -U "mineru[pipeline]"

Write-Host "`n验证 torch CUDA..." -ForegroundColor Yellow
& $Py -c "import torch; print('torch', torch.__version__); print('cuda', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no gpu')"

Write-Host "`n验证 mineru..." -ForegroundColor Yellow
& "C:\Users\PC\AppData\Local\Programs\Python\Python313\Scripts\mineru.exe" --version

Write-Host "`n[OK] 完成后重启「案件档案归档」，选 MinerU 再试。" -ForegroundColor Green
