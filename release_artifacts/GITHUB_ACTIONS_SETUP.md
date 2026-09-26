# GitHub Actions Release Workflow Setup

To enable automated releases:

## 1. Create GitHub Workflows Directory

```powershell
mkdir .github\workflows -Force
Copy-Item ".github_workflows_release.yml" -Destination ".github\workflows\release.yml"
git add .github/
git commit -m "Add GitHub Actions release workflow"
git push
```

## 2. Configure GitHub Secrets (Optional)

In your GitHub repository settings → Secrets and variables → Actions, add:

| Secret | Value |
|--------|-------|
| `CODESIGN_CERT` | Base64-encoded PFX certificate (for code signing) |
| `CODESIGN_PASSWORD` | Password for the PFX certificate |
| `SLACK_WEBHOOK_URL` | Slack webhook URL for notifications |
| `CDN_ACCESS_KEY` | CDN credentials (AWS S3, Azure, etc.) |

## 3. Manual Release Trigger

Go to GitHub → Actions → Release Snaglist Pro → Run workflow

Fill in:
- **Version:** 2.0.1
- **Channel:** stable (or beta/dev)

The workflow will:
1. ✓ Run all tests
2. ✓ Build EXE with PyInstaller
3. ✓ Create NSIS installer
4. ✓ Calculate SHA256 checksums
5. ✓ Code sign (if certificate provided)
6. ✓ Create GitHub Release
7. ✓ Upload artifacts
8. ✓ Update auto-update manifest
9. ✓ Notify Slack (if configured)
10. ✓ Run security scan

## 4. CDN Deployment

Update the "Update auto-update manifest on CDN" step to push to your CDN:

```yaml
- name: Update auto-update manifest on CDN
  run: |
    # AWS S3 example:
    aws s3 cp update-manifest-stable.json s3://my-releases-bucket/ --region us-east-1
    
    # Or Azure Blob Storage:
    az storage blob upload --file update-manifest-stable.json --container-name releases --name update-manifest-stable.json
```

## 5. Verify Release

After workflow completes:
- [ ] GitHub Release created: https://github.com/YOUR_REPO/releases
- [ ] All artifacts uploaded
- [ ] Auto-update manifest updated
- [ ] Slack notification sent (if configured)

## Scheduled Update Checks

To enable scheduled release checks (e.g., daily), add to `.github/workflows/release.yml`:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:
```

## Reverting a Release

If you need to revoke/rollback:

1. **Yank from GitHub:** Delete the GitHub Release (repo will show as "pre-release")
2. **Yank from CDN:** Delete update manifest from CDN
3. **Issue a patch:** Release a new version with fixes and mark old version as deprecated

---

**Next:** Push your repo to GitHub and enable Actions in settings.
