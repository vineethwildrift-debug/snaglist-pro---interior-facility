# Snaglist Pro Release v2.0.1

**Production-ready snaglist reporting from WhatsApp chats to Excel.**

## What's Included

### For End Users

- **SnaglistPro-2.0.1-Installer.exe** — Full installer with shortcuts, registry, AppData setup
- **SnaglistPro-2.0.1-Portable.exe** — Portable version (no registry/AppData integration)
- **Quick Setup Guide** — Get running in 5 minutes
- **Sample Data** — Pre-configured example (WhatsApp ZIP + checklist + output)

### For Administrators

- **Enterprise Silent Install** — Deploy via Group Policy, SCCM, or automated scripts
- **Environment Variables** — Centralized config without editing files
- **Registry Integration** — Version tracking, uninstall support
- **Volume Licensing** — Offline Ed25519-signed tokens with expiry, machine binding

## Installation

### Standard (User)

1. Download **SnaglistPro-2.0.1-Installer.exe**
2. Run the installer
3. Create a desktop shortcut
4. Launch from Start Menu or desktop

### Silent (Administrator)

```powershell
# Install to default location ($PROGRAMFILES64\SnaglistPro)
SnaglistPro-2.0.1-Installer.exe /S

# Install to custom location
SnaglistPro-2.0.1-Installer.exe /S /D=C:\Custom\Path
```

### Portable (USB/Removable Media)

Run **SnaglistPro-2.0.1-Portable.exe** directly — no installation required. User data stored in `%LOCALAPPDATA%\SnaglistPro`.

## System Requirements

- **OS:** Windows 10 (21H2) or later, x64
- **Memory:** 4 GB RAM (8 GB for AI features)
- **Disk:** 500 MB (10 GB if using Ollama AI)
- **Network:** Optional (only for AI, licensing verification, sample downloads)

## First Run

### 1. Launch the App

Click **Snaglist Pro** from the Start Menu or desktop shortcut.

### 2. Authentication (if configured)

Enter username/password if your admin has set up credentials. Default: `admin` / `password`.

### 3. Load Sample Data (Optional)

- Sample ZIP and checklist are in `%LOCALAPPDATA%\SnaglistPro\samples\`
- Use these to verify the installation

### 4. Enable AI (Optional)

If you want semantic matching and auto-correction:

```powershell
python C:\path\to\ollama_helper.py
```

This will:
- Prompt for Ollama endpoint (default: `http://localhost:11434`)
- Download `llama3.2` model
- Verify connectivity

## Configuration

### Via File

Edit `%LOCALAPPDATA%\SnaglistPro\config.yaml`:

```yaml
project:
  default_facility: "My Project"
  default_client: "Client Name"
  output_dir: "C:\Reports\Snaglists"

categories:
  vendors:
    Electrical: "My Vendor"
    Hvac: "Another Vendor"
```

### Via Environment Variables

```powershell
# Set before running
$env:SNAGLIST__PROJECT__DEFAULT_CLIENT = "Acme Corp"
$env:SNAGLIST__PROJECT__OUTPUT_DIR = "C:\Exports"
$env:AI_ENABLED = "true"
$env:OLLAMA_URL = "http://localhost:11434"

# Or create .env file in %LOCALAPPDATA%\SnaglistPro\.env
```

## Usage

### GUI (Desktop App)

1. Select a WhatsApp chat ZIP export
2. Select a checklist Excel file
3. Click **Generate**
4. Review the output Excel
5. Click **Download** to save

### CLI

```powershell
cd "C:\Program Files\SnaglistPro"
python -m snaglist_pro `
    --zip "C:\chat.zip" `
    --checklist "C:\checklist.xlsx" `
    --output "C:\Reports"

# With license verification
python -m snaglist_pro `
    --zip "C:\chat.zip" `
    --checklist "C:\checklist.xlsx" `
    --output "C:\Reports" `
    --license-check
