# 🏠 Local Development Guide

## 🚀 Quick Start (No Environment Files Needed!)

The NyTex Dashboard is designed to work out-of-the-box for local development without requiring any environment files.

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install dependencies (if needed)
pip install -r requirements.txt

# 3. Start local server
python run.py
```

**That's it!** The server will start at http://localhost:8000

---

## 🔧 Local Development Configuration

When no environment files are present, the application uses these **smart defaults**:

### **Database Configuration**
- **Fallback Database**: `postgresql+asyncpg://postgres:password@localhost:5432/square_data_sync`
- **What this means**: Attempts to connect to local PostgreSQL
- **If no local DB**: App will start but database features won't work (expected)

### **Application Settings**
- **Secret Key**: `dev-key-change-this` (development-only key)
- **Debug Mode**: `False` (can be overridden)
- **Square API**: Not configured (expected for local development)

### **Expected Behavior**
✅ **Server starts successfully**  
✅ **Web interface loads**  
⚠️ **Database-dependent features may not work** (unless you have local PostgreSQL)  
⚠️ **Square API features won't work** (no access token)  

---

## 🗄️ Local Database Setup (Optional)

If you want full functionality locally, you can set up a local PostgreSQL database:

### **Option 1: Docker PostgreSQL**
```bash
# Start PostgreSQL in Docker
docker run --name nytex-local-db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=square_data_sync \
  -p 5432:5432 \
  -d postgres:17

# Connect to verify
psql postgresql://postgres:password@localhost:5432/square_data_sync
```

### **Option 2: Local PostgreSQL Installation**
```bash
# macOS (using Homebrew)
brew install postgresql@17
brew services start postgresql@17

# Create database
createdb square_data_sync
```

---

## 🔐 Adding Local Secrets (Optional)

If you need to test with actual secrets locally:

### **Create Local Environment File**
```bash
# Pull secrets from production (requires authentication)
python scripts/secrets_manager.py pull

# This creates .env.local with all production secrets
# ⚠️ Remember: .env.local is in .gitignore - never commit it!
```

### **Manual Local Configuration**
Create `.env.local` (will be ignored by git):
```bash
SECRET_KEY=your-local-secret-key
SQUARE_ACCESS_TOKEN=your-square-sandbox-token
SQUARE_ENVIRONMENT=sandbox
DEBUG=true
```

---

## 🎯 Development Workflow

### **For UI/Frontend Work**
No setup needed! Just run:
```bash
python run.py
```
All static pages and UI components will work perfectly.

### **For Database Features**
Set up local PostgreSQL (see above) or use cloud fallback:
```bash
# Pull production secrets to test with live data
python scripts/secrets_manager.py pull
python run.py
```

### **For Square API Testing**
Add Square sandbox credentials to `.env.local`:
```bash
SQUARE_ACCESS_TOKEN=your-sandbox-token
SQUARE_ENVIRONMENT=sandbox
```

---

## 🔍 Troubleshooting Local Development

### **"Server won't start"**
```bash
# Check if virtual environment is active
which python  # Should show .venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt

# Check for import errors
python -c "from run import app; print('OK')"
```

### **"Database connection errors"**
This is **expected** without local PostgreSQL. The app will still work for:
- Static pages
- UI components  
- Non-database features

### **"Square API not working"**
This is **expected** without SQUARE_ACCESS_TOKEN. Add it to `.env.local` if needed.

---

## 🔄 Configuration Priority

The application loads configuration in this order:

1. **Environment variables** (from shell or .env.local)
2. **Google Secret Manager** (in production only)
3. **Smart defaults** (for local development)

This means you can override any setting by creating `.env.local` or setting environment variables.

---

## 📚 Related Documentation

- [Secrets Management Guide](SECRETS_GUIDE.md) - For production secrets
- [Deployment Guide](DEPLOYMENT.md) - For production deployment
- [Troubleshooting Guide](TROUBLESHOOTING.md) - For production issues 