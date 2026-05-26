@echo off
cd /d "%~dp0"

where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw "%~dp0image_watermark.py" --gui
    exit /b 0
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0image_watermark.py" --gui
    exit /b 0
)

where py >nul 2>nul
if %errorlevel%==0 (
    start "" py -3 "%~dp0image_watermark.py" --gui
    exit /b 0
)

where python >nul 2>nul
if %errorlevel%==0 (
    start "" python "%~dp0image_watermark.py" --gui
    exit /b 0
)

echo 未找到 Python，请先安装 Python 3，然后重新双击此启动文件。
pause
