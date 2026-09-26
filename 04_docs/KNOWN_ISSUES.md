# Snaglist Pro — Known Issues

Items observed during the QA audit and development of v2.0.1. Workarounds are
listed where available.

## Pipeline

- **Status detection accuracy depends on WhatsApp chat descriptions.** Items
  without explicit completion keywords may show as Open. Review the
  `determine_status()` keyword lists in `pipeline.py` if a project's chat
  uses different phrasing.
- **125 unmatched items (35.5%) have no vendor assigned.** Add the missing
  categories to `vendor_overrides` in `config.yaml`.
- **Ref. Images column M contains vendor names instead of image references.**
  Cosmetic; the image references are in columns L and N.
- **Duplicate `Slno` values** may appear when the checklist itself contains
  duplicate sequential numbers (observed at rows 6 and 10 of the sample
  checklist, both `Slno = 1`). This originates in the checklist data, not the
  pipeline.

## AI

- **AI is disabled in the desktop app by default** (`fast_mode=False,
  ai_enabled=False`). Semantic matching and description enhancement then fall
  back to local heuristics. Enable by passing `ai_enabled=True` or setting
  `AI_ENABLED=true` and running Ollama.
- **Ollama must be running** at `http://localhost:11434` for AI features.
- **Unauthenticated Hugging Face Hub requests** produce a warning and are
  rate-limited. Set `HF_TOKEN` to remove the warning and raise the limit.

## Licensing

- **Offline revocation is not instant.** A leaked token is valid until its
  `not_after` (≤30 days). Mitigate with short leases and renewal-based
  revocation.
- **Machine fingerprinting is coarse.** Hardware changes, Windows updates, or
  VM clones may change the fingerprint. The design uses a coarse composite
  hash and an activation limit (default 2) rather than strict binding.
- **The reset key is single-use and short-lived** (default 60 minutes). It
  clears the attempt counter only; it does not grant entitlement.

## Build

- The desktop EXE (`02_build\SnaglistPro.exe`) was built with PyInstaller from
  `app_launcher.py`. Rebuild with:
  `python -m PyInstaller --onefile --noconsole --name SnaglistPro app_launcher.py`
- The Android build uses Buildozer; see `SnaglistProMobile.spec`.

## Testing

- `test_summary_sheet_open_closed_counts_reflect_actual_data` fails due to a
  Hugging Face model download. It is pre-existing and unrelated to any change.
  Run the rest of the suite with `python -m pytest tests/ -q`.