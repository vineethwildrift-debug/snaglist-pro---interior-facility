# Snaglist Pro - Docker Containerization Guide

## 📦 What's Included

✅ **Dockerfile** - Multi-stage build, Python 3.10 slim, ~280MB optimized image  
✅ **docker-compose.yml** - Local dev: Flask web + optional CLI  
✅ **.dockerignore** - Excludes build artifacts  
✅ **requirements-prod.txt** - Minimal production dependencies  

---

## 🏠 Local Development (5 min)

### Prerequisites
- Docker Desktop installed & running
- Git (optional)

### Build & Run

```bash
# Navigate to project
cd C:\Users\vinee\snaglist_pro

# Build image (first time, ~3-5 min)
docker build -t snaglist-pro:2.0.1 .

# Run with docker-compose (easier)
docker compose up -d

# Or run directly
docker run -d -p 5000:5000 \
  --name snaglist-web \
  -e SNAGLIST_APP_USERNAME=admin \
  -e SNAGLIST_APP_PASSWORD=changeme123 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/output:/app/output \
  snaglist-pro:2.0.1
```

### Access Web UI
- **URL**: http://localhost:5000
- **Username**: admin
- **Password**: changeme123

### View Logs
```bash
docker logs -f snaglist-web
# or
docker compose logs -f snaglist-web
```

### Stop Container
```bash
docker compose down
# or
docker stop snaglist-web
```

---

## 🐳 Docker Commands Reference

### Build
```bash
# Build with tag
docker build -t snaglist-pro:2.0.1 .

# Build without cache (force rebuild)
docker build --no-cache -t snaglist-pro:2.0.1 .
```

### Run Web Service
```bash
# Foreground (see logs live)
docker run -p 5000:5000 \
  -e SNAGLIST_APP_USERNAME=admin \
  -e SNAGLIST_APP_PASSWORD=yourpassword \
  snaglist-pro:2.0.1

# Background
docker run -d -p 5000:5000 \
  --name snaglist-web \
  snaglist-pro:2.0.1

# With persistent volumes
docker run -d -p 5000:5000 \
  -v ./uploads:/app/uploads \
  -v ./output:/app/output \
  snaglist-pro:2.0.1
```

### Run CLI (Batch Processing)
```bash
docker run --rm \
  -v /path/to/chat.zip:/app/uploads/chat.zip \
  -v /path/to/checklist.xlsx:/app/uploads/checklist.xlsx \
  -v $(pwd)/output:/app/output \
  snaglist-pro:2.0.1 \
  snaglist_pro --zip /app/uploads/chat.zip \
               --checklist /app/uploads/checklist.xlsx \
               --output /app/output --project "My Project"
```

### Docker Compose
```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f snaglist-web

# Run CLI worker
docker compose --profile cli up snaglist-cli
```

### Useful Commands
```bash
# List running containers
docker ps

# View container logs
docker logs snaglist-web

# Check container resource usage
docker stats snaglist-web

# Execute command in running container
docker exec -it snaglist-web bash

# Remove container
docker rm snaglist-web

# Remove image
docker rmi snaglist-pro:2.0.1
```

---

## 📤 Push to Docker Hub

```bash
# Create Docker Hub account: https://hub.docker.com

# Login
docker login

# Tag image
docker tag snaglist-pro:2.0.1 yourusername/snaglist-pro:2.0.1

# Push
docker push yourusername/snaglist-pro:2.0.1

# Pull from anywhere
docker run -p 5000:5000 yourusername/snaglist-pro:2.0.1
```

---

## ☁️ Deployment Options

| Platform | Cost | Setup | Always-On | Best For |
|----------|------|-------|-----------|----------|
| **Heroku** | Free/7/50USD | 10 min | No (sleeps) | Quick demos |
| **Google Cloud Run** | Free tier | 15 min | No (scales to zero) | Cheap, serverless |
| **AWS EC2** | $0-12/mo | 30 min | Yes | High traffic |
| **Render** | Free/7/25USD | 10 min | Yes (free tier) | Simple apps |
| **Your Linux Server** | $5-50/mo | 30 min | Yes | Full control |

