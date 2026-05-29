@echo off
:: AI Agent Platform Windows Startup Script
:: Sets up a Python virtual environment, installs dependencies, and runs the FastAPI server.

echo ==========================================
echo    AI Agent Platform Startup (Windows)
echo ==========================================

:: Check if python is available
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your PATH.
    echo Please install Python 3.12+ and check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Show python version
echo Python found:
python --version

:: Define venv directory name
set VENV_DIR=.venv

:: Create venv if it does not exist
if not exist "%VENV_DIR%" (
    echo Creating virtual environment in %VENV_DIR%...
    python -m venv %VENV_DIR%
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
) else (
    echo Using existing virtual environment: %VENV_DIR%
)

:: Activate the virtual environment
echo Activating virtual environment...
call %VENV_DIR%\Scripts\activate.bat

:: Install requirements
echo Installing/updating requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Run the FastAPI application
echo Starting FastAPI server on http://localhost:8000 ...
echo Press Ctrl+C to stop the server.
python -m backend.main

pause
