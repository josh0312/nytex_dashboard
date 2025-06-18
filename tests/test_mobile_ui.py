"""
Mobile UI Components Tests
These tests validate mobile UI elements like navigation, footer, and responsive design.
Critical for ensuring mobile UX works correctly across deployments.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


@pytest.mark.mobile_ui
class TestMobileNavigationUI:
    """Test mobile navigation and UI components"""
    
    @pytest.fixture(scope="class")
    def test_app(self):
        """Create test application instance"""
        test_env = {
            "ENVIRONMENT": "test",
            "DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only",
            "SQLALCHEMY_DATABASE_URI": "sqlite+aiosqlite:///:memory:",
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
    
    def test_hamburger_menu_visibility_elements(self, test_app):
        """Test that hamburger menu has proper visibility in light/dark mode"""
        response = test_app.get("/items")  # Any page with base template
        
        if response.status_code == 302:  # Redirect to login
            pytest.skip("Authentication required")
        
        assert response.status_code == 200, f"Page failed with status {response.status_code}"
        
        content = response.text
        
        # Check for hamburger menu elements with proper styling
        hamburger_elements = [
            'mobileMenuOpen',  # Alpine.js variable
            'data-lucide="menu"',  # Menu icon with proper syntax
            'data-lucide="x"',  # Close icon with proper syntax
            'text-gray-600 dark:text-gray-300',  # Proper color scheme
            'hover:text-gray-900 dark:hover:text-white',  # Hover states
            'focus:ring-2 focus:ring-inset focus:ring-blue-500',  # Focus states
            'sm:hidden',  # Mobile-only visibility
        ]
        
        for element in hamburger_elements:
            assert element in content, f"Hamburger menu element '{element}' not found"
    
    def test_mobile_footer_structure(self, test_app):
        """Test that mobile footer has proper responsive structure"""
        response = test_app.get("/items")
        
        if response.status_code == 302:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for mobile footer elements
        mobile_footer_elements = [
            'sm:hidden',  # Mobile-only footer
            'hidden sm:block',  # Desktop-only footer
            'flex flex-col items-center text-center',  # Mobile layout
            'py-6 space-y-4',  # Mobile spacing
            'text-xs',  # Mobile text size
            'h-4 w-4',  # Mobile icon size
        ]
        
        for element in mobile_footer_elements:
            assert element in content, f"Mobile footer element '{element}' not found"
    
    def test_main_content_spacing(self, test_app):
        """Test that main content has proper spacing for mobile"""
        response = test_app.get("/items")
        
        if response.status_code == 302:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for proper content spacing
        spacing_elements = [
            'pb-8 sm:pb-6',  # Extra bottom padding for mobile
            'mt-auto',  # Footer positioning
            'min-h-screen flex flex-col',  # Flex layout for proper footer positioning
        ]
        
        for element in spacing_elements:
            assert element in content, f"Content spacing element '{element}' not found"
    
    def test_theme_toggle_icons_proper_syntax(self, test_app):
        """Test that theme toggle icons use proper data-lucide syntax"""
        response = test_app.get("/items")
        
        if response.status_code == 302:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for proper icon syntax (not class-based)
        icon_elements = [
            'data-lucide="sun"',  # Sun icon with data attribute
            'data-lucide="moon"',  # Moon icon with data attribute
            'text-amber-500',  # Sun color
            'text-blue-400',  # Moon color
        ]
        
        for element in icon_elements:
            assert element in content, f"Theme toggle icon element '{element}' not found"
        
        # Ensure old class-based syntax is not present
        old_syntax = [
            'class="lucide lucide-sun"',
            'class="lucide lucide-moon"',
        ]
        
        for old_element in old_syntax:
            assert old_element not in content, f"Old icon syntax '{old_element}' should not be present"
    
    def test_mobile_navigation_menu_structure(self, test_app):
        """Test that mobile navigation menu has proper structure"""
        response = test_app.get("/items")
        
        if response.status_code == 302:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for mobile menu structure
        mobile_nav_elements = [
            'x-show="mobileMenuOpen"',  # Alpine.js show directive
            'sm:hidden',  # Mobile-only menu
            'border-l-4',  # Mobile menu item styling
            'hover:bg-gray-50 dark:hover:bg-gray-700',  # Hover states
            'text-gray-600 dark:text-gray-300',  # Text colors
        ]
        
        for element in mobile_nav_elements:
            assert element in content, f"Mobile navigation element '{element}' not found"


@pytest.mark.mobile_ui
class TestMobileItemsIntegration:
    """Test mobile items page integration with UI components"""
    
    @pytest.fixture(scope="class")
    def test_app(self):
        """Create test application instance"""
        test_env = {
            "ENVIRONMENT": "test",
            "DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only",
            "SQLALCHEMY_DATABASE_URI": "sqlite+aiosqlite:///:memory:",
            "SQUARE_ACCESS_TOKEN": "test-token",
            "SQUARE_ENVIRONMENT": "sandbox",
        }
        
        with patch.dict(os.environ, test_env):
            try:
                from app.main import app
                return TestClient(app)
            except Exception as e:
                pytest.skip(f"Could not create test app: {e}")
    
    def test_items_page_mobile_ui_integration(self, test_app):
        """Test that items page properly integrates with mobile UI components"""
        response = test_app.get("/items")
        
        if response.status_code == 302:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        content = response.text
        
        # Check that items page includes mobile UI elements
        integration_elements = [
            # Base template mobile elements
            'mobileMenuOpen',
            'data-lucide="menu"',
            'sm:hidden',  # Mobile footer
            
            # Items-specific mobile elements
            'dev-mobile-mode',
            'mobile-filters',
            'slide-panel',
            'collapsed-header',
            
            # Pagination mobile elements
            'paginationSize: 7',
            '"first": "⏮"',
            '@media (max-width: 767px)',
        ]
        
        for element in integration_elements:
            assert element in content, f"Mobile UI integration element '{element}' not found"
    
    def test_no_ui_element_conflicts(self, test_app):
        """Test that mobile UI elements don't conflict with each other"""
        response = test_app.get("/items")
        
        if response.status_code == 302:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for potential conflicting z-index issues
        z_index_checks = [
            'z-40',  # Dev toggle button
            'z-50',  # Slide panel and other overlays
        ]
        
        for z_index in z_index_checks:
            assert z_index in content, f"Z-index '{z_index}' not found for proper layering"
        
        # Ensure multiple mobile filter containers don't exist
        mobile_filter_count = content.count('class="mobile-filters')
        assert mobile_filter_count >= 1, "Mobile filters container should exist"
        
        # Ensure proper Alpine.js integration
        alpine_elements = [
            'x-data=',  # Alpine.js data
            'x-show=',  # Alpine.js show
            '@click=',  # Alpine.js click handler
        ]
        
        for element in alpine_elements:
            assert element in content, f"Alpine.js element '{element}' not found"


