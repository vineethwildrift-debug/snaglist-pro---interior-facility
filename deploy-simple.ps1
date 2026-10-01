# Snaglist Pro - Heroku Deployment (SIMPLE VERSION)
# Run this step by step in PowerShell

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "SNAGLIST PRO - HEROKU DEPLOYMENT" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# STEP 1: Login
Write-Host "STEP 1: Login to Heroku" -ForegroundColor Yellow
Write-Host "A browser will open. Login with your Heroku account." -ForegroundColor Gray
Write-Host ""
Read-Host "Press Enter when ready, then login in the browser"

heroku login

# STEP 2: Create app
Write-Host ""
Write-Host "STEP 2: Creating Heroku app..." -ForegroundColor Yellow
heroku create snaglist-vineeth --region us

# Credentials come from the environment (or a local .env) and are never stored
# in this file. Set SNAGLIST_APP_USERNAME / SNAGLIST_APP_PASSWORD before running.
$username = $env:SNAGLIST_APP_USERNAME
$password = $env:SNAGLIST_APP_PASSWORD
if ([string]::IsNullOrWhiteSpace($username) -or [string]::IsNullOrWhiteSpace($password)) {
    Write-Host "SNAGLIST_APP_USERNAME / SNAGLIST_APP_PASSWORD are not set." -ForegroundColor Red
    Write-Host "Set them in your shell or in a .env file (git-ignored)." -ForegroundColor Red
    exit 1
}

# STEP 3: Set environment variables
Write-Host ""
Write-Host "STEP 3: Setting credentials..." -ForegroundColor Yellow
heroku config:set "SNAGLIST_APP_USERNAME=$username" "SNAGLIST_APP_PASSWORD=$password" -a snaglist-vineeth

# STEP 4: Login to container registry
Write-Host ""
Write-Host "STEP 4: Login to Heroku container registry..." -ForegroundColor Yellow
heroku container:login

# STEP 5: Push Docker image
Write-Host ""
Write-Host "STEP 5: Pushing Docker image (this takes 5-10 minutes)..." -ForegroundColor Yellow
heroku container:push web -a snaglist-vineeth

# STEP 6: Release
Write-Host ""
Write-Host "STEP 6: Releasing app..." -ForegroundColor Yellow
heroku container:release web -a snaglist-vineeth

# STEP 7: Check status
Write-Host ""
Write-Host "STEP 7: Checking deployment status..." -ForegroundColor Yellow
heroku logs --tail -n 100 -a snaglist-vineeth

# DONE
Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 YOUR APP IS LIVE AT:" -ForegroundColor Cyan
Write-Host "   https://snaglist-vineeth.herokuapp.com" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 LOGIN WITH:" -ForegroundColor Yellow
Write-Host "   Username: $username" -ForegroundColor Gray
Write-Host "   Password: (the value of SNAGLIST_APP_PASSWORD - not echoed)" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ NEXT: Open the link above in your browser!" -ForegroundColor Green
