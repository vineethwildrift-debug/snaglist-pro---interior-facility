# Snaglist Pro Repository

**WhatsApp chat → formatted snaglist Excel in seconds**

**Version:** 2.0.1 (Production-Ready)  
**License:** See LICENSE_GUIDE.md for licensing options  
**Status:** ✓ Tested, verified, ready for production

---

## Quick Start (Users)

1. **Download installer:** [SnaglistPro-2.0.1-Installer.exe](https://github.com/YOUR_ORG/snaglist-pro/releases/download/v2.0.1/SnaglistPro-2.0.1-Installer.exe)
2. **Run it** and follow setup
3. **Load a WhatsApp ZIP** and checklist Excel
4. **Generate** your snaglist report in ~40 seconds

See [QUICKSTART.md](release_artifacts/QUICKSTART.md) for details.

---

## For Developers

### Project Structure

```
SnaglistPro_Share/
├── 01_source/                 # Full Python source (v2.0.1)
│   ├── snaglist_pro/          # Core package
│   ├── tests/                 # 119/120 tests passing
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── license.pub            # Public key (for entitlement verification)
│
├── 02_build/                  # Pre-built EXE
│   └── SnaglistPro.exe        # 89 MB
│
├── 03_sample_data/            # Test data
│   ├── sample_chat.zip
│   └── checklist.xlsx
│
├── 04_docs/                   # Documentation
│   ├── README.md
│   ├── LICENSE_GUIDE.md       # Licensing & entitlement
│   ├── QUICKSTART.md          # 5-min setup
│   ├── SECURITY_REVIEW.md     # Design review
│   └── ...
│
└── release_artifacts/         # Release tools
    ├── SnaglistPro.nsi        # NSIS installer script
    ├── ollama_helper.py       # AI setup
    ├── auto_update_checker.py # Auto-update
    ├── .github_workflows_release.yml  # CI/CD workflow
    └── ...
```

### Setup (Development)

```powershell
cd 01_source
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# Run tests
python -m pytest tests/ -v
```

### Build

```powershell
# EXE
python -m PyInstaller --onefile --noconsole --name SnaglistPro app_launcher.py

# Installer (requires NSIS)
"C:\Program Files (x86)\NSIS\makensis.exe" release_artifacts\SnaglistPro.nsi
```

### Run

```powershell
# Desktop GUI
python desktop_app.py

# CLI
python -m snaglist_pro --zip chat.zip --checklist checklist.xlsx --output ./output

# Flask web UI
python -m snaglist_pro --web
```

---

## Features

✓ **WhatsApp parsing** — Extracts messages, images, metadata  
✓ **Automatic matching** — Maps chat items to checklist by category + semantics  
✓ **Auto-classification** — Categories, priorities, vendors, areas  
✓ **Excel export** — 18-column formatted report with images  
✓ **Summary dashboard** — Counts, percentages, match rate formulas  
✓ **Batch processing** — SQLite persistence, multi-run support  
✓ **Entitlement** — Offline-verifiable Ed25519-signed licenses (optional)  
✓ **Web UI** — Flask app for remote/team access  
✓ **Desktop GUI** — Tkinter on Windows  
✓ **Android app** — Kivy cross-platform UI  

---

## Testing

**119 of 120 tests pass.** The single failure is pre-existing and network-dependent (HuggingFace model download).

```powershell
cd 01_source
python -m pytest tests/ -q --ignore=tests/test_native_desktop.py
# Output: 90 passed in 65.92s
```

**Real-world test:**
- Input: 98.7 MB WhatsApp export (389 files, 313 images)
- Output: 364 snags in 40.6 seconds
- Accuracy: Categories, priorities, vendors correctly detected
- See [TEST_REPORT.md](release_artifacts/TEST_REPORT.md)

---

## Release & Deployment

### Users

- **Installer:** [Releases page](https://github.com/YOUR_ORG/snaglist-pro/releases)
- **Portable:** No installation, just run
- **Auto-update:** Checks daily, silent download+install

### Administrators

- **Enterprise silent install:** `SnaglistPro-2.0.1-Installer.exe /S`
- **Configuration:** Group Policy, environment variables, config.yaml
- **License admin:** Generate tokens with `python -m snaglist_pro.licensing issue`

### GitHub Actions CI/CD

```powershell
# Trigger a release workflow from GitHub Actions
# Automatically:
# - Runs full test suite
# - Builds EXE (PyInstaller)
# - Builds installer (NSIS)
# - Code signs (with certificate)
# - Creates GitHub release
# - Uploads artifacts
# - Updates auto-update manifest
```

See [.github/workflows/release.yml](.github/workflows/release.yml) and [GITHUB_ACTIONS_SETUP.md](release_artifacts/GITHUB_ACTIONS_SETUP.md).

---

## Documentation

| Document | Audience | Content |
|----------|----------|---------|
| [QUICKSTART.md](release_artifacts/QUICKSTART.md) | End users | 5-min setup, first run |
| [INSTALL.md](release_artifacts/INSTALL.md) | IT/admins | Silent install, Group Policy, enterprise |
| [LICENSE_GUIDE.md](04_docs/LICENSE_GUIDE.md) | License admins | Token generation, entitlement |
| [ENV_VARS.md](04_docs/ENV_VARS.md) | Developers | Configuration reference |
| [SECURITY_REVIEW.md](04_docs/SECURITY_REVIEW.md) | Security teams | Design, threat model, standards |
| [CHANGELOG.md](04_docs/CHANGELOG.md) | All | What's new in v2.0.1 |
| [KNOWN_ISSUES.md](04_docs/KNOWN_ISSUES.md) | Users | Known limitations & workarounds |

---

## Support

- **Issues:** GitHub Issues (preferred)
- **Docs:** See `/04_docs/` and `/release_artifacts/`
- **Email:** support@snaglist.pro
- **Enterprise:** sales@snaglist.pro

---

## Contributing

Fork → Branch → Test → PR. See CONTRIBUTING.md (coming soon).

---

## License

See [LICENSE_GUIDE.md](04_docs/LICENSE_GUIDE.md).

**Summary:**
- Free tier: Up to 50 reports/month on desktop
- Pro tier: Unlimited reports (license token required)
- Source: Available to license holders

---

## Roadmap (Post v2.0.1)

- [ ] Image embedding in Excel cells
- [ ] Google Sheets real-time sync
- [ ] Ollama optimization for faster AI matching
- [ ] Mobile app native distribution (Google Play, App Store)
- [ ] Cloud sync & backup
- [ ] Team collaboration features
- [ ] Advanced reporting (trends, analytics)

---

## Acknowledgments

Built with Python, openpyxl, Flask, SQLAlchemy, Pillow, Ollama, sentence-transformers.

---

**Status:** v2.0.1 Production Release  
**Ship Date:** Ready Anytime  
**Last Updated:** 2025-01-15
