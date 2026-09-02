@echo off
set "VENV_PYTHON=%~dp0..\venv\Scripts\python.exe"
echo Using Python: %VENV_PYTHON%
if exist "%VENV_PYTHON%" (
    echo Running Python command...
    "%VENV_PYTHON%" -m backend.scripts.run_paper_cycle
    echo Exit code: %errorlevel%
) else (
    echo VENV_PYTHON not found: %VENV_PYTHON%
)