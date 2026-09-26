# Snaglist Pro — Quick Start

Run the pipeline on the included sample data in three commands.

## 1. Install dependencies

```powershell
cd 01_source
pip install -r requirements.txt
```

Or install the package directly:

```powershell
pip install -e .
```

## 2. Run on the sample data

```powershell
cd 01_source
python -m snaglist_pro `
    --zip "..\03_sample_data\inputs\test_upload.zip" `
    --checklist "..\03_sample_data\inputs\checklist.xlsx" `
    --output "..\03_sample_data\outputs"
```

This writes `..\03_sample_data\outputs\<project>.xlsx`. The same workbook is
also produced with a `_gs` suffix for Google Sheets compatibility when run
without `--fast-mode`.

## 3. Inspect the output

The generated workbook has two sheets:

- **`<project>`** — the 18-column snaglist with embedded images
- **`Summary`** — counts, percentages, and a Match Rate formula

Compare against the verified reference:

```powershell
# Expected: ..\03_sample_data\outputs\verified_output.xlsx
```

## Run the desktop GUI

```powershell
cd 02_build
SnaglistPro.exe
```

Or from source:

```powershell
cd 01_source
python desktop_app.py
```

## Run the web UI

```powershell
cd 01_source
python -m snaglist_pro --web
# then open http://127.0.0.1:5000
```

## Run the test suite

```powershell
cd 01_source
python -m pytest tests/ -q
```

## License check (optional)

If a paid license token is installed, gate report generation with:

```powershell
python -m snaglist_pro `
    --zip "..\03_sample_data\inputs\test_upload.zip" `
    --checklist "..\03_sample_data\inputs\checklist.xlsx" `
    --output "..\03_sample_data\outputs" `
    --license-check
```

See `LICENSE_GUIDE.md` for issuance and installation.