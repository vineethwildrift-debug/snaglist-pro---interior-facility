#!/usr/bin/env python
"""
Release verification script — runs pre-flight checks before shipping.
Tests installer, portable, licensing, documentation completeness.
"""

import os
import sys
import json
import zipfile
import hashlib
from pathlib import Path


def check_file_exists(path: str, description: str) -> bool:
    """Verify a file exists."""
    if Path(path).exists():
        print(f"[OK] {description}")
        return True
    else:
        print(f"[FAIL] MISSING: {description} at {path}")
        return False


def check_sha256(file_path: str, expected_hash: str) -> bool:
    """Verify file SHA256."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        actual = sha256.hexdigest().lower()
        if actual == expected_hash.lower():
            print(f"[OK] {Path(file_path).name}: checksum valid")
            return True
        else:
            print(f"[FAIL] {Path(file_path).name}: checksum mismatch")
            print(f"  Expected: {expected_hash}")
            print(f"  Actual:   {actual}")
            return False
    except Exception as e:
        print(f"[FAIL] Error checking {file_path}: {e}")
        return False


def check_json_valid(file_path: str) -> bool:
    """Verify JSON file is valid."""
    try:
        with open(file_path) as f:
            json.load(f)
        print(f"[OK] {Path(file_path).name}: valid JSON")
        return True
    except Exception as e:
        print(f"[FAIL] {Path(file_path).name}: invalid JSON: {e}")
        return False


def check_nsis_script(file_path: str) -> bool:
    """Basic NSIS script validation."""
    try:
        with open(file_path) as f:
            content = f.read()
        
        required = ["InstallDir", "Section", "File", "WriteRegStr", "CreateShortcut"]
        missing = [req for req in required if req not in content]
        
        if missing:
            print(f"[FAIL] {Path(file_path).name}: missing {missing}")
            return False
        
        print(f"[OK] {Path(file_path).name}: structure valid")
        return True
    except Exception as e:
        print(f"[FAIL] Error reading {file_path}: {e}")
        return False


def main():
    """Run all checks."""
    print("\n=== Snaglist Pro v2.0.1 Release Verification ===\n")
    
    base = Path("C:/Users/vinee/Downloads/SnaglistPro_Share")
    release = base / "release_artifacts"
    source = base / "01_source"
    build = base / "02_build"
    docs = base / "04_docs"
    
    checks = []
    
    # Binaries
    print("Binaries:")
    checks.append(check_file_exists(build / "SnaglistPro.exe", "EXE (02_build/SnaglistPro.exe)"))
    checks.append(check_sha256(str(build / "SnaglistPro.exe"), "8AA5F19EEBFCF3B719AE159CAAA02B2218C6D3D08E1CD0DD791CBDFE48115B73"))
    
    # Installer & Tooling
    print("\nInstaller & Tooling:")
    checks.append(check_file_exists(release / "SnaglistPro.nsi", "NSIS script (release_artifacts/)"))
    checks.append(check_nsis_script(release / "SnaglistPro.nsi"))
    checks.append(check_file_exists(release / "ollama_helper.py", "Ollama helper (release_artifacts/)"))
    checks.append(check_file_exists(release / "auto_update_checker.py", "Auto-update checker (release_artifacts/)"))
    
    # Manifests & Config
    print("\nManifests & Configuration:")
    checks.append(check_file_exists(release / "update-manifest-2.0.1.json", "Update manifest (release_artifacts/)"))
    checks.append(check_json_valid(release / "update-manifest-2.0.1.json"))
    checks.append(check_file_exists(release / "checksums.sha256", "Checksums (release_artifacts/)"))
    
    # Documentation
    print("\nDocumentation:")
    checks.append(check_file_exists(release / "INSTALL.md", "Installation guide (release_artifacts/)"))
    checks.append(check_file_exists(release / "QUICKSTART.md", "Quick-start guide (release_artifacts/)"))
    checks.append(check_file_exists(docs / "README.md", "README (04_docs/)"))
    checks.append(check_file_exists(docs / "CHANGELOG.md", "Changelog (04_docs/)"))
    checks.append(check_file_exists(docs / "LICENSE_GUIDE.md", "Licensing guide (04_docs/)"))
    checks.append(check_file_exists(docs / "SECURITY_REVIEW.md", "Security review (04_docs/)"))
    checks.append(check_file_exists(docs / "ENV_VARS.md", "Environment vars (04_docs/)"))
    
    # Source & Tests
    print("\nSource & Tests:")
    checks.append(check_file_exists(source / "pyproject.toml", "pyproject.toml (01_source/)"))
    checks.append(check_file_exists(source / "requirements.txt", "requirements.txt (01_source/)"))
    checks.append(check_file_exists(source / "license.pub", "Public key (01_source/)"))
    checks.append(check_file_exists(source / "license.priv", "Private key (01_source/) - KEEP SAFE"))
    checks.append(check_file_exists(source / "tests", "Test suite (01_source/tests/)"))
    
    # Sample Data
    print("\nSample Data:")
    checks.append(check_file_exists(base / "03_sample_data", "Sample data (03_sample_data/)"))
    
    # Summary
    print(f"\n{'='*60}")
    passed = sum(checks)
    total = len(checks)
    print(f"Verification: {passed}/{total} checks passed")
    
    if passed == total:
        print("[OK] READY FOR RELEASE")
        return 0
    else:
        print("[FAIL] RELEASE BLOCKED — fix failures above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
