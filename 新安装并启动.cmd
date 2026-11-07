@echo off
rem TextiLeDream one-click installer (first run). Pure ASCII body so any console
rem code page can run it; all logic lives in tools/bootstrap.py.
rem Extra args pass through: --with-map --build-encyclopedia --yes --dry-run
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

%PYEXE% tools\bootstrap.py check
echo.
echo === Installing (creates .venv and installs dependencies) ===
%PYEXE% tools\bootstrap.py install %*
if errorlevel 1 goto failed

echo.
echo === Starting ===
%PYEXE% tools\bootstrap.py start %*
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo Install or start failed. See logs\startup.log for details.
pause
exit /b 1
