@echo off
rem TextiLeDream one-click installer (first run). Pure ASCII body so any console
rem code page can run it; all logic lives in tools/bootstrap.py.
rem Extra args pass through: --with-map --build-encyclopedia --yes --dry-run
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python tools\bootstrap.py check
echo.
echo === Installing (creates .venv and installs dependencies) ===
python tools\bootstrap.py install %*
if errorlevel 1 goto failed

echo.
echo === Starting ===
python tools\bootstrap.py start %*
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo Install or start failed. See logs\startup.log for details.
pause
exit /b 1
