@echo off
for /f "tokens=1-2 delims= " %%a in ('time /t') do (
    set "TIME_NOW=%%a %%b"
)
set "CYCLE_TIME=%date% %TIME_NOW%"
echo [%CYCLE_TIME%] Test message