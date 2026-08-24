@echo off
title Gold Robot - Report
cd /d "%~dp0"

echo.
echo  ============================================
echo    GOLD ROBOT - REPORT
echo  ============================================
echo.
echo    Choose a time period:
echo      1  = Today only
echo      3  = Last 3 days
echo      7  = Last 7 days (one week)
echo      30 = Last 30 days (one month)
echo      A  = All time
echo.
set /p CHOICE=    Type a number (1 / 3 / 7 / 30 / A) and press Enter: 

if /i "%CHOICE%"=="A" set DAYS=0
if "%CHOICE%"=="1" set DAYS=1
if "%CHOICE%"=="3" set DAYS=3
if "%CHOICE%"=="7" set DAYS=7
if "%CHOICE%"=="30" set DAYS=30

if not defined DAYS (
    echo.
    echo    Not a valid choice - I will use last 7 days.
    set DAYS=7
)

echo.
echo    Finding Python ...
if exist "venv\Scripts\python.exe" (
    set PY=venv\Scripts\python.exe
) else (
    set PY=python
)

echo    Building the report (a few seconds) ...
echo.
%PY% robot_report.py --days %DAYS% --html

echo.
echo    Opening the report in your browser ...
start "" "%CD%\data\robot_report.html"

echo.
echo    ============================================
echo    The report is saved here (you can open it any time):
echo      %CD%\data\robot_report.html
echo    ============================================
echo.
pause
