@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist "logs" mkdir "logs"
if not exist "D:\anaconda\python.exe" goto missing_python
"D:\anaconda\python.exe" -X utf8 "%~dp0launch.py"
if errorlevel 1 goto failed
exit /b 0
:missing_python
echo Configured Python is missing: D:\anaconda\python.exe
:failed
echo Startup failed. See logs\startup.log for details.
pause
exit /b 1
