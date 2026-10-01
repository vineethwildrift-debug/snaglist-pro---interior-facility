# Mobile Stable Build Design

> Goal: convert the verified desktop export flow into a stable mobile-first application that preserves the same workbook quality checks, spelling correction controls, and export reliability on a simpler platform.

## Outcome
The app should let a user upload a WhatsApp ZIP export and a checklist from a phone or tablet browser, validate the workbook before saving, and produce a downloadable Excel file that matches the verified desktop output quality.

## Constraints
- Use the validated export rules already proven by the desktop app.
- No silent fallback to a legacy workbook path.
- Preserve technical terms and log spelling corrections.
- Support uploading from mobile browsers without requiring a full native SDK build in this environment.
- Keep the app simple, testable, and deployable from the same Python project.

## Architecture
A Flask-based mobile-first web app will serve a lightweight HTML interface and handle file uploads. It will call the same parsing and export helpers used by the desktop flow, then write an Excel workbook with a data sheet and Summary sheet and validate its structure before returning the file.

## Acceptance Criteria
- A mobile browser can upload a ZIP and checklist file.
- The app creates a stable workbook with at least a Summary sheet and a data sheet.
- The app validates the workbook before download.
- Common report typos are corrected only when enabled.
- The app returns a clear error message if inputs are missing or invalid.

## Non-goals
- Full native Android/iOS packaging in this session.
- Cross-device push notifications or cloud sync.
- Advanced login systems or multi-user admin features.

## Risks and mitigations
- Risk: mobile browser uploads are inconsistent across devices. Mitigation: accept standard file uploads and keep the UI minimal.
- Risk: workbook validation may block valid exports. Mitigation: validate only the required stable sheets and data presence.
- Risk: typo correction could rewrite technical names. Mitigation: limit corrections to the known safe spelling dictionary and keep the toggle optional.
