@echo off
setlocal

REM ============================================================
REM Fast launcher for Tender Analysis Platform
REM Place this file in the project root next to main.py
REM Run setup.bat first if .venv does not exist
REM ============================================================

cd /d "%~dp0"

echo.
echo Starting Tender Analysis Platform...
echo Project folder: %CD%
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Run setup.bat first.
    echo.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo ERROR: main.py was not found in this folder.
    echo Make sure this file is in the project root.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with an error.
    echo Check the messages above for details.
    echo.
    pause
    exit /b 1
)

echo.
echo Application closed.
echo.
pause
endlocal
