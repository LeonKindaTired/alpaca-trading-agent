@echo off
echo Setting up virtual environment for Alpaca AI Trading Agent Dashboard...
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install/upgrade pip
python -m pip install --upgrade pip

REM Install dependencies from requirements.txt
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Dependencies installed successfully!
echo.
echo To run the dashboard:
echo   streamlit run dashboard/app.py
echo.
echo Or use the shortcut:
call venv\Scripts\activate && streamlit run dashboard/app.py
echo.
echo Dashboard will be available at: http://localhost:8501
echo.
pause
