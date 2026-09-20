@echo off
title Email Tracker Watcher
echo Starting Email Tracker Watcher...
echo Drop email files into: C:\Users\vinee\Downloads\EmailTracker\watcher
echo.
cd /d "C:\Users\vinee\snaglist_pro"
python -m snaglist_pro --watch "C:\Users\vinee\Downloads\EmailTracker\watcher" --tracker "C:\Users\vinee\Downloads\Client onboarding check points - 2026.xlsx"
pause
