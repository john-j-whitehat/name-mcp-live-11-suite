@echo off
REM Sync helper for the active Ableton remote script runtime

cd /d "C:\Users\DAW11\Share"

set "PYTHON_EXE=C:\Users\DAW11\Share\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo ERROR: Python environment not found at:
    echo   %PYTHON_EXE%
    pause
    exit /b 1
)

set "SYNC_COMMAND=%~1"
if "%SYNC_COMMAND%"=="" set "SYNC_COMMAND=status"

echo.
echo ========================================
echo Ableton Runtime Sync
echo ========================================
echo Command: %SYNC_COMMAND%
echo.

"%PYTHON_EXE%" sync_ableton_runtime.py %SYNC_COMMAND%

pause