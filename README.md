# SnaglistPro

WhatsApp chat ZIP → formatted snaglist Excel with database persistence and batch processing.

## Quick Start

### Desktop App

```powershell
C:\Users\vinee\Desktop\SnaglistPro_Release\SnaglistPro.exe
```

1. Select a WhatsApp chat ZIP file
2. Select a checklist Excel file
3. Click "Generate"
4. Click "Download" to save the Excel report

### Pipeline (Python)

```python
from snaglist_pro.pipeline import SnaglistPipeline

pipeline = SnaglistPipeline()
result = pipeline.run(
    zip_path="path/to/chat.zip",
    checklist_path="path/to/checklist.xlsx",
    output_dir="path/to/output",
)
# result["excel_path"] contains the output Excel file path
```

### Flask Web UI

```powershell
cd C:\Users\vinee\snaglist_pro
python -m snaglist_pro --web
# Or: flask --app snaglist_pro.web.app run --port 5000
```

Default login uses environment variables `SNAGLIST_APP_USERNAME` and `SNAGLIST_APP_PASSWORD`.

## Features

- **WhatsApp chat parsing**: Extracts messages, images, and media from WhatsApp ZIP exports
- **Automatic deduplication**: Removes duplicate images by perceptual hash (phash)
- **Checklist matching**: Matches chat items to checklist items using category and semantic similarity
- **Area detection**: Auto-detects 25 area/location names from descriptions
- **Category classification**: 17 categories (Electrical, Hvac, Interior, Fire Safety, etc.)
- **Vendor assignment**: Configurable vendor per category
- **Excel report**: 18-column formatted Excel with images embedded
- **Summary dashboard**: Auto-generated summary sheet with counts and percentages
- **Status detection**: Classifies items as Open/Closed based on description keywords
- **Spelling correction**: Auto-corrects common typos in descriptions

## Configuration

Edit `config.yaml` to customize:

- **Vendor overrides**: Map categories to specific vendors
- **Category normalization**: Map raw category names to standardized names
- **Priority keywords**: Keywords that indicate High priority items
- **Image settings**: Resize dimensions and quality

### Environment Variables

All config values can be overridden via environment variables using the `SNAGLIST__` prefix:

```powershell
$env:SNAGLIST__PROJECT__DEFAULT_CLIENT = "My Project"
$env:SNAGLIST__AUTH__USERNAME = "myuser"
$env:SNAGLIST__AUTH__PASSWORD = "mypassword"
```

## Project Structure

```
snaglist_pro/
├── pipeline.py          # Core processing pipeline
├── parse_export.py      # WhatsApp text parsing
├── config.py            # Settings (YAML + env vars)
├── config.yaml          # Default configuration
├── database.py          # SQLite database (SQLAlchemy)
├── models.py            # Database models
├── auth.py              # Authentication
├── ai_client.py         # AI integration (optional)
├── description_enhancer.py  # Text enhancement & typo correction
├── semantic_matcher.py  # Semantic matching
├── summary_dashboard.py # Summary sheet generator
├── image_processor.py   # Image resizing
├── notifications.py     # Notifications
├── web/
│   ├── app.py           # Flask web UI
│   ├── templates/       # HTML templates
│   └── static/          # Static assets
├── tests/               # Test suite (121 tests)
└── README.md            # This file

desktop_app.py         # Tkinter desktop GUI
app_launcher.py        # EXE launcher
mobile_app.py          # Mobile web app
android_app/           # Android app (Kivy)
```

## Excel Output Columns

| Column | Header | Description |
|--------|--------|-------------|
| A | Slno | Sequential number |
| B | Facility Name | Project name |
| C | Client Name | Client name |
| D | Date Given | Date of generation |
| E | Floor | Floor number |
| F | Area/Location | Detected area |
| G | Category | Item category |
| H | Check Points | Checklist check point |
| I | Status | Open/Closed |
| J | Snag Points | Description from chat |
| K | Priority | High/Medium/Low |
| L | Ref. Images | Image reference |
| M | Ref. Images | Image reference |
| N | Date Closed | Closure date |
| O | Closed Images | Closure images |
| P | Vendor Name | Assigned vendor |
| Q | Project SPOC | Project contact |
| R | Transition SPOC | Transition contact |

## Testing

```powershell
cd C:\Users\vinee\snaglist_pro
C:\Python314\python.exe -m pytest tests/ -v
```

97 tests across 10 test files covering:
- Pipeline processing
- Description enhancement
- WhatsApp text parsing
- Authentication
- Desktop app functionality
- Mobile app generation
- Android app generation
- Native desktop features
- Database configuration
- Packaging assets

## Build

```powershell
# Desktop EXE
python -m PyInstaller --onefile --noconsole --name SnaglistPro app_launcher.py

# Web app
flask --app snaglist_pro.web.app run --port 5000
```

## Requirements

- Python >= 3.10
- openpyxl >= 3.1.0
- Pillow >= 10.0.0
- imagehash >= 4.3.0
- pyyaml >= 6.0
- sqlalchemy >= 2.0.0
- flask >= 3.0.0
- sentence-transformers >= 3.0.0 (optional, for semantic matching)

## Known Issues

- Status detection accuracy depends on WhatsApp chat descriptions; items without explicit completion keywords may show as Open
- 125 unmatched items (35.5%) have no vendor assigned; add category to `vendor_overrides` in config.yaml
- Ref. Images column M contains vendor names instead of image references (cosmetic)

