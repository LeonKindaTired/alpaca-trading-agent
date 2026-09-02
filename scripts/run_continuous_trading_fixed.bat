@echo off
:: Continuous trading loop for Alpaca AI Trading Agent
:: Runs the paper trading cycle every 60 seconds and logs output

setlocal

rem Configure logging
set "LOG_DIR=logs"
set "TIMESTAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "LOG_FILE=%LOG_DIR%\trading_%TIMESTAMP%.log"

rem Create logs directory if it doesn't exist
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
)

echo Starting continuous trading loop...
echo Log file: %LOG_FILE%
echo Press Ctrl+C to stop
echo ============================================================

rem Log startup info
echo Starting continuous trading loop... >> "%LOG_FILE%"
echo Log file: %LOG_FILE% >> "%LOG_FILE%"
echo Press Ctrl+C to stop >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

rem Main loop
:loop
    rem Get timestamp for logging using date command (more reliable)
    for /f "tokens=1-2 delims= " %%a in ('time /t') do (
        set "TIME_NOW=%%a %%b"
    )
    set "CYCLE_TIME=%date% %TIME_NOW%"

    rem Console and log output
    echo [%CYCLE_TIME%] Starting trading cycle
    echo [%CYCLE_TIME%] Starting trading cycle >> "%LOG_FILE%"

    rem Change to root directory and execute trading cycle using venv Python
    pushd %~dp0..
    "%~dp0..\venv\Scripts\python.exe" -m backend.scripts.run_paper_cycle >> "%LOG_FILE%" 2>&1
    popd

    rem Add separator
    echo.
    echo ============================================================
    echo.
    echo ============================================================ >> "%LOG_FILE%"
    echo. >> "%LOG_FILE%"

    rem Wait 60 seconds using Windows-compatible method
    rem ping -n [seconds+1] 127.0.0.1 >nul waits for the specified number of seconds
    ping -n 61 127.0.0.1 >nul

goto loop
endlocal