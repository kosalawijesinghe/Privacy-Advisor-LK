@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set APP_NAME=Privacy Advisor SL
set VENV_DIR=.venv
set ACTIVATE_SCRIPT=%VENV_DIR%\Scripts\activate.bat
set PYTHON_EXE=%VENV_DIR%\Scripts\python.exe

echo.
echo ================================================================================
echo   %APP_NAME% - quick launcher
 echo ================================================================================
echo.

echo [1/4] Ensuring virtual environment exists...
if not exist "%PYTHON_EXE%" (
    echo     -> Creating venv at %VENV_DIR% ...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        echo         Install Python 3.9+ and retry.
        exit /b 1
    )
)
echo     -> Virtual environment ready.
echo.

echo [2/4] Activating virtual environment...
call "%ACTIVATE_SCRIPT%"
if errorlevel 1 (
    echo [ERROR] Unable to activate %VENV_DIR%.
    exit /b 1
)
echo     -> venv activated.
echo.

echo [3/4] Installing/validating dependencies (this may take a moment)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. Check your internet connection and retry.
    exit /b 1
)
echo     -> Dependencies ready.
echo.

echo [4/4] Launching Streamlit app on http://localhost:8501 ...
set STREAMLIT_SERVER_HEADLESS=false
streamlit run app.py --server.port=8501 --logger.level=info
if errorlevel 1 (
    echo.
    echo [ERROR] Streamlit terminated unexpectedly.
    exit /b 1
)

echo.
echo [INFO] %APP_NAME% closed.
echo.
pause
