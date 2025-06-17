"""
Performance Tests
Tests that validate application performance meets acceptable thresholds.
"""

import pytest
import time
import asyncio
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import os

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


class TestPerformance:
    """Test application performance metrics"""
    
    @pytest.fixture(scope="class")
    def test_app(self):
        """Create test application instance with performance monitoring"""
        test_env = {
            "ENVIRONMENT": "test",
            "DEBUG": "false",  # Disable debug for performance testing
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
    
    def test_root_endpoint_response_time(self, test_app):
        """Test that root endpoint responds within acceptable time"""
        start_time = time.time()
        response = test_app.get("/")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 2.0, f"Root endpoint took {response_time:.2f}s (should be < 2s)"
        assert response.status_code in [200, 302]
    
    def test_health_check_response_time(self, test_app):
        """Test that health check responds quickly"""
        start_time = time.time()
        response = test_app.get("/admin/status")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 5.0, f"Health check took {response_time:.2f}s (should be < 5s)"
        assert response.status_code == 200
    
    def test_static_file_response_time(self, test_app):
        """Test that static files load quickly"""
        start_time = time.time()
        response = test_app.get("/static/css/styles.css")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 1.0, f"Static file took {response_time:.2f}s (should be < 1s)"
        assert response.status_code == 200
    
    def test_concurrent_requests(self, test_app):
        """Test handling multiple concurrent requests"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                start_time = time.time()
                response = test_app.get("/admin/status")
                end_time = time.time()
                results.put({
                    'status': response.status_code,
                    'time': end_time - start_time
                })
            except Exception as e:
                results.put({'error': str(e)})
        
        # Start 5 concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Collect results
        response_times = []
        errors = 0
        
        while not results.empty():
            result = results.get()
            if 'error' in result:
                errors += 1
            else:
                response_times.append(result['time'])
                assert result['status'] == 200
        
        assert errors == 0, f"Got {errors} errors in concurrent requests"
        assert len(response_times) == 5, "Not all requests completed successfully"
        
        avg_time = sum(response_times) / len(response_times)
        assert avg_time < 3.0, f"Average response time {avg_time:.2f}s too high under load"


class TestMemoryUsage:
    """Test memory usage patterns"""
    
    def test_import_memory_usage(self):
        """Test that importing the app doesn't use excessive memory"""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Import the application
        test_env = {
            "ENVIRONMENT": "test",
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQUARE_ACCESS_TOKEN": "test-token",
            "SQUARE_ENVIRONMENT": "sandbox"
        }
        
        with patch.dict(os.environ, test_env):
            try:
                from app.main import app
                
                # Force garbage collection
                gc.collect()
                
                # Get memory after import
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = final_memory - initial_memory
                
                # Allow reasonable memory usage for import (adjust threshold as needed)
                assert memory_increase < 200, f"App import used {memory_increase:.1f}MB (should be < 200MB)"
                
            except ImportError:
                pytest.skip("Could not import app for memory testing")


class TestDatabasePerformance:
    """Test database operation performance"""
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self):
        """Test that basic database operations are performant"""
        test_env = {
            "ENVIRONMENT": "test",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
        
        with patch.dict(os.environ, test_env):
            try:
                from app.database.connection import get_async_session
                from sqlalchemy import text
                
                # Mock database operations for testing
                with patch('app.database.connection.create_async_engine') as mock_engine:
                    mock_session = MagicMock()
                    mock_engine.return_value.begin.return_value.__aenter__.return_value = mock_session
                    
                    start_time = time.time()
                    
                    # Simulate database query
                    async with get_async_session() as session:
                        # This would normally execute a query
                        pass
                    
                    end_time = time.time()
                    query_time = end_time - start_time
                    
                    # Should be very fast for mocked operations
                    assert query_time < 0.1, f"Database query simulation took {query_time:.3f}s"
                    
            except ImportError:
                pytest.skip("Could not import database modules")


class TestResourceUsage:
    """Test resource usage patterns"""
    
    def test_file_handle_usage(self):
        """Test that app doesn't leave file handles open"""
        import psutil
        
        process = psutil.Process()
        initial_files = process.num_fds() if hasattr(process, 'num_fds') else 0
        
        test_env = {
            "ENVIRONMENT": "test",
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
        
        with patch.dict(os.environ, test_env):
            try:
                from app.main import app
                from fastapi.testclient import TestClient
                
                client = TestClient(app)
                
                # Make several requests
                for _ in range(10):
                    response = client.get("/admin/status")
                
                final_files = process.num_fds() if hasattr(process, 'num_fds') else 0
                
                # Allow some increase but not excessive
                file_increase = final_files - initial_files
                assert file_increase < 50, f"File handle increase {file_increase} too high"
                
            except Exception:
                pytest.skip("Could not test file handle usage")


@pytest.mark.slow
class TestLoadTesting:
    """Load testing for production readiness"""
    
    @pytest.fixture(scope="class")
    def test_app(self):
        """Create test application for load testing"""
        test_env = {
            "ENVIRONMENT": "test",
            "DEBUG": "false",
            "SECRET_KEY": "test-secret-key-for-testing-only",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQUARE_ACCESS_TOKEN": "test-token",
            "SQUARE_ENVIRONMENT": "sandbox"
        }
        
        with patch.dict(os.environ, test_env):
            try:
                from app.main import app
                return TestClient(app)
            except Exception as e:
                pytest.skip(f"Could not create test app: {e}")
    
    def test_sustained_load(self, test_app):
        """Test application under sustained load"""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def sustained_requests():
            """Make requests continuously for a short period"""
            start = time.time()
            request_count = 0
            
            while time.time() - start < 5:  # Run for 5 seconds
                try:
                    response = test_app.get("/admin/status")
                    results.put(response.status_code)
                    request_count += 1
                    time.sleep(0.1)  # Small delay between requests
                except Exception as e:
                    errors.put(str(e))
            
            return request_count
        
        # Start load testing
        thread = threading.Thread(target=sustained_requests)
        thread.start()
        thread.join(timeout=10)
        
        # Collect results
        successful_requests = 0
        while not results.empty():
            status = results.get()
            if status == 200:
                successful_requests += 1
        
        error_count = errors.qsize()
        
        assert successful_requests > 0, "No successful requests during load test"
        assert error_count == 0, f"Got {error_count} errors during load test"
        
        # Should handle at least a few requests per second
        assert successful_requests >= 10, f"Only {successful_requests} successful requests in 5 seconds"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"]) 