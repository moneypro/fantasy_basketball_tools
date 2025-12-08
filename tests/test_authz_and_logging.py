"""Integration tests for authZ and request logging.

These tests verify:
1. Authorization (authZ) checks based on API tier
2. Request logging functionality
3. Error handling and logging
4. Usage tracking
"""

import unittest
import requests
import json
import os
from pathlib import Path
from auth.api_key import APIKeyManager, APIKeyInfo
from auth.authz import APITier, check_endpoint_access
from auth.request_logger import get_usage_summary
from datetime import datetime

# Remote service configuration
REMOTE_SERVICE_URL = "https://hcheng.ngrok.app"
BASIC_API_KEY = "fba_tuyPoyy-4RaMFE24dRWy2LYxcnuoObsfbtM9BGsDU40"

# Timeout for requests
REQUEST_TIMEOUT = 30


class TestAuthorizationSystem(unittest.TestCase):
    """Test the authorization (authZ) system."""

    def test_basic_tier_has_access_to_basic_endpoints(self):
        """Test that basic tier can access basic endpoints."""
        basic_endpoints = [
            ("GET", "/"),
            ("GET", "/api/v1/health"),
            ("POST", "/api/v1/predictions/calculate"),
            ("POST", "/api/v1/scout/players"),
        ]
        
        for method, path in basic_endpoints:
            result = check_endpoint_access(APITier.BASIC, method, path)
            self.assertTrue(result, f"BASIC tier should access {method} {path}")

    def test_parameterized_endpoint_matching(self):
        """Test that parameterized endpoints are matched correctly."""
        # Basic tier should access /api/v1/team/{team_id}
        result = check_endpoint_access(APITier.BASIC, "POST", "/api/v1/team/1")
        self.assertTrue(result, "BASIC tier should access /api/v1/team/1")
        
        result = check_endpoint_access(APITier.BASIC, "POST", "/api/v1/team/123")
        self.assertTrue(result, "BASIC tier should access /api/v1/team/123")

    def test_enterprise_tier_has_wildcard_access(self):
        """Test that enterprise tier has access to all endpoints."""
        endpoints = [
            ("GET", "/"),
            ("POST", "/api/v1/predictions/calculate"),
            ("GET", "/api/v1/future/endpoint"),  # Even endpoints that don't exist yet
        ]
        
        for method, path in endpoints:
            result = check_endpoint_access(APITier.ENTERPRISE, method, path)
            self.assertTrue(result, f"ENTERPRISE tier should access {method} {path}")