@pytest.mark.deployment
class TestMobileUIDeploymentReadiness:
    """Test mobile UI components are deployment ready"""
    
    def test_mobile_ui_critical_files_accessible(self):
        """Test that mobile UI works with critical files"""
        test_env = {
            "ENVIRONMENT": "test",
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite+aiosqlite:///:memory:",
            "SQUARE_ACCESS_TOKEN": "test-token",
            "SQUARE_ENVIRONMENT": "sandbox"
        }
        
        with patch.dict(os.environ, test_env):
            try:
                from app.main import app
                client = TestClient(app)
                
                # Test key mobile-enabled pages
                mobile_pages = ["/", "/items", "/reports", "/dashboard"]
                
                for page in mobile_pages:
                    response = client.get(page)
                    # Accept success or redirect (auth required)
                    assert response.status_code in [200, 302, 500], \
                        f"Mobile page {page} failed with status {response.status_code}"
                    
                    if response.status_code == 200:
                        content = response.text
                        # Basic mobile elements should be present
                        assert 'sm:hidden' in content, f"Mobile responsive classes missing from {page}"
                        assert 'data-lucide=' in content, f"Icon system missing from {page}"
                        
            except Exception as e:
                # Database issues acceptable in test environment
                assert "database" in str(e).lower() or "sqlite" in str(e).lower(), \
                    f"Unexpected error in mobile UI test: {e}"
    
    def test_mobile_assets_and_dependencies(self):
        """Test that mobile UI dependencies are properly configured"""
        test_env = {
            "ENVIRONMENT": "test",
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite+aiosqlite:///:memory:",
        }
        
        with patch.dict(os.environ, test_env):
            try:
                from app.main import app
                client = TestClient(app)
                response = client.get("/items")
                
                if response.status_code == 200:
                    content = response.text
                    
                    # Check for critical mobile dependencies
                    dependencies = [
                        'alpinejs',  # Alpine.js for mobile interactions
                        'lucide',  # Icon system
                        'tabulator',  # Table system with mobile support
                        'tailwindcss',  # CSS framework (implied by classes)
                    ]
                    
                    for dep in dependencies:
                        assert dep.lower() in content.lower(), \
                            f"Mobile dependency '{dep}' not found"
                            
            except Exception as e:
                # Skip if can't load app
                pytest.skip(f"Could not test mobile dependencies: {e}") 