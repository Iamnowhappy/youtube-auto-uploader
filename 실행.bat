@echo off
chcp 65001 > nul
title YouTube Manager

cd /d "%~dp0"

echo.
echo  Starting YouTube Manager...
echo.

python -c "import gspread, dropbox, requests" 2>nul
if errorlevel 1 (
    echo  Installing required libraries...
    python -m pip install requests gspread google-auth google-api-python-client dropbox --quiet
)

python youtube_manager_ui.py

if errorlevel 1 (
    echo.
    echo  Error occurred. Press any key to exit.
    pause
)
