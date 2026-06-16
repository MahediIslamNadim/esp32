@echo off
REM ESP-FC one-command setup (Windows).
REM Double-click this file, or run it from a command prompt in the project root.
REM
REM On startup the tool checks GitHub for updates and shows an Update / Skip
REM prompt (this needs git installed). Pass --no-update to skip that check, e.g.
REM   setup.bat --no-update

setlocal
cd /d "%~dp0"

REM Auto-update needs git; warn (but continue) if it's missing.
where git >nul 2>nul
if not %errorlevel%==0 (
  echo ! git not found - the GitHub auto-update check will be skipped.
  echo   Install Git from https://git-scm.com to enable updates.
)

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
