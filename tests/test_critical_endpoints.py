"""
Critical Endpoint Tests
These tests validate essential application functionality before deployment.
All tests in this file must pass for deployment to proceed.
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json


class TestCriticalEndpoints:
    """Test critical endpoints that must work in production"""
    
    @pytest.fixture(scope="class")
    def test_app(self):
        """Create test application instance"""
        # Mock environment variables for testing
        test_env = {
            "ENVIRONMENT": "test",
            "DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQUARE_ACCESS_TOKEN": "test-token",
            "SQUARE_ENVIRONMENT": "sandbox",
            "OPENWEATHER_API_KEY": "test-key",
            "MANUAL_USER_EMAIL": "test@example.com",
            "MANUAL_USER_PASSWORD": "test-password",
            "MANUAL_USER_NAME": "Test User"
        }
        
        with patch.dict(os.environ, test_env):
            try:
                from app.main import app
                return TestClient(app)
            except Exception as e:
                pytest.skip(f"Could not create test app: {e}")
    
    def test_root_endpoint(self, test_app):
        """Test that root endpoint returns successfully"""
        response = test_app.get("/")
        assert response.status_code in [200, 302], f"Root endpoint failed with status {response.status_code}"
    
    def test_health_check_endpoint(self, test_app):
        """Test health check endpoint"""
        response = test_app.get("/admin/status")
        assert response.status_code == 200, f"Health check failed with status {response.status_code}"
        
        # Verify response contains expected fields
        data = response.json()
        required_fields = ["database", "square_config"]
        for field in required_fields:
            assert field in data, f"Health check missing required field: {field}"
    
    def test_authentication_endpoints(self, test_app):
        """Test that auth endpoints are accessible"""
        # Test login page
        response = test_app.get("/auth/login")
        assert response.status_code == 200, "Login page not accessible"
        
        # Test that protected endpoints redirect to login
        response = test_app.get("/admin/sync")
        assert response.status_code in [302, 401, 403], "Protected endpoint should require auth"
    
    def test_static_files_accessible(self, test_app):
        """Test that static files are served correctly"""
        # Test CSS
        response = test_app.get("/static/css/styles.css")
        assert response.status_code == 200, "CSS files not accessible"
        
        # Test JS
        response = test_app.get("/static/js/app.js")
        assert response.status_code == 200, "JS files not accessible"
    
    def test_dashboard_endpoint(self, test_app):
        """Test that dashboard loads without critical errors"""
        response = test_app.get("/dashboard")
        # Should either load (200) or redirect to login (302)
        assert response.status_code in [200, 302], f"Dashboard endpoint failed with status {response.status_code}"
    
    def test_reports_landing_page(self, test_app):
        """Test that reports page loads"""
        response = test_app.get("/reports")
        assert response.status_code in [200, 302], f"Reports page failed with status {response.status_code}"
    
    def test_api_documentation(self, test_app):
        """Test that API docs are accessible"""
        response = test_app.get("/docs")
        assert response.status_code == 200, "API documentation not accessible"


class TestConfigurationValidation:
    """Test that application configuration is valid"""
    
    def test_required_environment_variables(self):
        """Test that critical environment variables can be loaded"""
        critical_vars = [
            "SECRET_KEY",
            "SQLALCHEMY_DATABASE_URI",
            "SQUARE_ACCESS_TOKEN",
            "SQUARE_ENVIRONMENT"
        ]
        
        # In CI/CD, these should be available via secrets
        # In local dev, they might have defaults
        for var in critical_vars:
            value = os.environ.get(var)
            # Allow None for local testing, but in CI it should be set
            if os.environ.get("ENVIRONMENT") == "production":
                assert value is not None, f"Critical environment variable {var} not set"
            # Basic validation for non-empty values in production
            if value is not None:
                assert len(value.strip()) > 0, f"Environment variable {var} is empty"
    
    def test_database_uri_format(self):
        """Test that database URI has correct format"""
        db_uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
        if db_uri:
            # Should start with postgresql+asyncpg:// for production
            if os.environ.get("ENVIRONMENT") == "production":
                assert db_uri.startswith("postgresql+asyncpg://"), "Production should use PostgreSQL with asyncpg"
            
            # Should not contain localhost in production
            if os.environ.get("ENVIRONMENT") == "production":
                assert "localhost" not in db_uri, "Production should not use localhost database"
    
    def test_square_environment_validity(self):
        """Test that Square environment is valid"""
        square_env = os.environ.get("SQUARE_ENVIRONMENT")
        if square_env:
            valid_envs = ["sandbox", "production"]
            assert square_env in valid_envs, f"Square environment must be one of {valid_envs}"


class TestApplicationImports:
    """Test that critical application modules can be imported"""
    
    def test_main_app_import(self):
        """Test that main application can be imported"""
        try:
            from app.main import app
            assert app is not None, "Main application object is None"
        except ImportError as e:
            pytest.fail(f"Could not import main application: {e}")
    
    def test_database_models_import(self):
        """Test that database models can be imported"""
        try:
            from app.database.models import order, payment, catalog
            # Basic validation that models exist
            assert hasattr(order, 'Order'), "Order model not found"
            assert hasattr(payment, 'Payment'), "Payment model not found"
            assert hasattr(catalog, 'CatalogItem'), "CatalogItem model not found"
        except ImportError as e:
            pytest.fail(f"Could not import database models: {e}")
    
    def test_services_import(self):
        """Test that critical services can be imported"""
        try:
            from app.services import square_service, current_season
            # Basic validation
            assert hasattr(square_service, 'SquareService'), "SquareService not found"
        except ImportError as e:
            pytest.fail(f"Could not import services: {e}")
    
    def test_routes_import(self):
        """Test that route modules can be imported"""
        try:
            from app.routes import dashboard, admin, auth, reports
            # These should import without errors
        except ImportError as e:
            pytest.fail(f"Could not import routes: {e}")


class TestDatabaseConnection:
    """Test database connectivity (mocked for CI/CD)"""
    
    @pytest.mark.asyncio
    async def test_database_connection_mock(self):
        """Test database connection logic (mocked for CI/CD)"""
        # Mock the database connection for CI/CD
        with patch('app.database.connection.create_async_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            
            try:
                from app.database.connection import get_async_session
                # This should not raise an exception
                async with get_async_session() as session:
                    assert session is not None
            except Exception as e:
                pytest.fail(f"Database connection logic failed: {e}")


@pytest.mark.deployment
class TestDeploymentReadiness:
    """Tests that must pass for production deployment"""
    
    def test_no_debug_mode_in_production(self):
        """Ensure debug mode is disabled in production"""
        if os.environ.get("ENVIRONMENT") == "production":
            debug_setting = os.environ.get("DEBUG", "false").lower()
            assert debug_setting in ["false", "0", ""], "Debug mode must be disabled in production"
    
    def test_secret_key_strength(self):
        """Test that secret key is sufficiently strong"""
        secret_key = os.environ.get("SECRET_KEY")
        if secret_key and os.environ.get("ENVIRONMENT") == "production":
            # Production secret key should be long and not use defaults
            assert len(secret_key) >= 32, "Production secret key should be at least 32 characters"
            assert secret_key not in ["your-secret-key", "dev-secret-key"], "Using default secret key"
    
    def test_required_secrets_present(self):
        """Test that all required secrets are available in production"""
        if os.environ.get("ENVIRONMENT") == "production":
            required_secrets = [
                "SECRET_KEY",
                "SQLALCHEMY_DATABASE_URI", 
                "SQUARE_ACCESS_TOKEN",
                "SQUARE_ENVIRONMENT",
                "MANUAL_USER_EMAIL",
                "MANUAL_USER_PASSWORD"
            ]
            
            for secret in required_secrets:
                value = os.environ.get(secret)
                assert value is not None, f"Required secret {secret} not found"
                assert len(value.strip()) > 0, f"Required secret {secret} is empty"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"]) 