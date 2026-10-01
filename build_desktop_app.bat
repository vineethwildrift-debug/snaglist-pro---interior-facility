@echo off
cd /d "%~dp0"
python -m pip install --upgrade pip
python -m pip install pyinstaller
pyinstaller --clean --noconfirm SnaglistPro.spec

REM Optional: build an installer with Inno Setup later
ECHO.
ECHO Desktop app build completed.
ECHO Output folder: dist
pause
