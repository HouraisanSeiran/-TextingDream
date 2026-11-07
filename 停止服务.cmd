@echo off
rem Stop only the service this project started (identity-checked). ASCII body.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
rem Pick a real Python: "python" may be the Microsoft Store stub, so fall back to the py launcher.
set "PYEXE="
python -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1 && set "PYEXE=python"
if not defined PYEXE py -3 -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1 && set "PYEXE=py -3"
if not defined PYEXE (
  echo Python 3.11+ not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)
%PYEXE% tools\bootstrap.py stop %*
if errorlevel 1 (
  echo.
  echo Stop failed. See logs\startup.log
  pause
  exit /b 1
)
pause
exit /b 0
