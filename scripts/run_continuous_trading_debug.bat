@echo off
:: Continuous trading loop for Alpaca AI Trading Agent - DEBUG VERSION
:: Runs the paper trading cycle every 60 seconds and logs output

setlocal enabledelayedexpansion

echo [DEBUG] Current directory: %cd%
set "LOG_DIR=logs"
echo [DEBUG] LOG_DIR set to: %LOG_DIR%

if not exist "%LOG_DIR%" (
    echo [DEBUG] Creating log directory: %LOG_DIR%
    mkdir "%LOG_DIR%"
) else (
    echo [DEBUG] Log directory already exists: %LOG_DIR%
)

echo [DEBUG] Contents of log directory before setting timestamp:
dir "%LOG_DIR%"

:: Get date and time components for timestamp
echo [DEBUG] Raw date: %date%
echo [DEBUG] Raw time: %time%

set "YYYY=%date:~-4%"
set "MM=%date:~4,2%"
set "DD=%date:~7,2%"
set "HH=%time:~0,2%"
set "MN=%time:~3,2%"
set "SS=%time:~6,2%"

:: Handle leading space in time (for hours < 10)
if "%HH:~0,1%"==" " set "HH=0%HH:~1,1%"

set "TIMESTAMP=%YYYY%%MM%%DD%_%HH%%MN%%SS%"
set "LOG_FILE=%LOG_DIR%\trading_%TIMESTAMP%.log"

echo [DEBUG] Constructed TIMESTAMP: %TIMESTAMP%
echo [DEBUG] Constructed LOG_FILE: %LOG_FILE%

echo Starting continuous trading loop...
echo Log file: %LOG_FILE%
echo Press Ctrl+C to stop
echo ============================================================

echo Starting continuous trading loop... >> "%LOG_FILE%"
echo Log file: %LOG_FILE% >> "%LOG_FILE%"
echo Press Ctrl+C to stop >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

echo [DEBUG] Attempting to write test entry to log file...
echo [DEBUG] Test entry at %date% %time% >> "%LOG_FILE%"

:: Loop indefinitely
:loop
    :: Get current timestamp for the log entry
    echo [DEBUG] In loop iteration
    set "YYYY=%date:~-4%"
    set "MM=%date:~4,2%"
    set "DD=%date:~7,2%"
    set "HH=%time:~0,2%"
    set "MN=%time:~3,2%"
    set "SS=%time:~6,2%"

    :: Handle leading space in time (for hours < 10)
    if "%HH:~0,1%"==" " set "HH=0%HH:~1,1%"

    set "TIME_NOW=%date% %HH%:%MN%:%SS%"
    echo [!TIME_NOW!] Starting trading cycle
    echo [!TIME_NOW!] Starting trading cycle >> "%LOG_FILE%"

    :: Run the paper trading cycle and append output to log file
    echo [DEBUG] About to run: python -m backend.scripts.run_paper_cycle
    python -m backend.scripts.run_paper_cycle 2>&1 > "%LOG_DIR%\temp_output.log"
    type "%LOG_DIR%\temp_output.log"
    type "%LOG_DIR%\temp_output.log" >> "%LOG_FILE%"
    del "%LOG_DIR%\temp_output.log"
    echo [DEBUG] Finished running python command

    :: Add a separator between cycles
    echo.
    echo ============================================================
    echo.
    echo ============================================================ >> "%LOG_FILE%"
    echo. >> "%LOG_FILE%"

    echo [DEBUG] Completed cycle, waiting 60 seconds...
    :: Wait for 60 seconds (as per LOOP_INTERVAL_SECONDS in .env)
    timeout /t 60 >nul
    echo [DEBUG] Wait complete, starting next cycle
goto loop
endlocal