@echo off
setlocal

REM ============================================================
REM One-time setup for Tender Analysis Platform
REM Place this file in the project root next to main.py
REM ============================================================

cd /d "%~dp0"

echo.
echo Tender Analysis Platform - Setup
echo Project folder: %CD%
echo.

REM Prefer the Python launcher if available, otherwise use python.
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

REM Check Python is available.
%PYTHON_CMD% --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python could not be found.
    echo Install Python 3 and make sure it is available on PATH.
    echo.
    pause
    exit /b 1
)

REM Create virtual environment if required.
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create virtual environment.
        echo.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
)

set "VENV_PYTHON=.venv\Scripts\python.exe"

echo.
echo Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to upgrade pip.
    echo.
    pause
    exit /b 1
)

REM Install dependencies from requirements.txt if present.
if exist "requirements.txt" (
    echo.
    echo Installing dependencies from requirements.txt...
    "%VENV_PYTHON%" -m pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install dependencies.
        echo.
        pause
        exit /b 1
    )
) else (
    echo.
    echo No requirements.txt found.
    echo Installing minimum required packages...
    "%VENV_PYTHON%" -m pip install openpyxl tksheet sv-ttk
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install minimum required packages.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Setup complete.
echo You can now run the application using run.bat.
echo.
pause
endlocal
