@echo off
rem Everyday start: no install steps. ASCII body; logic in tools/bootstrap.py.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python tools\bootstrap.py start %*
if errorlevel 1 (
  echo.
  echo Start failed. If this is the first run, double-click the install-and-start cmd
  echo in this folder, or see logs\startup.log
  pause
  exit /b 1
)
exit /b 0
