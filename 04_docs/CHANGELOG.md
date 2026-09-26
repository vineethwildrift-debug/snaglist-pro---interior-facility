# Snaglist Pro — Changelog

## v2.0.1 (2026-09-25) — Current

### Added
- **Licensing module** (`snaglist_pro/licensing.py`) — Option A paid
  entitlement: offline-verifiable, Ed25519-signed license tokens with
  machine binding, clock-rollback defense, offline grace window, exponential
  lockout, and an owner CLI (`gen-keypair`, `issue`, `reset-key`, `verify`).
- **Opt-in license gate** on `SnaglistPipeline.run(license_check=True)`.
- **Licensing configuration** in `config.yaml` (`licensing:` block).
- **Licensing documentation** (`04_docs/LICENSE_GUIDE.md`).
- **Test suites**: `tests/test_licensing.py` (16 tests) and
  `tests/test_auth_security.py` (8 tests).

### Fixed
- `_PASSWORD_ITERATIONS` was referenced in `auth.py` but never defined, causing
  a `NameError` on every `hash_password()` call (including the environment
  credential login path). Now defined as 600,000 (OWASP minimum for
  PBKDF2-HMAC-SHA256), overridable via `SNAGLIST_PASSWORD_ITERATIONS`.
- The session file was plaintext JSON with only `last_activity`, so it could
  be edited to keep a session alive. It is now HMAC-signed using
  `get_or_create_secret()` (previously generated but never used).
- `password_change_required` was stored in the ephemeral session file, which
  is deleted after the 30-minute idle timeout, forcing a password change after
  every idle period. It now lives in `auth.json`.
- Added account-keyed exponential lockout to `verify_credentials()`.

### Security hardening
- Session integrity via HMAC.
- Password-change state moved out of the session file.
- Login throttling with exponential backoff and owner reset key.

## v2.0.0 (2026-09-21)
- Desktop-first release flow; app data stored in Local AppData.
- 11 pipeline bug fixes from the QA audit (status logic, system-message
  filtering, category keywords, date/area columns, Match Rate formula, sheet
  naming, vendor overrides, SPOC columns, test updates).

## Earlier
- WhatsApp parsing, checklist matching, Excel export, summary dashboard,
  database persistence, and batch processing.

## Test summary

- **119 of 120 tests pass.**
- The single failing test (`test_summary_sheet_open_closed_counts_reflect_actual_data`)
  is pre-existing and network-dependent (Hugging Face model download); it is
  unrelated to any change in this release.