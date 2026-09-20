import os
import sys
from pathlib import Path


def create_shortcut():
    app_dir = Path(__file__).resolve().parent
    exe_path = app_dir / "dist" / "SnaglistPro.exe"
    if not exe_path.exists():
        print("Executable not found. Build the app first.")
        return

    try:
        import win32com.client
    except Exception as exc:
        print(f"Shortcut creation failed: {exc}")
        return

    desktop = Path.home() / "Desktop"
    desktop.mkdir(exist_ok=True)

    shortcut_path = desktop / "Snaglist Pro.lnk"
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(exe_path)
    shortcut.WorkingDirectory = str(exe_path.parent)
    shortcut.IconLocation = str(exe_path)
    shortcut.Description = "Snaglist Pro desktop app"
    shortcut.save()

    start_menu = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    start_menu.mkdir(parents=True, exist_ok=True)
    start_shortcut = shell.CreateShortCut(str(start_menu / "Snaglist Pro.lnk"))
    start_shortcut.Targetpath = str(exe_path)
    start_shortcut.WorkingDirectory = str(exe_path.parent)
    start_shortcut.IconLocation = str(exe_path)
    start_shortcut.Description = "Snaglist Pro desktop app"
    start_shortcut.save()

    print(f"Desktop shortcut created at: {shortcut_path}")
    print(f"Start menu shortcut created at: {start_menu / 'Snaglist Pro.lnk'}")


if __name__ == "__main__":
    create_shortcut()