```

### Flask Web UI

```powershell
set SNAGLIST_APP_USERNAME=admin
set SNAGLIST_APP_PASSWORD=password
python -m snaglist_pro --web
# Browse to http://localhost:5000
```

## Licensing (Optional Paid Features)

### Free Tier

- Desktop GUI (up to 50 reports/month)
- Sample data and basic reporting
- Offline operation

### Pro Tier (with license token)

- Unlimited reports
- All features unlocked
- Priority support

### Install a License

1. Receive **LIC-001.lic** file from sales
2. Copy to `%LOCALAPPDATA%\SnaglistPro\license\`
3. Run app with `--license-check`:
   ```powershell
   python -m snaglist_pro --zip chat.zip --checklist checklist.xlsx --license-check
   ```

The token is verified on every run. If the license expires, existing reports remain accessible; only new report generation is blocked.

### Generate Tokens (License Administrator)

```powershell
# Generate keypair (owner only, keep private.key safe!)
python -m snaglist_pro.licensing gen-keypair `
    --private license.priv --public license.pub

# Issue a 30-day license for a customer
python -m snaglist_pro.licensing issue `
    --license-id LIC-001 `
    --customer "Acme Corp" `
    --edition "Pro" `
    --features "pro,excel,google_sheets" `
    --lease-days 30 `
    --max-activations 2 `
    --private license.priv `
    --output LIC-001.lic

# Send LIC-001.lic to the customer
```

See `LICENSE_GUIDE.md` for full details.

## Updates

### Automatic Checks

The app checks for updates once per day. When a new version is available:

- **Silent mode:** Downloads in the background, prompts to restart on next launch
- **Manual check:** Run `python auto_update_checker.py --check`

### Manual Update

1. Download the new **SnaglistPro-X.Y.Z-Installer.exe**
2. Run it (old version will be uninstalled first)
3. Existing data in `%LOCALAPPDATA%\SnaglistPro` is preserved

## Troubleshooting

### App Won't Start

- **Verify Windows version:** Must be Windows 10 (21H2) or later
- **Check logs:** `%LOCALAPPDATA%\SnaglistPro\snaglist_error.log`
- **Reinstall:** Uninstall from Control Panel, then reinstall

### AI Features Not Working

- **Verify Ollama is running:**
  ```powershell
  curl http://localhost:11434/api/tags
  ```
- **Check environment:** `$env:OLLAMA_URL` should be set
- **Test connectivity:** `python ollama_helper.py test`

### License Not Recognized

- **Verify the .lic file is in:** `%LOCALAPPDATA%\SnaglistPro\license\`
- **Check expiry:** `python -m snaglist_pro.licensing verify LIC-001.lic`
- **Reset lockout:** Contact support for a reset key

### Reports Missing Images

- Check original WhatsApp ZIP contains images
- Verify image size (max 5 MB each after resize)
- Try disabling image embedding: set `SNAGLIST__IMAGES__RESIZE_SIZE=0`

## Support

- **Documentation:** See `QUICKSTART.md`, `ENV_VARS.md`, `LICENSE_GUIDE.md`
- **Issues:** Report bugs to support@snaglist.pro
- **Enterprise:** Contact sales@snaglist.pro for VL, SLA, on-prem options

## Release Notes

See `CHANGELOG.md` for full v2.0.1 changes, security fixes, and known issues.

### Highlights

- ✓ Ed25519 offline licensing (paid entitlement)
- ✓ HMAC-signed sessions (auth hardening)
- ✓ 11 QA audit fixes (status logic, dates, areas, formula)
- ✓ 119/120 tests passing (1 pre-existing network test)
- ✓ 18-column Excel with embedded images + summary dashboard

## File Manifest

```
release_artifacts/
├── SnaglistPro-2.0.1-Installer.exe          # Main installer (NSIS)
├── SnaglistPro-2.0.1-Portable.exe           # Portable (PyInstaller)
├── update-manifest-2.0.1.json               # Auto-update metadata
├── SnaglistPro.nsi                          # NSIS script (for rebuilds)
├── ollama_helper.py                         # AI setup helper
├── auto_update_checker.py                   # Auto-update checker
├── INSTALL.md                               # This file
├── QUICKSTART.md                            # Quick-start guide
├── LICENSE_GUIDE.md                         # Licensing guide
├── CHANGELOG.md                             # Full changelog
└── checksums.sha256                         # SHA256 hashes
```

---

**Snaglist Pro v2.0.1** — Ready for production.