---

## 🚀 Deploy to Heroku (FREE - Recommended)

### Step 1: Create Heroku Account
- Go to https://signup.heroku.com (free)

### Step 2: Install Heroku CLI
```bash
# macOS/Linux
brew tap heroku/brew && brew install heroku

# Windows
choco install heroku-cli
# Or download: https://devcenter.heroku.com/articles/heroku-cli
```

### Step 3: Deploy
```bash
# Login
heroku login

# Create app
heroku create snaglist-pro-YOUR-NAME

# Set credentials
heroku config:set \
  SNAGLIST_APP_USERNAME=admin \
  SNAGLIST_APP_PASSWORD=your-secure-password \
  -a snaglist-pro-YOUR-NAME

# Enable container registry
heroku container:login

# Build and push
heroku container:push web -a snaglist-pro-YOUR-NAME

# Release
heroku container:release web -a snaglist-pro-YOUR-NAME

# Open app
heroku open -a snaglist-pro-YOUR-NAME
```

**Done!** Your app is live at `https://snaglist-pro-YOUR-NAME.herokuapp.com`

---

## 📊 Image Specs

| Metric | Value |
|--------|-------|
| Base Image | python:3.10-slim (Debian) |
| Final Size | ~280MB |
| Startup | ~3-5 seconds |
| Memory Idle | ~150MB |
| Memory Peak | ~400MB |

---

## 🔐 Security

### Environment Variables (Never Hardcode)
```bash
# Set via CLI
docker run -e SNAGLIST_APP_USERNAME=admin \
           -e SNAGLIST_APP_PASSWORD=secure-password \
           snaglist-pro:2.0.1

# Or .env file (local only)
SNAGLIST_APP_USERNAME=admin
SNAGLIST_APP_PASSWORD=secure-password

# Load from file
docker run --env-file .env snaglist-pro:2.0.1
```

### Licensing
- Public key stays in image ✓
- Private key **NEVER** in image ✗
- Tokens verified at runtime ✓

---

## 📝 Troubleshooting

### "Port already in use"
```bash
docker ps  # Find container using port 5000
docker stop <container-id>
```

### "Cannot connect to localhost:5000"
- Check container is running: `docker ps`
- Check logs: `docker logs snaglist-web`
- Try: `curl http://localhost:5000`

### "Permission denied"
- Use `sudo docker` on Linux
- Or: `docker run --user=root ...`

### Out of memory
```bash
# Allocate more memory
docker run -m 2gb snaglist-pro:2.0.1
```

### Build takes too long
- Comment out sentence-transformers in requirements-prod.txt
- Use: `docker build --no-cache -t snaglist-pro:2.0.1 .`

---

## 📈 Monitoring

### Local
```bash
# Logs
docker logs -f snaglist-web

# Stats
docker stats snaglist-web

# Health
curl http://localhost:5000/
```

### Heroku
```bash
# Logs
heroku logs --tail -a snaglist-pro-YOUR-NAME

# Dyno status
heroku ps -a snaglist-pro-YOUR-NAME
```

---

## ✅ Testing Checklist

- [ ] Build completes: `docker build -t snaglist-pro:2.0.1 .`
- [ ] Container runs: `docker run -p 5000:5000 snaglist-pro:2.0.1`
- [ ] Web UI accessible: http://localhost:5000
- [ ] Login works with credentials
- [ ] Can upload ZIP + checklist
- [ ] Generate button works
- [ ] Can download Excel output
- [ ] CLI works: `docker run ... snaglist_pro --zip ... --checklist ... --output ...`

---

**Next: Deploy to Heroku following the "Deploy to Heroku" section above!**