## Licensing (paid entitlement)

Snaglist Pro supports an optional paid entitlement using **Option A**: an
offline-verifiable, Ed25519-signed license token. The client ships with the
owner's **public** key only; the private key stays on the owner's machine and
is used solely by the issuer CLI. A token is a signed JSON envelope, so it
cannot be forged without the private key.

### Architecture

- **Entitlement** is decided by a signed token, not a local flag. The client
  verifies the signature against the embedded public key on every run.
- **Clock trust is limited**: a monotonic watermark defends against
  wall-clock rollback; forward drift is tolerated up to the offline grace
  window.
- **Enforcement gates new report generation only** — reading or exporting
  already-produced data is never blocked.
- **State is stored in the OS credential store** (DPAPI on Windows), so the
  token and watermark cannot be edited by another user.
- **Activation limit** per license (default 2 machines). Re-installing the
  same token on an already-activated machine is idempotent.

### Step 1 — Generate a keypair (owner)

```powershell
cd C:\Users\vinee\snaglist_pro
python -m snaglist_pro.licensing gen-keypair `
    --private license.priv --public license.pub
```

This writes two PEM files:

| File | Contents | Where it goes |
|------|----------|---------------|
| `license.priv` | PKCS#8 private key | **Owner's machine only. Never ships.** |
| `license.pub` | SubjectPublicKeyInfo public key | Ships with the client (see step 4) |

The private key is chmod `0600` on non-Windows. Store it safely — anyone with
it can mint valid tokens. The fingerprint printed at the end is a short
identifier for the keypair.

### Step 2 — Issue a license token (owner)

```powershell
python -m snaglist_pro.licensing issue `
    --license-id LIC-001 `
    --customer "Acme Corp" `
    --edition Pro `
    --features "pro,excel,google_sheets" `
    --lease-days 30 `
    --max-activations 2 `
    --private license.priv `
    --output LIC-001.lic
```

| Argument | Meaning |
|----------|---------|
| `--license-id` | Unique identifier for this license |
| `--customer` | Customer name (stored in the token) |
| `--edition` | Edition label (e.g. `Pro`, `Lite`) |
| `--features` | Comma-separated feature tags gated by this license |
| `--lease-days` | Token validity (default 30). Short leases make revocation effective within one cycle. |
| `--max-activations` | Distinct machines this license may activate (default 2) |
| `--machine-hash` | Optional: bind the token to one machine fingerprint |
| `--private` | Path to the owner's private key |
| `--output` | Where to write the `.lic` file |

The token embeds `not_before` (now − 5 min) and `not_after` (now + lease), so
tokens issued near midnight are valid immediately.

### Step 3 — Deliver the token to the customer

Send the `.lic` file to the customer. It is a plain JSON envelope; it contains
no secrets — only the signed payload and the Ed25519 signature. A leaked
token is valid until its `not_after`, and can be revoked only by issuing a
new token (short leases limit the blast radius).

### Step 4 — Install the public key and token on the customer's machine

**Public key** — place `license.pub` in the application package directory
(`snaglist_pro/license.pub`) or set the environment variable:

```powershell
$env:SNAGLIST_LICENSE_PUBLIC_KEY = "C:\path\to\license.pub"
```

**Token** — place the `.lic` file in the license state directory and run the
pipeline with `--license-check`:

```powershell
$env:SNAGLIST_LICENSE_DIR = "C:\Users\<user>\AppData\Local\SnaglistPro\license"
$env:SNAGLIST_LICENSE_PUBLIC_KEY = "C:\path\to\license.pub"
python -m snaglist_pro --zip chat.zip --checklist checklist.xlsx --output ./output --license-check
```

On first run the token is read, signature-verified, and stored in the OS
credential store (DPAPI on Windows) along with a monotonic watermark and the
attempt counter. Subsequent runs re-validate without re-entering the token.

### Step 5 — Verify a token without installing it

```powershell
$env:SNAGLIST_LICENSE_PUBLIC_KEY = "C:\path\to\license.pub"
python -m snaglist_pro.licensing verify LIC-001.lic
```

Prints the decoded payload (license id, edition, features, expiry).

### Renewal and revocation

- **Renew** by issuing a new token with the same `--license-id`. The client
  keeps the newest valid token.
- **Revoke** by not renewing: the lease expires, a 7-day offline grace window
  runs, then new report generation is locked. Reading existing output is
  unaffected.
- **Hard-locked install** (after repeated failed checks) requires a
  single-use reset key:

```powershell
python -m snaglist_pro.licensing reset-key --private license.priv
```

Pass the printed key to the locked machine; it clears the attempt counter.

### Programmatic use

```python
from snaglist_pro.pipeline import SnaglistPipeline
from snaglist_pro import licensing

entitlement = licensing.evaluate_entitlement()
if entitlement["gated"]:
    raise RuntimeError(entitlement["reason"])

result = SnaglistPipeline().run(
    zip_path="chat.zip",
    checklist_path="checklist.xlsx",
    output_dir="./output",
    license_check=True,  # gates report generation on the entitlement
)
```

### Environment variables

| Variable | Purpose |
|----------|---------|
| `SNAGLIST_LICENSE_DIR` | State directory (token, watermark, attempts) |
| `SNAGLIST_LICENSE_PUBLIC_KEY` | Path to the owner's public key |
| `SNAGLIST_LICENSE_PRIVATE_KEY` | Path to the owner's private key (issuer only) |
