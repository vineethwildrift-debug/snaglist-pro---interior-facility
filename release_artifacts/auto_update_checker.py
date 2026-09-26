#!/usr/bin/env python
"""Auto-update checker for Snaglist Pro (Windows).

Runs periodically, checks manifest, downloads and installs updates.
Can be embedded as a scheduled task or run on app startup.
"""

import os
import sys
import json
import logging
import hashlib
import requests
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta

MANIFEST_URL = os.getenv(
    "SNAGLIST_UPDATE_MANIFEST",
    "https://releases.snaglist.pro/update-manifest-stable.json"
)
UPDATE_CHECK_INTERVAL = 86400  # 1 day

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


def get_current_version() -> str:
    """Get installed version from registry."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\SnaglistPro") as key:
            version, _ = winreg.QueryValueEx(key, "Version")
            return version
    except Exception:
        return "0.0.0"


def should_check_for_update() -> bool:
    """Check if enough time has passed since last update check."""
    last_check_file = Path.home() / ".snaglist_pro" / "last_update_check"
    
    if not last_check_file.exists():
        return True
    
    try:
        last_check = datetime.fromisoformat(last_check_file.read_text())
        if datetime.now() - last_check > timedelta(seconds=UPDATE_CHECK_INTERVAL):
            return True
    except Exception:
        return True
    
    return False


def record_update_check() -> None:
    """Record the time of this update check."""
    check_dir = Path.home() / ".snaglist_pro"
    check_dir.mkdir(parents=True, exist_ok=True)
    
    last_check_file = check_dir / "last_update_check"
    last_check_file.write_text(datetime.now().isoformat())


def fetch_manifest() -> Optional[Dict]:
    """Fetch the update manifest."""
    try:
        resp = requests.get(MANIFEST_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.warning(f"Failed to fetch manifest: {e}")
        return None


def verify_checksum(file_path: Path, expected_sha256: str) -> bool:
    """Verify SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    
    actual = sha256.hexdigest().lower()
    expected = expected_sha256.lower()
    
    if actual != expected:
        log.error(f"Checksum mismatch: {actual} != {expected}")
        return False
    
    return True


def download_installer(url: str, dest: Path) -> bool:
    """Download installer with progress."""
    try:
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = (downloaded / total) * 100
                        log.info(f"Download: {pct:.1f}%")
        
        log.info(f"✓ Downloaded to {dest}")
        return True
    except Exception as e:
        log.error(f"Download failed: {e}")
        return False


def install_update(installer_path: Path) -> bool:
    """Launch the installer (elevated)."""
    try:
        import subprocess
        # /S = silent, /D sets install dir
        result = subprocess.run(
            [str(installer_path), "/S"],
            check=False
        )
        
        if result.returncode == 0:
            log.info("✓ Update installed. Restart the app to apply.")
            return True
        else:
            log.error(f"Installer exited with code {result.returncode}")
            return False
    except Exception as e:
        log.error(f"Installation failed: {e}")
        return False


def check_for_updates(silent: bool = True) -> bool:
    """Main update check logic."""
    if not should_check_for_update():
        log.debug("Update check not yet due")
        return False
    
    record_update_check()
    
    manifest = fetch_manifest()
    if not manifest:
        return False
    
    current = get_current_version()
    available = manifest.get("version")
    
    log.info(f"Current: {current}, Available: {available}")
    
    if available <= current:
        if not silent:
            log.info("Already on the latest version")
        return False
    
    log.info(f"Update available: {current} → {available}")
    
    download_info = manifest.get("downloads", {}).get("installer_exe")
    if not download_info:
        log.error("No installer found in manifest")
        return False
    
    # Download
    dest = Path.home() / ".snaglist_pro" / "pending_update.exe"
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    if not download_installer(download_info["url"], dest):
        return False
    
    # Verify checksum
    if not verify_checksum(dest, download_info["sha256"]):
        dest.unlink()
        return False
    
    log.info("Update ready to install")
    
    if not silent:
        resp = input(f"\nUpdate available: {available}\nInstall now? [Y/n]: ").strip().lower()
        if resp == "n":
            return False
    
    return install_update(dest)


def cli_main():
    """CLI entrypoint."""
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check_for_updates(silent=False)
    else:
        check_for_updates(silent=True)


if __name__ == "__main__":
    cli_main()
