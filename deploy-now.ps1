# Snaglist Pro - Heroku Deployment
# Uses full path to Heroku CLI

$heroku = "C:\Program Files\heroku\bin\heroku.cmd"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SNAGLIST PRO - HEROKU DEPLOYMENT" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $heroku)) {
    Write-Host "ERROR: Heroku CLI not found" -ForegroundColor Red
    exit 1
}

Write-Host "OK: Found Heroku CLI" -ForegroundColor Green
Write-Host ""

# STEP 1: Login
Write-Host "STEP 1: Login to Heroku" -ForegroundColor Yellow
Read-Host "Press Enter to continue"
& $heroku login

# STEP 2: Create app
Write-Host ""
Write-Host "STEP 2: Creating app..." -ForegroundColor Yellow
& $heroku create snaglist-vineeth --region us

# Credentials come from the environment (or a local .env) and are never stored
# in this file. Set SNAGLIST_APP_USERNAME / SNAGLIST_APP_PASSWORD before running.
$username = $env:SNAGLIST_APP_USERNAME
$password = $env:SNAGLIST_APP_PASSWORD
if ([string]::IsNullOrWhiteSpace($username) -or [string]::IsNullOrWhiteSpace($password)) {
    Write-Host "SNAGLIST_APP_USERNAME / SNAGLIST_APP_PASSWORD are not set." -ForegroundColor Red
    Write-Host "Set them in your shell or in a .env file (git-ignored)." -ForegroundColor Red
    exit 1
}

# STEP 3: Set credentials
Write-Host ""
Write-Host "STEP 3: Setting credentials..." -ForegroundColor Yellow
& $heroku config:set "SNAGLIST_APP_USERNAME=$username" "SNAGLIST_APP_PASSWORD=$password" -a snaglist-vineeth

# STEP 4: Login to Docker
Write-Host ""
Write-Host "STEP 4: Login to Docker registry..." -ForegroundColor Yellow
& $heroku container:login

# STEP 5: Push image
Write-Host ""
Write-Host "STEP 5: Pushing Docker image (5-10 minutes)..." -ForegroundColor Yellow
& $heroku container:push web -a snaglist-vineeth

# STEP 6: Release
Write-Host ""
Write-Host "STEP 6: Releasing..." -ForegroundColor Yellow
& $heroku container:release web -a snaglist-vineeth

# STEP 7: Logs
Write-Host ""
Write-Host "STEP 7: Checking status..." -ForegroundColor Yellow
& $heroku logs --tail -n 50 -a snaglist-vineeth

# DONE
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "SUCCESS!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "App URL:" -ForegroundColor Cyan
Write-Host "https://snaglist-vineeth.herokuapp.com" -ForegroundColor Cyan
Write-Host ""
Write-Host "Login:" -ForegroundColor Yellow
Write-Host "Username: $username" -ForegroundColor Gray
Write-Host "Password: (the value of SNAGLIST_APP_PASSWORD - not echoed)" -ForegroundColor Gray
Write-Host ""
