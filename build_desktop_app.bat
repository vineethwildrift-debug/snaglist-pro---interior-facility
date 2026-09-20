@echo off
cd /d "%~dp0"
python -m pip install --upgrade pip
python -m pip install pyinstaller
pyinstaller --onefile --noconsole --name SnaglistPro app_launcher.py --collect-submodules snaglist_pro

REM Optional: build an installer with Inno Setup later
ECHO.
ECHO Desktop app build completed.
ECHO Output folder: dist
pause
