@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ===================================
REM Privacy Advisor - System Startup
REM ===================================

echo.
echo ================================================================================
echo.
echo   PRIVACY ADVISOR - Sri Lanka Privacy Compliance System
echo.
echo ================================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or higher from https://www.python.org/
    echo Make sure to check 'Add Python to PATH' during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Found: %PYTHON_VERSION%
echo.

REM Check if virtual environment exists
if not exist ".venv\" (
    echo [INFO] Virtual environment not found. Creating...
    echo.
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment
        echo.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
    echo.
) else (
    echo [OK] Virtual environment exists
    echo.
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to activate virtual environment
    echo.
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM Upgrade pip first
echo [INFO] Ensuring pip is up to date...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [WARNING] Could not upgrade pip, continuing anyway...
)
echo.

REM Check if requirements are installed
echo [INFO] Checking required packages...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo [INFO] Required packages not found. Installing from requirements.txt...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install required packages
        echo.
        echo Make sure you have:
        echo   - Internet connection
        echo   - Sufficient disk space
        echo   - Permissions to install packages
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [OK] All packages installed successfully
    echo.
) else (
    echo [OK] All required packages are present
    echo.
)

REM Verify critical modules exist
echo [INFO] Verifying system structure...
if not exist "modules\" (
    echo [ERROR] modules directory not found
    pause
    exit /b 1
)
if not exist "data\" (
    echo [ERROR] data directory not found
    pause
    exit /b 1
)
if not exist "app.py" (
    echo [ERROR] app.py not found
    pause
    exit /b 1
)
echo [OK] All system directories and files verified
echo.

REM Display startup information
echo ================================================================================
echo.
echo [INFO] System initialization complete
echo.
echo Starting Privacy Advisor application...
echo.
echo   URL: http://localhost:8501
echo   Port: 8501
echo.
echo Controls:
echo   - Press Ctrl+C to stop the application
echo   - Check the terminal for debug messages and errors
echo.
echo ================================================================================
echo.

REM Start Streamlit application
REM Use portfile to prevent port conflicts
set STREAMLIT_SERVER_HEADLESS=false
streamlit run app.py --logger.level=info --client.showErrorDetails=true

echo.
echo [INFO] Application closed
echo.
pause
exit /b 0

REM If streamlit fails, pause to show error
if errorlevel 1 (
    echo.
    echo Error: Failed to start Streamlit
    pause
)

echo.
echo Privacy Advisor is running at http://localhost:8501
echo VS Code has been opened
echo.
pause
