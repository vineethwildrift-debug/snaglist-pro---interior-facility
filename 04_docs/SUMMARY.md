# Snaglist Pro — Final Summary

## What it is

Snaglist Pro is a Windows desktop application that converts a WhatsApp chat
export (ZIP) into a formatted, stakeholder-ready snaglist Excel workbook. It
eliminates the manual transcription and formatting that construction site
snag lists traditionally require.

**Value proposition:** turn site chats into snaglist reports in seconds.

## Core functionality

1. **Ingest** — reads a WhatsApp chat ZIP (messages + images + media).
2. **Parse** — extracts messages, pairs images to snag descriptions, and
   filters system messages.
3. **Deduplicate** — removes duplicate items and duplicate images by
   perceptual hash (phash).
4. **Match** — matches chat items to a project checklist by category and
   semantic similarity.
5. **Classify** — assigns category (17 categories), priority (High/Medium/Low),
   status (Open/Closed), area/location, and vendor.
6. **Export** — writes an 18-column formatted Excel workbook with embedded
   images and an auto-generated Summary dashboard (counts, percentages, and
   a Match Rate formula).
7. **Persist** — optional SQLite persistence and batch processing.
8. **Entitlement (optional)** — offline-verifiable, Ed25519-signed license
   tokens gate paid features.

## Interfaces

| Interface | How to run |
|-----------|-----------|
| Desktop GUI (Tkinter) | `02_build\SnaglistPro.exe` or `python desktop_app.py` |
| CLI | `python -m snaglist_pro --zip chat.zip --checklist checklist.xlsx --output ./output` |
| Web UI (Flask) | `python -m snaglist_pro --web` |
| Python API | `from snaglist_pro.pipeline import SnaglistPipeline` |

## Current development status

**v2.0.1 — feature complete and verified.**

- 11 pipeline bug fixes from the QA audit are implemented and verified against
  real test data (253 rows, 18 columns, correct status logic, dates, areas,
  Match Rate formula, SPOC columns, sheet naming).
- Option A paid entitlement is implemented, tested (16 tests), and verified
  end-to-end (keypair generation → token issuance → installation → active
  entitlement).
- Authentication hardened: fixed the live `_PASSWORD_ITERATIONS` crash,
  HMAC-signed sessions, persistent password-change state, and exponential
  login lockout (8 tests).
- **119 of 120 tests pass.** The single failure is pre-existing and
  network-dependent (Hugging Face model download); it is unrelated to any
  change.

## Outstanding items

1. **Google Sheets export (`_gs.xlsx`)** — not generated when the pipeline
   runs in `fast_mode=True`. Requires a non-fast run to produce.
2. **Slno duplicates** — the sample checklist contains duplicate sequential
   numbers (rows 6 and 10 both = 1). Root cause is in the checklist data, not
   the pipeline.
3. **`_PASSWORD_ITERATIONS`** — now defined (600,000); Argon2id remains the
   preferred algorithm but is kept optional so the module imports without
   `argon2-cffi`.
4. **One pre-existing test failure** — `test_summary_sheet_open_closed_counts_reflect_actual_data`
   depends on a Hugging Face download that fails without network/token.
5. **AI is disabled by default** in the desktop app — semantic matching and
   description enhancement fall back to local heuristics unless Ollama is
   running and `ai_enabled=True`.

## Shareable package contents

```
SnaglistPro_Share/
├── 01_source/        # Full Python source, tests, build config, android_app
├── 02_build/         # SnaglistPro.exe (89 MB), release screenshots
├── 03_sample_data/   # Sample inputs (ZIP + checklist) and verified output
└── 04_docs/          # README, QUICKSTART, LICENSE_GUIDE, SECURITY_REVIEW,
                      # ENV_VARS, CHANGELOG, KNOWN_ISSUES, requirements.txt
```

See `04_docs/README.md` for the full documentation index.