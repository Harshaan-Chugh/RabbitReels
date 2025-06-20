# 🔧 RabbitReels Troubleshooting Guide

## What Happened & How to Fix It

### ❌ **Issue 1: Docker Compose Volume Error**
**Problem:** `service volume services.api.volumes.[0] is missing a mount target`

**Solution:** ✅ **FIXED** - There was a malformed volume mount in docker-compose.yml
```yaml
# Before (broken):
volumes:
  - videos-data:/app/data/videos    restart: on-failure

# After (fixed):  
volumes:
  - videos-data:/app/data/videos
restart: on-failure
```

### ❌ **Issue 2: Uvicorn Command Not Found**
**Problem:** `uvicorn : The term 'uvicorn' is not recognized`

**Solution:** ✅ **FIXED** - Python dependencies weren't installed
- Created Python virtual environment
- Installed all API dependencies including uvicorn

### ❌ **Issue 3: Navigation Issues**
**Problem:** `cd web` from `api` directory didn't work

**Solution:** ✅ **FIXED** - Need to navigate correctly:
```powershell
# Wrong:
cd api
cd web  # ❌ There's no 'web' folder inside 'api'

# Right:
cd api      # Go to API directory
cd ..\web   # Go back and into web directory
```

## 🚀 **How to Start RabbitReels Now**

### **Option 1: Use the Setup Script (First Time)**
```powershell
# Run this once to set everything up
.\setup.ps1
```

### **Option 2: Use Quick Start (After Setup)**
```powershell
# Run this to start everything
.\quick-start.ps1
```

### **Option 3: Manual Steps**

#### 1. Start Infrastructure
```powershell
docker compose up -d rabbitmq redis
```

#### 2. Start API (New Terminal)
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Navigate to API directory
cd api

# Start API server
uvicorn main:app --reload
```

#### 3. Start Frontend (Another Terminal)
```powershell
# Navigate to web directory
cd web

# Start development server
npm run dev
```

### **Option 4: Full Docker Stack**
```powershell
# Start everything with Docker
docker compose up -d
```

## 🌐 **Access URLs**
- **Frontend**: http://localhost:3001
- **API**: http://localhost:8080
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **API Health**: http://localhost:8080/health
- **API Docs**: http://localhost:8080/docs

## 🧪 **Test Everything Works**

### Quick API Test:
```powershell
# Test themes endpoint
curl http://localhost:8080/themes

# Expected response: ["family_guy", "rick_and_morty"]
```

### Full Integration Test:
```powershell
# Run the comprehensive test
cd api
python test_api.py
```

## 💡 **Common PowerShell Issues**

### Use `;` instead of `&&` for command chaining:
```powershell
# Wrong:
cd api && uvicorn main:app --reload

# Right:
cd api; uvicorn main:app --reload
```

### Use `.\script.ps1` to run PowerShell scripts:
```powershell
# Run setup script
.\setup.ps1

# Run quick start
.\quick-start.ps1
```

## 🎯 **Next Steps**

1. ✅ Infrastructure is running (RabbitMQ + Redis)
2. 🔧 Run `.\setup.ps1` to install all dependencies
3. 🚀 Run `.\quick-start.ps1` to start API and Frontend
4. 🌐 Open http://localhost:3001 to use your video generator!

All issues are now resolved! 🎉
