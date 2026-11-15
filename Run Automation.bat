@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo Python was not found on PATH.
  pause
  exit /b 1
)

python run_automation.py
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% neq 0 (
  echo Finished with errors ^(exit %EXITCODE%^).
) else (
  echo Done.
)
pause
exit /b %EXITCODE%
