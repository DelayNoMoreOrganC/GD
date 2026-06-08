@echo off
echo === 验证所有修复 ===
echo.

echo [1] 检查模板文件...
if exist "templates_local\立案审批表.doc" echo     OK 立案审批表.doc
if exist "templates_local\送达材料清单.doc" echo     OK 送达材料清单.doc
if exist "templates_local\档案卷宗.doc" echo     OK 档案卷宗.doc
if exist "templates_local\结案报告表.doc" echo     OK 结案报告表.doc
if exist "templates_local\质量监督卡.doc" echo     OK 质量监督卡.doc

echo.
echo [2] 检查HTML文件修复...
findstr /C:"MinerU" templates\chinese.html >nul
if errorlevel 1 (
    echo     OK MinerU配置已移除
) else (
    echo     FAIL MinerU配置仍然存在
)

echo.
echo [3] 检查app_chinese.py路径配置...
findstr /C:"templates_local" app_chinese.py >nul
if errorlevel 1 (
    echo     FAIL 模板路径未更新
) else (
    echo     OK 模板路径已更新为本地英文路径
)

echo.
echo [4] 检查百度OCR集成...
findstr /C:"BAIDU_OCR_CONFIG" app_chinese.py >nul
if errorlevel 1 (
    echo     FAIL 百度OCR配置不存在
) else (
    echo     OK 百度OCR配置存在
)

echo.
echo === 修复验证完成 ===
echo 现在可以运行: python app_chinese.py
pause