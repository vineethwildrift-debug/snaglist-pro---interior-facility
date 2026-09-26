# Snaglist Pro — License Guide (Paid Entitlement)

Snaglist Pro supports an optional paid entitlement using **Option A**: an
offline-verifiable, Ed25519-signed license token. The client ships with the
owner's **public** key only; the private key stays on the owner's machine and
is used solely by the issuer CLI. A token is a signed JSON envelope, so it
cannot be forged without the private key.

## Architecture

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

## Step 1 — Generate a keypair (owner)

```powershell
cd 01_source
python -m snaglist_pro.licensing gen-keypair `
    --private license.priv --public license.pub
```

This writes two PEM files:

| File | Contents | Where it goes |
|------|----------|---------------|
| `license.priv` | PKCS#8 private key | **Owner's machine only. Never ships.** |
| `license.pub` | SubjectPublicKeyInfo public key | Ships with the client (see step 4) |

The private key is `chmod 0600` on non-Windows. Store it safely — anyone with
it can mint valid tokens. The fingerprint printed at the end is a short
identifier for the keypair.

## Step 2 — Issue a license token (owner)

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

## Step 3 — Deliver the token to the customer

Send the `.lic` file to the customer. It is a plain JSON envelope; it contains
no secrets — only the signed payload and the Ed25519 signature. A leaked
token is valid until its `not_after`, and can be revoked only by issuing a
new token (short leases limit the blast radius).

## Step 4 — Install the public key and token on the customer's machine

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

## Step 5 — Verify a token without installing it

```powershell
$env:SNAGLIST_LICENSE_PUBLIC_KEY = "C:\path\to\license.pub"
python -m snaglist_pro.licensing verify LIC-001.lic
```

Prints the decoded payload (license id, edition, features, expiry).

## Renewal and revocation

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

## Programmatic use

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

## Environment variables

| Variable | Purpose |
|----------|---------|
| `SNAGLIST_LICENSE_DIR` | State directory (token, watermark, attempts) |
| `SNAGLIST_LICENSE_PUBLIC_KEY` | Path to the owner's public key |
| `SNAGLIST_LICENSE_PRIVATE_KEY` | Path to the owner's private key (issuer only) |