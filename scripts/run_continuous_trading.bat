@echo off
:: Continuous trading loop for Alpaca AI Trading Agent
:: Runs the paper trading cycle every 60 seconds and logs output

setlocal enabledelayedexpansion

set "LOG_DIR=logs"
set "TIMESTAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "LOG_FILE=%LOG_DIR%\trading_%TIMESTAMP%.log"

:: Create logs directory if it doesn't exist
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
)

echo Starting continuous trading loop...
echo Log file: %LOG_FILE%
echo Press Ctrl+C to stop
echo ============================================================
echo Starting continuous trading loop... >> "%LOG_FILE%"
echo Log file: %LOG_FILE% >> "%LOG_FILE%"
echo Press Ctrl+C to stop >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: Loop indefinitely
:loop
    :: Get current timestamp for the log entry
    for /f "tokens=1-2 delims= " %%a in ('time /t') do (
        set "TIME_NOW=%%a %%b"
    )
    set "CYCLE_TIME=%date% %TIME_NOW%"
    echo [!CYCLE_TIME!] Starting trading cycle
    echo [!CYCLE_TIME!] Starting trading cycle >> "%LOG_FILE%"

    :: Run the paper trading cycle and append output to log file
    python -m backend.scripts.run_paper_cycle 2>&1 > "%LOG_DIR%\temp_output.log"
    type "%LOG_DIR%\temp_output.log"
    type "%LOG_DIR%\temp_output.log" >> "%LOG_FILE%"
    del "%LOG_DIR%\temp_output.log"

    :: Add a separator between cycles
    echo.
    echo ============================================================
    echo.
    echo ============================================================ >> "%LOG_FILE%"
    echo. >> "%LOG_FILE%"

    :: Wait for 60 seconds (as per LOOP_INTERVAL_SECONDS in .env)
    :: Using ping method for Windows batch compatibility
    ping -n 61 127.0.0.1 >nul
goto loop
endlocal