# Snaglist Pro - Heroku Deployment Script (PowerShell)
# Run this in PowerShell after Docker build completes

$appName = "snaglist-vineeth"
$region = "us"

# Credentials come from the environment (or a local .env) and are never stored
# in this file. Set SNAGLIST_APP_USERNAME / SNAGLIST_APP_PASSWORD before running.
$username = $env:SNAGLIST_APP_USERNAME
$password = $env:SNAGLIST_APP_PASSWORD
if ([string]::IsNullOrWhiteSpace($username) -or [string]::IsNullOrWhiteSpace($password)) {
    Write-Host "❌ SNAGLIST_APP_USERNAME / SNAGLIST_APP_PASSWORD are not set." -ForegroundColor Red
    Write-Host "   Set them in your shell or in a .env file (git-ignored)." -ForegroundColor Red
    exit 1
}

Write-Host "🚀 Snaglist Pro - Heroku Deployment Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Heroku CLI
Write-Host "📝 Checking Heroku CLI..." -ForegroundColor Yellow
if (-not (Get-Command heroku -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Heroku CLI not found. Install it:" -ForegroundColor Red
    Write-Host "   Windows: https://devcenter.heroku.com/articles/heroku-cli" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Heroku CLI found" -ForegroundColor Green

# Step 2: Login
Write-Host ""
Write-Host "📝 Login to Heroku (browser will open)..." -ForegroundColor Yellow
heroku login

# Step 3: Create app
Write-Host ""
Write-Host "🔧 Creating Heroku app: $appName" -ForegroundColor Yellow
heroku create $appName --region $region
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  App might already exist, continuing..." -ForegroundColor Yellow
}

# Step 4: Set credentials
Write-Host ""
Write-Host "🔐 Setting environment variables..." -ForegroundColor Yellow
heroku config:set `
  "SNAGLIST_APP_USERNAME=$username" `
  "SNAGLIST_APP_PASSWORD=$password" `
  -a $appName

# Step 5: Show config
Write-Host ""
Write-Host "✅ Current Configuration:" -ForegroundColor Green
heroku config -a $appName

# Step 6: Deploy
Write-Host ""
Write-Host "📦 Deploying Docker container..." -ForegroundColor Yellow
Write-Host "   This may take 5-10 minutes..." -ForegroundColor Gray

heroku container:login
heroku container:push web -a $appName
heroku container:release web -a $appName

# Step 7: Logs
Write-Host ""
Write-Host "📋 Checking deployment status..." -ForegroundColor Yellow
heroku logs --tail -n 50 -a $appName

# Step 8: Success
Write-Host ""
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Your app is live at:" -ForegroundColor Cyan
Write-Host "   https://$appName.herokuapp.com" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Login Credentials:" -ForegroundColor Yellow
Write-Host "   Username: $username" -ForegroundColor Gray
Write-Host "   Password: (the value of SNAGLIST_APP_PASSWORD - not echoed)" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Visit https://$appName.herokuapp.com in your browser" -ForegroundColor Gray
Write-Host "   2. Login with credentials above" -ForegroundColor Gray
Write-Host "   3. Upload WhatsApp ZIP + checklist Excel" -ForegroundColor Gray
Write-Host "   4. Click Generate → Download Excel" -ForegroundColor Gray
Write-Host ""
Write-Host "📊 Monitor in Real-Time:" -ForegroundColor Yellow
Write-Host "   heroku logs --tail -a $appName" -ForegroundColor Gray
Write-Host ""
