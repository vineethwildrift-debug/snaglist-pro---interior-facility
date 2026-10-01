@echo off
cd /d "%~dp0"
if not exist dist\SnaglistPro.exe (
    echo Building EXE first...
    python -m PyInstaller --clean --noconfirm SnaglistPro.spec
)

if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    echo Building installer...
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /O"output" "installer\SnaglistPro.iss"
) else (
    echo Inno Setup not found. Install Inno Setup and then run this script again.
)

pause
