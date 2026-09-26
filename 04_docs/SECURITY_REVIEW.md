# Snaglist Pro — Security Review (Entitlement Design)

This document reviews the paid-entitlement design implemented in
`snaglist_pro/licensing.py` (Option A) and the authentication hardening in
`snaglist_pro/auth.py`. It is intended for stakeholders who need to understand
what the system protects against, and what it does not.

## Threat model

The application runs on customer-owned machines at construction sites, where
connectivity is intermittent and the operator has full local access. The
design targets:

- **Casual sharing / unpaid use** — a customer who forwards the app to
  colleagues or runs it beyond their paid period.
- **Credential tampering** — editing local auth state to stay logged in or
  to bypass the license check.
- **Clock manipulation** — rolling the system clock back to keep a license
  "alive" past expiry.

It does **not** target a determined, resourceful attacker with root access to
the binary. Client-side enforcement is a speed bump, not a cryptographic
boundary; a signed token raises the cost of forgery to "requires the owner's
private key" but cannot prevent patching the client itself.

## What the system does

### Entitlement (licensing.py)

- License tokens are **Ed25519-signed JSON envelopes**. The client verifies the
  signature against an embedded public key. Without the private key, a token
  cannot be forged.
- The payload carries `license_id`, `customer`, `edition`, `features`,
  `not_before`, `not_after`, `machine_hash`, and `max_activations`.
- State (token, watermark, attempts, activation list) is stored in the **OS
  credential store** (DPAPI on Windows), which is bound to the user's logon
  credentials and adds a MAC for tamper detection.
- A **monotonic watermark** defends against wall-clock rollback; forward drift
  is tolerated up to the offline grace window.
- An **offline grace window** (7 days) keeps paying users working during
  outages before generation is locked.
- **Enforcement gates new report generation only** — reading or exporting
  already-produced data is never blocked, so a lapsed license cannot destroy
  or lock existing work.
- **Exponential lockout** (30s → 15min cap) after repeated failed checks,
  with an owner-issued single-use reset key to clear a hard lockout.
- **Activation limit** per license (default 2 machines); re-installing the
  same token on an already-activated machine is idempotent.

### Authentication (auth.py)

- Passwords are hashed with **PBKDF2-HMAC-SHA256 at 600,000 iterations**
  (OWASP minimum; Argon2id is preferred but kept optional).
- The **session file is HMAC-signed** using `get_or_create_secret()`, so
  `last_activity` cannot be edited to keep a session alive.
- `password_change_required` lives in `auth.json`, not the ephemeral session
  file, so it survives the 30-minute idle timeout.
- **Account-keyed exponential lockout** on `verify_credentials()`.

## Known limitations

| Limitation | Consequence |
|-----------|-------------|
| Local-only enforcement | A determined user can patch the binary, delete the state, or restore a snapshot. This is inherent to client-side licensing. |
| 4-digit PIN is not the gate | A 4-digit PIN has 10,000 possibilities and is crackable in seconds–minutes offline. It is suitable only as a convenience screen lock, never as the revenue gate. |
| No instant offline revocation | Revocation takes effect at the next lease renewal (≤30 days). A leaked token is valid until `not_after`. |
| Clock trust is limited, not eliminated | The watermark stops simple rollback; it does not stop a user who can set the BIOS clock. |
| Machine fingerprinting is coarse | Over-binding causes legitimate lockouts after hardware/VM changes; the design uses a coarse composite hash and an activation limit instead. |

## Standards referenced

- OWASP Password Storage Cheat Sheet (Argon2id preferred; PBKDF2 600k as
  FIPS fallback; unique salt; constant-time compare)
- OWASP Authentication Cheat Sheet (re-auth triggers; account-keyed
  exponential lockout; avoid periodic credential rotation; generic errors)
- OWASP Key Management Cheat Sheet (full key lifecycle; never store keys
  plaintext; one key per purpose; compromise-recovery plan)
- Microsoft DPAPI (`CryptProtectData`) for OS-bound authenticated encryption
- NIST SP 800-63B (no composition rules; no forced periodic rotation; use
  length + breached-password blocklist)

## Testing

See `04_docs/CHANGELOG.md` for the full test summary. The licensing module has
16 tests covering: keypair generation, token issuance, signature tamper
rejection, wrong-key rejection, entitlement states (unlicensed/active/expired/
grace/tampered), clock-rollback defense, exponential lockout with reset-key
recovery, activation limits, and the CLI. The auth module has 8 tests covering
hashing round-trips, `password_change_required` persistence, session HMAC
tamper detection, and lockout behavior.