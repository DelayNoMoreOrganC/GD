# 清理冗余/失效文件（保留核心源码与 tools）
# 用法: powershell -ExecutionPolicy Bypass -File scripts\cleanup_project.ps1

$ErrorActionPreference = "SilentlyContinue"
Set-Location (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))

$deleteFiles = @(
  "e2e_frozen_sim.py","e2e_gui_worker.py","e2e_exe_log.txt",
  "legal_archive_gui_v2.py","legal_archive_v2.spec","run_archive_v2.py",
  "app.py","app_simple.py","app_ascii.py","app_auto.py","app_config.py",
  "app_chinese.py","app_chinese_fixed.py","app_chinese_mineru_backup.py","app_local_ocr.py",
  "legal_doc_system.py",
  "emergency_fix_filling.py","fundamental_fix.py","fix_all_issues.py","fix_batch_download.py",
  "fix_template_conversion.py","fix_template_paths.py","debug_template_filling.py",
  "original_format_preservation.py","advanced_format_templates.py","structure_aware_templates.py",
  "auto_convert_templates.py","analyze_doc_templates.py","analyze_token_issue.py",
  "local_ocr_scanned_pdf.py","build_field_aliases.py",
  "scan_delivery_template.py","scan_red_text.py","fix_manifest_roles.py","template_instructions.py",
  "mineru_api_correct.py","mineru_correct_implementation.py",
  "verify_ocr_modes.py","verify_all_fixes.py","verify_new_token.py",
  "strict_api_check.py","final_test.py","final_verification.py","real_end_to_end_test.py",
  "FINAL_VERIFICATION_REPORT.md","FIX_COMPLETION_REPORT.md","BAIDU_OCR_MODE_REPORT.md",
  "DOC_CONVERSION_GUIDE.md","START_GUIDE.md"
) + (Get-ChildItem -File -Filter "test_*.py" | ForEach-Object { $_.Name }) +
  (Get-ChildItem -File -Filter "check_pdf*.py" | ForEach-Object { $_.Name })

$deleteDirs = @("build", "uploads")

foreach ($f in $deleteFiles) {
  if (Test-Path $f) { Remove-Item $f -Force; Write-Host "del $f" }
}
foreach ($d in $deleteDirs) {
  if (Test-Path $d) { Remove-Item $d -Recurse -Force; Write-Host "del $d/" }
}
if (Test-Path "outputs") { Remove-Item "outputs\*" -Recurse -Force; Write-Host "clear outputs/" }

foreach ($h in @("chinese.html","chinese_fixed.html","config.html","upload.html","index.html")) {
  $p = Join-Path "templates" $h
  if (Test-Path $p) { Remove-Item $p -Force; Write-Host "del templates/$h" }
}

Write-Host "`nDone. Core: legal_archive_gui.py, archive_pipeline.py, dist/V1.3.6 + V2"
