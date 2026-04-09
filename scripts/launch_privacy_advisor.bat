@echo off
setlocal enabledelayedexpansion

REM Privacy Advisor SL - System Launcher
REM Double-click this file to start the application

cd /d "%~dp0\.."

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Python is not installed or not in PATH
    echo ========================================
    echo.
    echo Please install Python 3.8+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Check if requirements are installed
echo Checking dependencies...
python -c "import sentence_transformers" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Installing required packages...
    echo This may take a few minutes on first run...
    echo.
    pip install -q -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ========================================
        echo ERROR: Failed to install dependencies
        echo ========================================
        pause
        exit /b 1
    )
)

REM Launch the application using Streamlit
echo.
echo Starting Privacy Advisor SL...
echo Streamlit will open your browser automatically...
echo.
python -m streamlit run app.py --logger.level=error

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Application failed to start
    echo ========================================
    echo Check the error messages above
    echo.
    pause
)

endlocal
