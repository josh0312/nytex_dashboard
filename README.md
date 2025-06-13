# 🧨 NyTex Fireworks Dashboard

> **Enterprise-grade inventory management and business intelligence dashboard for NyTex Fireworks**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](./docs/DOCKER_GUIDE.md)
[![Google Cloud](https://img.shields.io/badge/GCP-Secret_Manager-red?logo=google-cloud)](./docs/SECRETS_GUIDE.md)
[![FastAPI](https://img.shields.io/badge/FastAPI-Modern-green?logo=fastapi)](https://fastapi.tiangolo.com/)

## 🚀 Quick Start

### **Option 1: Docker Development (Recommended)**
```bash
# 1. Initialize secrets and environment
./scripts/dev-secrets.sh init

# 2. Configure your local secrets
nano .env.local

# 3. Start development environment
docker-compose -f docker-compose.simple.yml up --build

# 4. Access the dashboard
open http://localhost:8080
```

### **Option 2: Direct Python Development**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp production.env .env.local
# Edit .env.local with your values

# 3. Run the application
python run.py
```

## ✨ Features

### 📊 **Business Intelligence**
- **Real-time Dashboard**: Live sales metrics and inventory status
- **Seasonal Analytics**: Track performance by fireworks seasons
- **Customer Insights**: Comprehensive customer behavior analysis
- **Revenue Tracking**: Detailed financial reporting and trends

### 📦 **Inventory Management**
- **Square Integration**: Real-time sync with Square POS systems
- **Square Catalog Export**: Complete 76-column export matching Square's official format
- **Automated Categorization**: Smart product classification
- **Stock Alerts**: Low inventory notifications
- **Seasonal Tracking**: Track products by fireworks seasons

### 🔐 **Authentication & Security**
- **Microsoft 365 Integration**: Enterprise SSO with O365
- **Manual Authentication**: Fallback guest account system
- **Google Secret Manager**: Production-grade secrets management
- **Role-based Access**: Secure user permissions

### 🏗️ **Architecture**
- **FastAPI Backend**: Modern async Python web framework
- **PostgreSQL Database**: Robust data persistence
- **HTMX Frontend**: Dynamic UI without complex JavaScript
- **Docker Ready**: Complete containerization for development and production

## 📁 Project Structure

```
nytex_dashboard/
├── app/                        # Main application
│   ├── database/              # Database models and queries
│   ├── routes/                # API endpoints and web routes
│   ├── services/              # Business logic layer
│   ├── templates/             # Jinja2 HTML templates
│   └── static/                # CSS, JavaScript, assets
├── scripts/                    # Automation and utilities
│   ├── secrets_manager.py     # Google Secret Manager integration
│   ├── dev-secrets.sh         # Development secrets helper
│   └── operational/           # Production utilities
├── docs/                       # Documentation
│   ├── DOCKER_GUIDE.md       # Docker development guide
│   ├── SECRETS_GUIDE.md      # Secrets management guide
│   ├── DEPLOYMENT.md         # Production deployment
│   └── CATALOG_PAGE.md           # Square catalog management guide
├── docker-compose.yml         # Full development environment
├── docker-compose.simple.yml  # Simplified development
└── docker-compose.prod.yml    # Production testing
```

## 🛠️ Development

### **Environment Setup**

1. **Secrets Management**:
   ```bash
   # Initialize development environment
   ./scripts/dev-secrets.sh init
   
   # Sync with production secrets
   ./scripts/dev-secrets.sh pull
   
   # Push local changes to production
   ./scripts/dev-secrets.sh push
   ```

2. **Database Setup**:
   ```bash
   # Run migrations
   alembic upgrade head
   
   # Create test data
   python scripts/seed_data.py
   ```

3. **Development Modes**:
   ```bash
   # Simple local development
   docker-compose -f docker-compose.simple.yml up
   
   # Full development with database
   docker-compose up
   
   # Production-like testing
   docker-compose -f docker-compose.prod.yml up
   ```

### **Common Development Tasks**

**View Logs**:
```bash
docker-compose logs -f nytex-dashboard
```

**Access Database**:
```bash
# Connect to local database
psql postgresql://user:pass@localhost:5432/nytex_dashboard

# Or use pgAdmin at http://localhost:8081
```

**Run Tests**:
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=app
```

## 🚀 Deployment

### **Production Deployment**

1. **Google Cloud Run** (Recommended):
   ```bash
   # Deploy with secrets integration
   gcloud run deploy nytex-dashboard \
     --source . \
     --dockerfile Dockerfile.secrets \
     --region=us-central1 \
     --allow-unauthenticated
   ```

2. **Docker Container**:
   ```bash
   # Build production image
   docker build -f Dockerfile.secrets -t nytex-dashboard .
   
   # Run with Secret Manager
   docker run -p 8080:8080 \
     -e GOOGLE_CLOUD_PROJECT=nytex-business-systems \
     nytex-dashboard
   ```

### **Environment Configuration**

| Environment | Database | Secrets | Authentication |
|-------------|----------|---------|----------------|
| **Development** | Local PostgreSQL | `.env.local` file | Manual + O365 |
| **Staging** | Cloud SQL | Google Secret Manager | Manual + O365 |
| **Production** | Cloud SQL | Google Secret Manager | O365 Only |

## 🔧 Configuration

### **Required Environment Variables**

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Application secret key | `your-secret-key-here` |
| `SQUARE_ACCESS_TOKEN` | Square API token | `EAAAxx...` |
| `SQUARE_ENVIRONMENT` | Square environment | `sandbox` or `production` |
| `SQLALCHEMY_DATABASE_URI` | Database connection | `postgresql://user:pass@host/db` |
| `AZURE_CLIENT_ID` | O365 application ID | `11471949-...` |
| `AZURE_CLIENT_SECRET` | O365 application secret | `Yrn8Q~...` |
| `AZURE_TENANT_ID` | O365 tenant ID | `1e478c98-...` |

### **Optional Configuration**

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Application environment | `development` |
| `DEBUG` | Enable debug mode | `True` |
| `PORT` | Server port | `8080` |
| `LOG_LEVEL` | Logging level | `INFO` |

## 📚 Integrated Documentation System

The NyTex Dashboard includes a comprehensive **web-based documentation system** accessible at `/docs`. This wiki-style knowledge base provides:

- **🌐 Web interface** - Browse all documentation without leaving the app
- **🔗 Automatic cross-linking** - Key terms link to relevant documentation
- **🎯 Contextual help** - Help icons and floating help button throughout the interface
- **📱 Responsive design** - Works on desktop and mobile devices
- **📖 Rich formatting** - Full Markdown support with syntax highlighting

### **Quick Access**
- **Main navigation**: Click "Help" in the top menu
- **Floating button**: Blue help button (bottom-right corner) 
- **Direct URL**: Visit `/docs` for the documentation homepage
- **Contextual links**: Help icons next to page titles

### **System Documentation**
- **[Docker Development Guide](./docs/DOCKER_GUIDE.md)** - Complete Docker setup and workflow
- **[Secrets Management Guide](./docs/SECRETS_GUIDE.md)** - Google Secret Manager integration
- **[Authentication Setup](./docs/AUTHENTICATION.md)** - O365 and manual authentication
- **[Documentation System](./docs/DOCUMENTATION_SYSTEM.md)** - How the integrated docs work
- **[API Documentation](http://localhost:8080/docs)** - Interactive API docs (when running)

### **Page Documentation**
- **[Dashboard Page](./docs/DASHBOARD_PAGE.md)** - Main analytics and business intelligence hub
- **[Reports Page](./docs/REPORTS_PAGE.md)** - Comprehensive inventory and business reports
- **[Catalog Page](./docs/CATALOG_PAGE.md)** - Square catalog management and export system
- **[Items Page](./docs/ITEMS_PAGE.md)** - Advanced inventory management and search
- **[Tools Page](./docs/TOOLS_PAGE.md)** - Administrative utilities and system tools
- **[Admin Page](./docs/ADMIN_PAGE.md)** - System administration and data synchronization

> 💡 **Tip**: All documentation is also available through the integrated web interface at `/docs` with enhanced navigation, search, and cross-linking between topics.

## 🔒 Security

- **Secrets Management**: All secrets stored in Google Secret Manager
- **Authentication**: Microsoft 365 SSO with manual fallback
- **HTTPS Only**: Force HTTPS in production
- **Input Validation**: Comprehensive request validation
- **SQL Injection Protection**: Using SQLAlchemy ORM with parameterized queries

## 🧪 Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app --cov-report=html

# Run integration tests
python -m pytest tests/integration/

# Test specific component
python -m pytest tests/test_square_api.py -v
```

## 📊 Monitoring

- **Application Logs**: Structured logging with context
- **Health Checks**: Built-in health monitoring endpoints
- **Performance Metrics**: Request timing and resource usage
- **Error Tracking**: Comprehensive error reporting

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Set up development environment**: `./scripts/dev-secrets.sh init`
4. **Make your changes and test thoroughly**
5. **Commit with clear messages**: `git commit -m 'Add amazing feature'`
6. **Push to your branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

## 📄 License

This project is proprietary software for NyTex Fireworks. All rights reserved.

## 🆘 Support

- **Documentation**: Check the `docs/` directory
- **Issues**: Contact the development team
- **Emergency**: See `docs/SUPPORT.md` for escalation procedures

---

**Built with ❤️ for NyTex Fireworks** 