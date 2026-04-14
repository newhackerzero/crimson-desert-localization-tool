@echo off
title Crimson Desert Localization Tool - Install Requirements
echo Installing required Python packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Installation complete.
pause
