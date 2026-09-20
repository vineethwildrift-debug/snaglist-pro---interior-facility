@echo off
title Process Single Email
if "%~1"=="" (
    echo Drag and drop an email file (.html/.eml) onto this script
    pause
    exit /b
)
cd /d "C:\Users\vinee\snaglist_pro"
python -m snaglist_pro --email "%~1" --tracker "C:\Users\vinee\Downloads\Client onboarding check points - 2026.xlsx"
pause
