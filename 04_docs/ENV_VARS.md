# Snaglist Pro — Environment Variables

All configuration can be overridden via environment variables using the
`SNAGLIST__` prefix, matching the dotted path in `config.yaml`. For example,
`project.default_client` becomes `SNAGLIST__PROJECT__DEFAULT_CLIENT`.

## Application

| Variable | Purpose | Default |
|----------|---------|---------|
| `SNAGLIST__PROJECT__DEFAULT_CLIENT` | Default client name | `""` |
| `SNAGLIST__PROJECT__DEFAULT_FACILITY` | Default facility name | `""` |
| `SNAGLIST__PROJECT__DEFAULT_FLOOR` | Default floor | `""` |
| `SNAGLIST__PROJECT__DEFAULT_PRIORITY` | Default priority | `Medium` |
| `SNAGLIST__PROJECT__DEFAULT_STATUS` | Default status | `Open` |
| `SNAGLIST__PROJECT__OUTPUT_DIR` | Output directory | `""` |
| `SNAGLIST__DATABASE__URL` | Database URL | SQLite in AppData |
| `SNAGLIST__IMAGES__RESIZE_SIZE` | Image resize dimension | `200` |
| `SNAGLIST__IMAGES__QUALITY` | Image JPEG quality | `90` |

## AI

| Variable | Purpose | Default |
|----------|---------|---------|
| `AI_ENABLED` | Enable AI features | `true` |
| `AI_PROVIDER` | AI provider | `ollama` |
| `OLLAMA_URL` | Ollama endpoint | `http://localhost:11434` |
| `OLLAMA_TEXT_MODEL` | Text model | `llama3.2` |
| `AI_REQUEST_TIMEOUT` | Request timeout (s) | `120` |
| `MAX_AI_CALLS_PER_RUN` | Max AI calls per run | `1000` |

## Notifications

| Variable | Purpose | Default |
|----------|---------|---------|
| `SMTP_HOST` | SMTP server | `""` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | SMTP username | `""` |
| `SMTP_PASS` | SMTP password | `""` |
| `NOTIFY_EMAIL` | Notification recipient | `""` |

## Authentication

| Variable | Purpose | Default |
|----------|---------|---------|
| `SNAGLIST_APP_USERNAME` | Login username | `""` |
| `SNAGLIST_APP_PASSWORD` | Login password | `""` |
| `SNAGLIST_SECRET` | HMAC key for session signing | generated on first use |
| `SNAGLIST_PASSWORD_ITERATIONS` | PBKDF2 iteration count | `600000` |

## Licensing (paid entitlement)

| Variable | Purpose | Default |
|----------|---------|---------|
| `SNAGLIST_LICENSE_DIR` | State directory (token, watermark, attempts) | AppData\SnaglistPro\license |
| `SNAGLIST_LICENSE_PUBLIC_KEY` | Path to the owner's public key | `snaglist_pro/license.pub` |
| `SNAGLIST_LICENSE_PRIVATE_KEY` | Path to the owner's private key (issuer only) | `snaglist_pro/license.priv` |

## Notes

- On Windows, `LOCALAPPDATA` is used as the base for app data and license
  state. Override it to redirect storage.
- The license state directory is isolated per-machine via the OS credential
  store; do not copy it between machines, as the machine fingerprint will not
  match.