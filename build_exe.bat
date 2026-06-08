@echo off
chcp 65001 >nul
cd /d "%~dp0"

for /f "delims=" %%i in ('py -c "from app_version import V1_VERSION, V2_VERSION; print(V1_VERSION)"') do set V1VER=%%i
for /f "delims=" %%i in ('py -c "from app_version import V3_VERSION; print(V3_VERSION)"') do set V3VER=%%i

echo ========================================
echo  案件档案归档 — 打包 %V1VER% + %V3VER%
echo ========================================

where py >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 py 命令
    pause
    exit /b 1
)

py -m pip install -q pyinstaller pymupdf python-docx pywin32 requests baidu-aip

echo [1/2] %V1VER% ...
py -m PyInstaller --noconfirm legal_archive_v1.spec

echo [2/2] %V3VER% ...
py -m PyInstaller --noconfirm legal_archive.spec

set V1DIR=dist\案件档案归档%V1VER%
set V3DIR=dist\案件档案归档%V3VER%
set V1EXE=案件档案归档%V1VER%.exe
set V3EXE=案件档案归档%V3VER%.exe

if not exist "%V1DIR%" mkdir "%V1DIR%"
if not exist "%V3DIR%" mkdir "%V3DIR%"

copy /Y "dist\%V1EXE%" "%V1DIR%\"
copy /Y "dist\%V3EXE%" "%V3DIR%\"
xcopy /Y /E /I templates\bundled\* "%V1DIR%\templates\bundled\"
xcopy /Y /E /I templates\bundled\* "%V3DIR%\templates\bundled\"
xcopy /Y /E /I templates\manifests\* "%V1DIR%\templates\manifests\"
xcopy /Y /E /I templates\manifests\* "%V3DIR%\templates\manifests\"
xcopy /Y /I prompts\* "%V1DIR%\prompts\"
xcopy /Y /I prompts\* "%V3DIR%\prompts\"
copy /Y config.v1.example.json "%V1DIR%\config.json.example"
copy /Y config.target-pc.example.json "%V3DIR%\config.json.example"
if exist config.json.v2.example copy /Y config.json.v2.example "%V3DIR%\"
if exist DEPLOY_V2.md copy /Y DEPLOY_V2.md "%V3DIR%\"
if exist MINERU_V2_SETUP.md copy /Y MINERU_V2_SETUP.md "%V3DIR%\"
if exist OCR_PACKAGING.md copy /Y OCR_PACKAGING.md "%V3DIR%\"
if exist EXE_README.md copy /Y EXE_README.md "%V1DIR%\"
if exist "dist\案件档案归档V2\scripts" xcopy /Y /E /I "dist\案件档案归档V2\scripts" "%V3DIR%\scripts\"
if exist "dist\案件档案归档V2\config.json" copy /Y "dist\案件档案归档V2\config.json" "%V3DIR%\"
del /Q dist\*.exe 2>nul

echo.
echo [完成]
echo   %V1DIR%\%V1EXE%
echo   %V3DIR%\%V3EXE%
pause
