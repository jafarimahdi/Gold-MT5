@echo off
title Gold Trading Bot - Test
cd /d "%~dp0"

echo.
echo  ==================================================
echo   GOLD TRADING BOT - CONNECTION TEST
echo  ==================================================
echo  Make sure MetaTrader 5 is OPEN and logged into a
echo  demo account, then watch the results below.
echo.

where python >nul 2>nul
if errorlevel 1 goto nopython

if not exist "venv\Scripts\activate.bat" goto makevenv
goto venvready

:makevenv
echo  [SETUP] Creating environment - first run, one minute
python -m venv venv

:venvready
call venv\Scripts\activate.bat
python -c "import pandas, MetaTrader5; from google import genai" >nul 2>nul
if errorlevel 1 pip install -r requirements.txt

echo.
python mt5_test.py
echo.
pause
exit /b 0

:nopython
echo  [ERROR] Python is not installed.
echo  Install Python 3 from python.org and tick Add Python to PATH.
echo.
pause
exit /b 1
