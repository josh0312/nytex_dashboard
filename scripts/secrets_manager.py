#!/usr/bin/env python3
"""
NyTex Dashboard Secrets Manager
Manages secrets between local development and Google Secret Manager

Usage:
    python scripts/secrets_manager.py push    # Push local .env.local to Secret Manager
    python scripts/secrets_manager.py pull    # Pull secrets from Secret Manager to .env.local
    python scripts/secrets_manager.py list    # List all secrets in Secret Manager
    python scripts/secrets_manager.py compare # Compare local vs remote secrets
"""

import os
import sys
import argparse
from pathlib import Path
from google.cloud import secretmanager
from google.api_core import exceptions
import json
from typing import Dict, Optional
import subprocess

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

class SecretsManager:
    def __init__(self, project_id: str = "nytex-business-systems"):
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_path = f"projects/{project_id}"
        
        # Define secret mappings
        self.secret_mappings = {
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
            "SQLALCHEMY_DATABASE_URI": "database-uri"
        }

    def read_local_env(self, env_file: str = ".env.local") -> Dict[str, str]:
        """Read environment variables from local file"""
        env_vars = {}
        env_path = Path(env_file)
        
        if not env_path.exists():
            print(f"❌ Environment file {env_file} not found!")
            return {}
            
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        return env_vars

    def write_local_env(self, env_vars: Dict[str, str], env_file: str = ".env.local"):
        """Write environment variables to local file"""
        env_path = Path(env_file)
        
        with open(env_path, 'w') as f:
            f.write("# Environment variables synced from Google Secret Manager\n")
            f.write(f"# Generated automatically - do not edit manually\n\n")
            
            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")
        
        print(f"✅ Environment file {env_file} updated")

    def create_secret(self, secret_id: str) -> bool:
        """Create a new secret in Secret Manager"""
        try:
            secret = {
                "replication": {"automatic": {}}
            }
            
            response = self.client.create_secret(
                request={
                    "parent": self.project_path,
                    "secret_id": secret_id,
                    "secret": secret
                }
            )
            print(f"✅ Created secret: {secret_id}")
            return True
            
        except exceptions.AlreadyExists:
            # Secret already exists, which is fine
            return True
        except Exception as e:
            print(f"❌ Failed to create secret {secret_id}: {e}")
            return False

    def add_secret_version(self, secret_id: str, value: str) -> bool:
        """Add a new version to an existing secret"""
        try:
            parent = f"{self.project_path}/secrets/{secret_id}"
            payload = {"data": value.encode("UTF-8")}
            
            response = self.client.add_secret_version(
                request={"parent": parent, "payload": payload}
            )
            print(f"✅ Updated secret: {secret_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update secret {secret_id}: {e}")
            return False

    def get_secret_value(self, secret_id: str) -> Optional[str]:
        """Get the latest version of a secret"""
        try:
            name = f"{self.project_path}/secrets/{secret_id}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
            
        except exceptions.NotFound:
            return None
        except Exception as e:
            print(f"❌ Failed to get secret {secret_id}: {e}")
            return None

    def list_secrets(self) -> Dict[str, str]:
        """List all secrets and their values"""
        secrets = {}
        
        try:
            response = self.client.list_secrets(request={"parent": self.project_path})
            
            for secret in response:
                secret_id = secret.name.split('/')[-1]
                value = self.get_secret_value(secret_id)
                secrets[secret_id] = value
                
        except Exception as e:
            print(f"❌ Failed to list secrets: {e}")
            
        return secrets

    def push_to_secret_manager(self, env_file: str = ".env.local") -> bool:
        """Push local environment variables to Secret Manager"""
        print(f"🔄 Pushing {env_file} to Google Secret Manager...")
        
        env_vars = self.read_local_env(env_file)
        if not env_vars:
            return False
        
        success_count = 0
        total_count = 0
        
        for env_key, secret_id in self.secret_mappings.items():
            if env_key in env_vars:
                total_count += 1
                
                # Create secret if it doesn't exist
                if self.create_secret(secret_id):
                    # Add the secret value
                    if self.add_secret_version(secret_id, env_vars[env_key]):
                        success_count += 1
        
        print(f"\n📊 Summary: {success_count}/{total_count} secrets updated successfully")
        return success_count == total_count

    def pull_from_secret_manager(self, env_file: str = ".env.local") -> bool:
        """Pull secrets from Secret Manager to local environment file"""
        print(f"🔄 Pulling secrets from Google Secret Manager to {env_file}...")
        
        env_vars = {}
        success_count = 0
        total_count = len(self.secret_mappings)
        
        for env_key, secret_id in self.secret_mappings.items():
            value = self.get_secret_value(secret_id)
            if value:
                env_vars[env_key] = value
                success_count += 1
                print(f"✅ Retrieved: {env_key}")
            else:
                print(f"⚠️  Not found: {env_key} (secret: {secret_id})")
        
        if env_vars:
            self.write_local_env(env_vars, env_file)
            
        print(f"\n📊 Summary: {success_count}/{total_count} secrets retrieved successfully")
        return success_count > 0

    def compare_secrets(self, env_file: str = ".env.local"):
        """Compare local environment file with Secret Manager"""
        print("🔍 Comparing local environment with Secret Manager...")
        
        local_vars = self.read_local_env(env_file)
        
        print("\n📋 Comparison Results:")
        print("-" * 60)
        
        for env_key, secret_id in self.secret_mappings.items():
            local_value = local_vars.get(env_key, "")
            remote_value = self.get_secret_value(secret_id) or ""
            
            # Mask sensitive values for display
            local_display = self._mask_value(local_value)
            remote_display = self._mask_value(remote_value)
            
            if local_value == remote_value:
                status = "✅ MATCH"
            elif not local_value:
                status = "⚠️  LOCAL MISSING"
            elif not remote_value:
                status = "⚠️  REMOTE MISSING"
            else:
                status = "❌ DIFFERENT"
            
            print(f"{env_key:25} | {status:15} | Local: {local_display:20} | Remote: {remote_display}")

    def _mask_value(self, value: str, show_chars: int = 4) -> str:
        """Mask sensitive values for display"""
        if not value:
            return "(empty)"
        
        if len(value) <= show_chars * 2:
            return "*" * len(value)
        
        return value[:show_chars] + "*" * (len(value) - show_chars * 2) + value[-show_chars:]

    def check_authentication(self) -> bool:
        """Check if user is authenticated with Google Cloud"""
        try:
            # Try to list secrets to verify authentication
            self.client.list_secrets(request={"parent": self.project_path})
            return True
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print("💡 Run: gcloud auth application-default login")
            return False

