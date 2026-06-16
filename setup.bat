@echo off
REM ESP-FC one-command setup (Windows).
REM Double-click this file, or run it from a command prompt in the project root.

setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py tools\espfc-setup.py %*
  goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
  python tools\espfc-setup.py %*
  goto :end
)

echo Python 3 is required. Install it from https://python.org and re-run.
pause

:end
endlocal
