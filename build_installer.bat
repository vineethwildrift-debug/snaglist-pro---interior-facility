@echo off
cd /d "%~dp0"
if not exist dist\SnaglistPro.exe (
    echo Building EXE first...
    python -m PyInstaller --clean --noconfirm SnaglistPro.spec
)

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"

if defined ISCC (
    echo Building installer with %ISCC%
    "%ISCC%" /O"output" "installer\SnaglistPro.iss"
) else (
    echo Inno Setup not found. Install Inno Setup and then run this script again.
    exit /b 1
)

pause