def main():
    parser = argparse.ArgumentParser(description="NyTex Dashboard Secrets Manager")
    parser.add_argument("action", choices=["push", "pull", "list", "compare", "init"], 
                       help="Action to perform")
    parser.add_argument("--env-file", default=".env.local", 
                       help="Environment file to use (default: .env.local)")
    parser.add_argument("--project-id", default="nytex-business-systems",
                       help="Google Cloud project ID")
    
    args = parser.parse_args()
    
    # Initialize secrets manager
    secrets_manager = SecretsManager(args.project_id)
    
    # Check authentication first
    if not secrets_manager.check_authentication():
        sys.exit(1)
    
    # Execute requested action
    if args.action == "push":
        success = secrets_manager.push_to_secret_manager(args.env_file)
        sys.exit(0 if success else 1)
        
    elif args.action == "pull":
        success = secrets_manager.pull_from_secret_manager(args.env_file)
        sys.exit(0 if success else 1)
        
    elif args.action == "list":
        secrets = secrets_manager.list_secrets()
        print("\n📋 Current secrets in Secret Manager:")
        print("-" * 50)
        for secret_id, value in secrets.items():
            masked_value = secrets_manager._mask_value(value or "")
            print(f"{secret_id:30} | {masked_value}")
        
    elif args.action == "compare":
        secrets_manager.compare_secrets(args.env_file)
        
    elif args.action == "init":
        print("🚀 Initializing secrets management...")
        
        # Create example env file if it doesn't exist
        env_path = Path(args.env_file)
        if not env_path.exists():
            example_env = """# NyTex Dashboard Local Environment Variables
SECRET_KEY=dev-secret-key-not-for-production
SQUARE_ACCESS_TOKEN=your-square-access-token
SQUARE_ENVIRONMENT=sandbox
OPENWEATHER_API_KEY=your-openweather-api-key
MANUAL_USER_EMAIL=guest@nytexfireworks.com
MANUAL_USER_PASSWORD=NytexD@shboard2025!
MANUAL_USER_NAME=Guest User
AZURE_CLIENT_ID=11471949-d82c-4fd2-b6c2-125de0e4dade
AZURE_CLIENT_SECRET=your-azure-client-secret
AZURE_TENANT_ID=1e478c98-66d7-4487-a4fa-53df0bf2d103
AZURE_REDIRECT_URI=http://localhost:8080/auth/callback
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://user:pass@localhost:5432/db
"""
            with open(env_path, 'w') as f:
                f.write(example_env)
            print(f"✅ Created example environment file: {args.env_file}")
            print(f"💡 Edit {args.env_file} with your actual values, then run:")
            print(f"   python scripts/secrets_manager.py push")

if __name__ == "__main__":
    main() 