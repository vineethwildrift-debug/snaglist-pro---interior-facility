# Snaglist Pro — Shareable Package

A WhatsApp chat export → formatted snaglist Excel pipeline for construction
site snag lists. Turns site chats into stakeholder-ready snaglist reports in
seconds, eliminating manual transcription and formatting.

This folder contains everything an external stakeholder needs to evaluate,
run, and (optionally) license the application:

| Folder | Purpose |
|--------|---------|
| `01_source` | Full Python source, tests, and build configuration |
| `02_build` | Pre-built Windows executable and release screenshots |
| `03_sample_data` | Sample input ZIP, checklist, and a verified output |
| `04_docs` | Instruction files and documentation |

## What it does

Snaglist Pro ingests a WhatsApp chat ZIP export (messages + images), parses
the conversation into snag items, matches them against a project checklist,
classifies each item by category and priority, detects its status
(Open/Closed), and writes a formatted 18-column Excel report with an embedded
summary dashboard and embedded images.

Key capabilities:

- **WhatsApp parsing** — extracts messages, images, and media from chat ZIPs
- **Automatic deduplication** — removes duplicate items and duplicate images
  by perceptual hash (phash)
- **Checklist matching** — matches chat items to checklist items by category
  and semantic similarity
- **Area detection** — auto-detects 25 area/location names from descriptions
- **Category classification** — 17 categories (Electrical, Hvac, Interior,
  Fire Safety, etc.)
- **Vendor assignment** — configurable vendor per category, with overrides
- **Excel report** — 18-column formatted workbook with embedded images
- **Summary dashboard** — auto-generated summary sheet with counts,
  percentages, and a Match Rate formula
- **Status detection** — classifies items as Open/Closed from description
  keywords
- **Spelling correction** — auto-corrects common typos in descriptions
- **Optional paid entitlement** — offline-verifiable, Ed25519-signed license
  tokens (see `LICENSE_GUIDE.md`)

## Interfaces

- **Desktop GUI** (Tkinter) — `02_build\SnaglistPro.exe`, or
  `python desktop_app.py`
- **CLI** — `python -m snaglist_pro --zip chat.zip --checklist checklist.xlsx --output ./output`
- **Web UI** (Flask) — `python -m snaglist_pro --web`
- **Python API** — `from snaglist_pro.pipeline import SnaglistPipeline`

## Quick start

See `QUICKSTART.md` for runnable commands.

## Requirements

- Python >= 3.10
- `openpyxl`, `Pillow`, `imagehash`, `pyyaml`, `sqlalchemy`,
  `python-dotenv`, `rapidfuzz`, `sentence-transformers`, `requests`,
  `flask`, `gunicorn`
- `cryptography` and `pywin32` are required for the optional license module
  (`04_docs/LICENSE_GUIDE.md`)

## Documentation

- `04_docs/README.md` — this file
- `04_docs/QUICKSTART.md` — runnable first-run commands
- `04_docs/LICENSE_GUIDE.md` — paid entitlement setup and issuance
- `04_docs/SECURITY_REVIEW.md` — security review of the entitlement design
- `04_docs/ENV_VARS.md` — environment variable reference
- `04_docs/CHANGELOG.md` — change history
- `04_docs/KNOWN_ISSUES.md` — known issues and workarounds
- `04_docs/SUMMARY.md` — final summary of the application and its status

## Testing

```powershell
cd 01_source
python -m pytest tests/ -q
```

119 of 120 tests pass. The single failing test
(`test_summary_sheet_open_closed_counts_reflect_actual_data`) is a pre-existing
network-dependent test (Hugging Face model download) unrelated to any change.