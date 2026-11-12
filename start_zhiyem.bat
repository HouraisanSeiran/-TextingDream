@echo off
rem Legacy filename; use the shared launcher instead of a machine-specific Python.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "PYEXE="
python -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1 && set "PYEXE=python"
if not defined PYEXE py -3 -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1 && set "PYEXE=py -3"
if not defined PYEXE (
  echo Python 3.11+ not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)
%PYEXE% tools\bootstrap.py start %*
if errorlevel 1 (
  echo.
  echo Start failed. If this is the first run, use the install-and-start cmd
  echo in this folder, or see logs\startup.log
  pause
  exit /b 1
)
exit /b 0
