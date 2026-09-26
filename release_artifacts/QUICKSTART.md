# Snaglist Pro — Quick Start (5 minutes)

## 1. Install

Download **SnaglistPro-2.0.1-Installer.exe** and run it. Done!

Shortcuts are created in Start Menu and Desktop.

## 2. First Run

Click **Snaglist Pro** from the Start Menu.

If prompted for credentials (admin password), enter `admin` / `password` (or what your IT team gave you).

## 3. Generate a Report (30 seconds)

1. Click **Select ZIP** → choose a WhatsApp chat export
2. Click **Select Checklist** → choose an Excel checklist file
3. Click **Generate** → wait for processing
4. Click **Download** → save the output Excel

That's it! Open the Excel file to view the snaglist report.

## What You'll See

The Excel output has:

| Column | What it contains |
|--------|-----------------|
| Slno | Item number |
| Facility/Client | Project details |
| Floor | Floor/level |
| Area/Location | Auto-detected location |
| Category | Item type (Electrical, HVAC, etc.) |
| Check Points | From the checklist |
| Status | Open/Closed (detected from chat) |
| Snag Points | Description from chat |
| Priority | High/Medium/Low (auto-detected) |
| Ref. Images | Embedded photos from chat |
| Vendor | Assigned contractor |
| SPOC | Contact person |
| ... + 6 more columns | ... |

**Plus:** A Summary sheet with counts, percentages, and match statistics.

## Using Sample Data

Included with the installer:

- **ZIP:** `%LOCALAPPDATA%\SnaglistPro\samples\sample_chat.zip`
- **Checklist:** `%LOCALAPPDATA%\SnaglistPro\samples\checklist.xlsx`

Use these to test before running on real data.

## Configuring Vendors & Categories

Edit `%LOCALAPPDATA%\SnaglistPro\config.yaml`:

```yaml
vendor_overrides:
  Electrical: "MD Electrical"
  Hvac: "IND Aircon"
  Fire Safety: "V3 automation"
```

Restart the app for changes to take effect.

## AI Features (Optional)

To enable semantic matching and auto-correction:

1. Download Ollama: https://ollama.ai
2. Run: `ollama serve`
3. Run setup: `python C:\path\to\ollama_helper.py`
4. Select default model (e.g., `llama3.2`)

Now the app will use AI to:
- Match checklist items more accurately
- Auto-correct typos and spelling
- Better category/area detection

(The app works without Ollama too — just uses simpler matching.)

## Where is My Data?

Everything is stored in:

```
C:\Users\<YourUsername>\AppData\Local\SnaglistPro\
├── exports/           # Generated reports
├── license/           # License tokens (if you have a paid license)
├── database/          # SQLite database (optional persistence)
└── config.yaml        # Your custom configuration
```

## Troubleshooting

**"App won't start"**
- Check `%LOCALAPPDATA%\SnaglistPro\snaglist_error.log` for errors
- Reinstall if needed

**"No images in the report"**
- Make sure the WhatsApp ZIP contains images
- Check that original chat had media

**"Checklist items not matching"**
- Review the checklist format (should have a header row)
- Adjust keywords in `config.yaml` if categories are wrong

**"AI is slow / not working"**
- Make sure Ollama is running: `ollama serve`
- Check OLLAMA_URL env var is set correctly
- Run `python ollama_helper.py test` to diagnose

## Next Steps

- Read `ENV_VARS.md` to customize via environment variables
- Read `LICENSE_GUIDE.md` if you have a license
- See `INSTALL.md` for full installation options (silent, portable, etc.)

---

**Need help?** Contact support@snaglist.pro
