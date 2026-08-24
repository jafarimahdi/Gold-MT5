@echo off
title Gold Trading Bot
cd /d "%~dp0"

echo.
echo  ==================================================
echo   GOLD TRADING BOT - STARTING
echo  ==================================================
echo.

REM ---- 1) is Python installed? ----
where python >nul 2>nul
if errorlevel 1 goto nopython

REM ---- 2) close every OLD bot (any python running main.py) ----
echo  Closing any previous bot instance...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'main.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" 2>nul
timeout /t 2 /nobreak >nul

REM ---- 3) remove the leftover lock so the new bot can start ----
if exist "data\bot.lock" del /q "data\bot.lock" 2>nul

REM ---- 4) create the virtual environment on first run ----
if not exist "venv\Scripts\activate.bat" (
    echo  [SETUP] First run - creating the private environment.
    echo          This happens only once - takes a minute.
    python -m venv venv
)

call venv\Scripts\activate.bat

REM ---- 5) install the required packages on first run ----
python -c "import pandas" >nul 2>nul
if errorlevel 1 (
    echo  [SETUP] Installing required packages - once - a few minutes.
    pip install -r requirements.txt
)

echo.
echo  Starting the bot. It keeps running until you close this window.
echo  To STOP - close this window or press Ctrl+C.
echo.

python main.py --loop

echo.
echo  The bot has stopped. This window closes in 5 seconds.
timeout /t 5 >nul
exit /b 0

:nopython
echo  [ERROR] Python is not installed.
echo  Install Python 3 from python.org and tick Add Python to PATH.
echo.
timeout /t 10 >nul
exit /b 1
