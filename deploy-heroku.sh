#!/bin/bash
# Snaglist Pro - Heroku Deployment Script
# Run this after Docker build completes

APP_NAME="snaglist-vineeth"
REGION="us"

echo "🚀 Snaglist Pro - Heroku Deployment Setup"
echo "=========================================="
echo ""

# Step 1: Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI not found. Install it:"
    echo "   macOS: brew tap heroku/brew && brew install heroku"
    echo "   Windows: https://devcenter.heroku.com/articles/heroku-cli"
    echo "   Linux: curl https://cli-assets.heroku.com/install.sh | sh"
    exit 1
fi

# Step 2: Login to Heroku
echo "📝 Login to Heroku..."
heroku login

# Step 3: Create Heroku app
echo ""
echo "🔧 Creating Heroku app: $APP_NAME"
heroku create $APP_NAME --region $REGION || echo "App might already exist"

# Step 4: Set environment variables
echo ""
echo "Setting credentials..."
: "${SNAGLIST_APP_USERNAME:?SNAGLIST_APP_USERNAME is not set - export it before running}"
: "${SNAGLIST_APP_PASSWORD:?SNAGLIST_APP_PASSWORD is not set - export it before running}"
heroku config:set \
  SNAGLIST_APP_USERNAME="$SNAGLIST_APP_USERNAME" \
  SNAGLIST_APP_PASSWORD="$SNAGLIST_APP_PASSWORD" \
  -a $APP_NAME

# Step 5: Verify credentials set
echo ""
echo "✅ Configuration:"
heroku config -a $APP_NAME

# Step 6: Deploy container
echo ""
echo "📦 Deploying Docker image to Heroku..."
heroku container:login
heroku container:push web -a $APP_NAME
heroku container:release web -a $APP_NAME

# Step 7: View logs
echo ""
echo "📋 Checking deployment status..."
heroku logs --tail -n 50 -a $APP_NAME

# Step 8: Open app
echo ""
echo "✅ Deployment complete!"
echo "🌐 Your app is live at:"
echo "   https://$APP_NAME.herokuapp.com"
echo ""
echo "📝 Credentials:"
echo "   Username: $SNAGLIST_APP_USERNAME"
echo "   Password: (the value of SNAGLIST_APP_PASSWORD - not echoed)"
echo ""
echo "💡 Next steps:"
echo "   1. Visit https://$APP_NAME.herokuapp.com"
echo "   2. Login with credentials above"
echo "   3. Upload WhatsApp ZIP + checklist"
echo "   4. Generate and download Excel"
echo ""
echo "📊 Monitor in real-time:"
echo "   heroku logs --tail -a $APP_NAME"
echo ""
echo "🔧 View all apps:"
echo "   heroku apps"
