# Mobile Stable Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stable mobile-first Flask app that reuses the desktop export logic and produces validated workbook output from ZIP + checklist uploads.

**Architecture:** The mobile app will be a lightweight Python Flask server with a responsive interface and a stable backend that wraps the proven export helpers. It will validate the workbook before download, keep the same spelling-correction rules, and avoid the legacy path that caused workbook drift.

**Tech Stack:** Python 3.10+, Flask, openpyxl, Pillow, pytest

**Spec:** docs/superpowers/specs/2026-09-20-mobile-stable-design.md

## Global Constraints
- Python project already depends on Flask and openpyxl.
- The app must re-use the validated desktop flow instead of introducing a new export engine.
- The workbook must contain a valid data sheet and Summary sheet before download.
- Spelling correction remains optional and safe.

## Review Focus
- Upload validation for missing ZIP/checklist files
- Output workbook contains Summary and data sheet
- Mobile browser requests can generate workbook using standard form-data uploads
- Correction toggle does not rewrite technical terms

---

### Task 1: Write the failing mobile export tests

**Files:**
- Create: `tests/test_mobile_app.py`

**Interfaces:**
- Consumes: temporary ZIP and checklist files created in tests
- Produces: calls to `generate_report_from_uploads()` or app test client

- [ ] **Step 1: Write the failing test**

```python
def test_mobile_app_index_page_loads():
    app = create_mobile_app()
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200


def test_mobile_app_generates_valid_workbook():
    zip_path = Path('tmp_mobile.zip')
    checklist_path = Path('tmp_mobile_checklist.csv')
    output = generate_report_from_uploads(str(zip_path), str(checklist_path))
    assert Path(output).exists()
    wb = load_workbook(output)
    assert 'Summary' in wb.sheetnames
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mobile_app.py -q`
Expected: FAIL with "module not found" or missing function

- [ ] **Step 3: Implement minimal app scaffolding**

- [ ] **Step 4: Run tests to verify they pass**

### Task 2: Build the mobile-first Flask app

**Files:**
- Create: `mobile_app.py`
- Modify: `pyproject.toml` if needed for app metadata only

**Interfaces:**
- Exposes: `create_mobile_app()` and `generate_report_from_uploads(...)`
- Consumes: ZIP path and checklist file path
- Produces: workbook file path

- [ ] **Step 1: Create Flask app with mobile layout and upload form**
- [ ] **Step 2: Re-use the stable export helpers from the desktop flow**
- [ ] **Step 3: Validate workbook before returning the output**
- [ ] **Step 4: Verify index page and generation endpoint**

### Task 3: Verify stable behavior and shipping path

**Files:**
- Test: `tests/test_mobile_app.py`

**Interfaces:**
- Consumes: stable workbook creation from ZIP and checklist
- Produces: evidence for a released mobile-first build

- [ ] **Step 1: Run focused mobile tests**
- [ ] **Step 2: Confirm app starts and index route responds**
- [ ] **Step 3: Prepare final notes for the user**
