# Google Cloud Configuration

## Project Details
- **Project ID**: nytex-business-systems
- **Project Number**: 932676587025
- **Database Instance**: nytex-main-db
- **Database IP**: 34.67.201.62
- **Region**: us-central1-f
- **Database Version**: PostgreSQL 17

## Database Configuration
- **Instance Type**: PostgreSQL 17
- **CPU**: 1 vCPU (db-f1-micro)
- **Memory**: 614MB RAM
- **Storage**: 10GB SSD
- **Estimated Cost**: $7-15/month

## Database Credentials
- **Database Name**: nytex_dashboard
- **Username**: nytex_user
- **Password**: NytexSecure2024!
- **Connection Name**: nytex-business-systems:us-central1-f:nytex-main-db

## Environment Variables for Cloud Deployment

### Database Connection
```
# Cloud SQL connection string format
DATABASE_URL=postgresql+asyncpg://nytex_user:NytexSecure2024!@/nytex_dashboard?host=/cloudsql/nytex-business-systems:us-central1-f:nytex-main-db

# Alternative format for Cloud Run
CLOUD_SQL_CONNECTION_NAME=nytex-business-systems:us-central1-f:nytex-main-db
DB_USER=nytex_user
DB_PASS=NytexSecure2024!
DB_NAME=nytex_dashboard
```

### Application Configuration
```
SECRET_KEY=production-secret-key-here
SQLALCHEMY_ECHO=false
GOOGLE_CLOUD_PROJECT=nytex-business-systems
```

## Next Steps

1. ✅ **Install Google Cloud CLI** 
2. ✅ **Authenticate with Google Cloud**
3. ✅ **Create database and user in Cloud SQL**
4. **Create Dockerfile for the application** ✅
5. **Set up Cloud Build for CI/CD** ✅
6. **Deploy to Cloud Run**

## Commands to Test Connection

```bash
# Test connection to Cloud SQL
gcloud sql connect nytex-main-db --user=nytex_user --database=nytex_dashboard

# Build and test Docker image locally
docker build -t nytex-dashboard .
docker run -p 8080:8080 nytex-dashboard

# Deploy to Cloud Run (after setting up environment variables)
gcloud run deploy nytex-dashboard \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances nytex-business-systems:us-central1-f:nytex-main-db
```

## Security Notes
- Database has public IP for initial setup
- Will configure authorized networks for security
- Consider private IP for production
- Enable SSL connections
- Use IAM database authentication when possible
- Store sensitive environment variables in Google Secret Manager 