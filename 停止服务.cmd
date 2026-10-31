@echo off
rem Stop only the service this project started (identity-checked). ASCII body.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python tools\bootstrap.py stop %*
if errorlevel 1 (
  echo.
  echo Stop failed. See logs\startup.log
  pause
  exit /b 1
)
pause
exit /b 0
