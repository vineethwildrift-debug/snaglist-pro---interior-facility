# Snaglist Pro Desktop Release Guide

This project is now structured for a desktop-first installation flow.

## Desktop app behavior

- App data is stored in the current user's Local AppData folder.
- The app does not rely on the project folder for runtime data.
- This makes it more stable when packaged into a Windows EXE.

## Default login

- Username: admin
- Password: admin123

## Build commands

From the project root:

```powershell
python -m PyInstaller --onefile --noconsole --name SnaglistPro app_launcher.py --collect-submodules snaglist_pro
```

The built file is created in the `dist` folder.

## App data directory

On Windows, runtime files are stored under:

```text
%LOCALAPPDATA%\SnaglistPro\
```

This includes uploaded ZIP files, generated outputs, and temporary processing data.
