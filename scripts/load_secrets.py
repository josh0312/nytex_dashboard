#!/usr/bin/env python3
"""
Load secrets from Google Secret Manager and set as environment variables
Used in production to dynamically load secrets at startup
"""

import os
import sys
from google.cloud import secretmanager
from google.api_core import exceptions

def load_secrets_to_env(project_id: str = "nytex-business-systems"):
    """Load secrets from Secret Manager and set as environment variables"""
    
    # Initialize the Secret Manager client
    client = secretmanager.SecretManagerServiceClient()
    project_path = f"projects/{project_id}"
    
    # Define secret mappings (same as in secrets_manager.py)
    secret_mappings = {
        "SECRET_KEY": "secret-key",
        "SQUARE_ACCESS_TOKEN": "square-access-token", 
        "SQUARE_ENVIRONMENT": "square-environment",
        "OPENWEATHER_API_KEY": "openweather-api-key",
        "MANUAL_USER_EMAIL": "manual-user-email",
        "MANUAL_USER_PASSWORD": "manual-user-password",
        "MANUAL_USER_NAME": "manual-user-name",
        "AZURE_CLIENT_ID": "azure-client-id",
        "AZURE_CLIENT_SECRET": "azure-client-secret",
        "AZURE_TENANT_ID": "azure-tenant-id",
        "AZURE_REDIRECT_URI": "azure-redirect-uri",
        "SQLALCHEMY_DATABASE_URI": "database-uri",
        # Email notification credentials
        "SMTP_USERNAME": "smtp-username",
        "SMTP_PASSWORD": "smtp-password",
        "SMTP_SENDER_EMAIL": "smtp-sender-email",
        "SYNC_NOTIFICATION_RECIPIENTS": "sync-notification-recipients"
    }
    
    loaded_count = 0
    
    for env_key, secret_id in secret_mappings.items():
        try:
            # Get the secret value
            name = f"{project_path}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            
            # Set as environment variable
            os.environ[env_key] = secret_value
            loaded_count += 1
            print(f"✅ Loaded secret: {env_key}")
            
        except exceptions.NotFound:
            print(f"⚠️  Secret not found: {secret_id} (for {env_key})")
        except Exception as e:
            print(f"❌ Failed to load secret {secret_id}: {e}")
    
    print(f"📊 Loaded {loaded_count}/{len(secret_mappings)} secrets from Secret Manager")
    
    if loaded_count == 0:
        print("❌ No secrets loaded! Check authentication and secret names.")
        sys.exit(1)
    
    return loaded_count

if __name__ == "__main__":
    # Load secrets when run as a script
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "nytex-business-systems")
    load_secrets_to_env(project_id) 