@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1

where python >nul 2>nul
if errorlevel 1 (
  echo [Guizang] Python was not found. Install Python 3.10 or later and add it to PATH.
  pause
  exit /b 1
)

python app.py
if errorlevel 1 (
  echo.
  echo [Guizang] Startup failed. Review the error above.
  pause
)