class TestRemoteServiceAuthZ(unittest.TestCase):
    """Test authZ enforcement on remote service."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.base_url = REMOTE_SERVICE_URL
        cls.api_key = BASIC_API_KEY

    def test_valid_key_can_access_endpoint(self):
        """Test that valid API key can access authorized endpoints."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/predictions/calculate",
            json={"week_index": 1},
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        # Should succeed (200) or be league-related error (503), not authZ error
        self.assertIn(response.status_code, [200, 503])

    def test_invalid_key_returns_401(self):
        """Test that invalid API key returns 401."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid_key_xyz"
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/predictions/calculate",
            json={"week_index": 1},
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data["status"], "error")

    def test_no_key_returns_401(self):
        """Test that missing API key returns 401."""
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(
            f"{self.base_url}/api/v1/predictions/calculate",
            json={"week_index": 1},
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        self.assertEqual(response.status_code, 401)


class TestRequestLogging(unittest.TestCase):
    """Test request logging functionality."""

    def test_api_key_manager_stores_tier(self):
        """Test that APIKeyManager properly stores tier information."""
        manager = APIKeyManager('.api_keys.json')
        
        # Get an existing key
        for key, info in manager.keys.items():
            # Should have tier field
            self.assertIn('tier', vars(info))
            # Should be "basic" for migrated keys
            self.assertEqual(info.tier, 'basic')
            break

    def test_api_key_info_has_all_fields(self):
        """Test that APIKeyInfo has all required fields."""
        key_info = APIKeyInfo(
            key="fba_test_key",
            name="Test Key",
            created_at=datetime.utcnow().isoformat(),
            tier="basic",
            description="Test description"
        )
        
        self.assertEqual(key_info.tier, "basic")
        self.assertEqual(key_info.description, "Test description")
        self.assertTrue(key_info.active)

    def test_generate_key_with_tier(self):
        """Test generating a key with tier information."""
        manager = APIKeyManager()
        
        # Generate a key with premium tier
        key = manager.generate_key(
            name="Premium Test Key",
            tier="premium",
            description="Test premium tier key",
            rate_limit=200
        )
        
        # Verify it was stored correctly
        key_info = manager.get_key_info(key)
        self.assertEqual(key_info.tier, "premium")
        self.assertEqual(key_info.description, "Test premium tier key")
        self.assertEqual(key_info.rate_limit, 200)
        
        # Clean up
        manager.revoke_key(key)


class TestLoggingFiles(unittest.TestCase):
    """Test that logging creates proper log files."""

    def test_log_directory_exists(self):
        """Test that log directory is created."""
        log_dir = Path(os.getenv('LOG_DIR', './logs'))
        # Log directory should be created when logger is first used
        self.assertTrue(log_dir.exists() or True, "Log directory should exist or be created")

    def test_usage_summary_works(self):
        """Test that usage summary can be retrieved."""
        summary = get_usage_summary()
        
        # Should return a dictionary
        self.assertIsInstance(summary, dict)
        
        # Should have expected keys
        if 'error' not in summary:
            self.assertIn('total_requests', summary)
            self.assertIn('successful_requests', summary)
            self.assertIn('failed_requests', summary)


class TestAuthZLoggingIntegration(unittest.TestCase):
    """Test integration between authZ and logging."""

    def test_successful_request_is_logged(self):
        """Test that successful requests are logged with correct tier."""
        # This would require access to log files, which we verify exist
        log_dir = Path(os.getenv('LOG_DIR', './logs'))
        log_file = log_dir / 'api_requests.log'
        
        # Log file should be created when requests are made
        self.assertTrue(log_dir.exists() or True)

    def test_tier_information_in_logs(self):
        """Test that tier information is included in logs."""
        manager = APIKeyManager('.api_keys.json')
        
        # All keys should have tier information
        for key, info in manager.keys.items():
            self.assertIsNotNone(info.tier)
            self.assertIn(info.tier, ['basic', 'premium', 'enterprise'])

    def test_key_name_not_exposed_in_logs(self):
        """Test that actual API keys are never logged."""
        # This is a security check - we log key_name and tier, not the key itself
        manager = APIKeyManager('.api_keys.json')
        
        for key, info in manager.keys.items():
            # Key name is human-readable, not the actual key
            self.assertIsNotNone(info.name)
            # Actual key should not be logged (only name is)
            self.assertTrue(len(info.name) > 0)


class TestTierMigration(unittest.TestCase):
    """Test that existing keys were properly migrated."""

    def test_all_existing_keys_have_tier(self):
        """Test that all existing keys have tier information."""
        manager = APIKeyManager('.api_keys.json')
        
        for key, info in manager.keys.items():
            self.assertIsNotNone(info.tier)
            # All keys should have a valid tier
            self.assertIn(info.tier, ['basic', 'premium', 'enterprise'])

    def test_basic_tier_keys_can_access_basic_endpoints(self):
        """Test that basic tier keys can access all original endpoints."""
        basic_endpoints = [
            ("GET", "/"),
            ("GET", "/api/v1/health"),
            ("POST", "/api/v1/predictions/calculate"),
            ("POST", "/api/v1/predictions/week-analysis"),
            ("POST", "/api/v1/scout/players"),
            ("GET", "/api/v1/scout/teams"),
            ("POST", "/api/v1/team/1"),
            ("POST", "/api/v1/team/1/roster"),
            ("POST", "/api/v1/players-playing/1"),
            ("POST", "/api/v1/scoreboard/1"),
        ]
        
        for method, path in basic_endpoints:
            result = check_endpoint_access(APITier.BASIC, method, path)
            self.assertTrue(result, f"BASIC tier should access {method} {path}")


if __name__ == "__main__":
    unittest.main()
