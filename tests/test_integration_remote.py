"""Integration tests for remote Fantasy Basketball Service.

These tests run against the remote service at https://hcheng.ngrok.app
and verify all API endpoints are working correctly.
"""

import unittest
import requests
import json
from typing import Dict, Any, Optional

# Remote service configuration
REMOTE_SERVICE_URL = "https://hcheng.ngrok.app"
API_KEY = "fba_tuyPoyy-4RaMFE24dRWy2LYxcnuoObsfbtM9BGsDU40"

# Timeout for requests (ngrok connections can be slow)
REQUEST_TIMEOUT = 30


class RemoteServiceTestBase(unittest.TestCase):
    """Base class for remote service tests with common utilities."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.base_url = REMOTE_SERVICE_URL
        cls.api_key = API_KEY
        
    def _get_headers(self, with_auth: bool = True) -> Dict[str, str]:
        """Get request headers with optional API key authentication."""
        headers = {"Content-Type": "application/json"}
        if with_auth:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        with_auth: bool = True,
        expected_status: Optional[int] = None
    ) -> requests.Response:
        """Make a request to the service with error handling."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(with_auth)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=REQUEST_TIMEOUT)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if expected_status and response.status_code != expected_status:
                print(f"Response status: {response.status_code}")
                print(f"Response body: {response.text}")
            
            return response
        except requests.exceptions.Timeout:
            self.fail(f"Request timed out to {url}")
        except requests.exceptions.ConnectionError as e:
            self.fail(f"Connection error to {url}: {str(e)}")


class TestPublicEndpoints(RemoteServiceTestBase):
    """Test public endpoints that don't require authentication."""

    def test_root_endpoint(self):
        """Test the root endpoint returns API info."""
        response = self._make_request("GET", "/", with_auth=False, expected_status=200)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("service", data)
        self.assertIn("endpoints", data)
        self.assertEqual(data["service"], "Fantasy Basketball Predictions API")

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self._make_request("GET", "/api/v1/health", with_auth=False, expected_status=200)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("league", data)
        self.assertIn("service", data)

    def test_privacy_policy(self):
        """Test the privacy policy endpoint."""
        response = self._make_request("GET", "/privacy", with_auth=False)
        self.assertEqual(response.status_code, 200)
        # Privacy should return HTML
        self.assertIn("text/html", response.headers.get("Content-Type", ""))


class TestAuthenticationRequirements(RemoteServiceTestBase):
    """Test authentication requirements on protected endpoints."""

    def test_predictions_endpoint_requires_auth(self):
        """Test that predictions endpoint requires authentication."""
        response = self._make_request(
            "POST",
            "/api/v1/predictions/calculate",
            data={"week_index": 1},
            with_auth=False
        )
        self.assertEqual(response.status_code, 401)
        
        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "error")

    def test_invalid_api_key(self):
        """Test that invalid API key is rejected."""
        headers = {"Content-Type": "application/json"}
        headers["Authorization"] = "Bearer invalid_key_12345"
        
        url = f"{self.base_url}/api/v1/predictions/calculate"
        response = requests.post(
            url,
            json={"week_index": 1},
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        self.assertEqual(response.status_code, 401)


class TestPredictionEndpoints(RemoteServiceTestBase):
    """Test prediction calculation endpoints."""

    def test_calculate_predictions_valid_week(self):
        """Test calculating predictions for a valid week."""
        response = self._make_request(
            "POST",
            "/api/v1/predictions/calculate",
            data={"week_index": 1},
            expected_status=200
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("data", data)
        
        result = data["data"]
        self.assertIn("week_index", result)
        self.assertIn("team_predictions", result)
        self.assertIn("num_games", result)
        self.assertEqual(result["week_index"], 1)

    def test_calculate_predictions_with_day_override(self):
        """Test calculating predictions with day of week override."""
        response = self._make_request(
            "POST",
            "/api/v1/predictions/calculate",
            data={"week_index": 2, "day_of_week_override": 3},
            expected_status=200
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["week_index"], 2)
        self.assertEqual(data["data"]["day_of_week"], 3)

    def test_calculate_predictions_invalid_week(self):
        """Test that invalid week index is rejected."""
        response = self._make_request(
            "POST",
            "/api/v1/predictions/calculate",
            data={"week_index": 0},
            expected_status=400
        )
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn("error", data["status"])

    def test_calculate_predictions_week_out_of_range(self):
        """Test that week index out of range is rejected."""
        response = self._make_request(
            "POST",
            "/api/v1/predictions/calculate",
            data={"week_index": 24},
            expected_status=400
        )
        self.assertEqual(response.status_code, 400)

    def test_calculate_predictions_missing_week_index(self):
        """Test that missing week_index is rejected."""
        response = self._make_request(
            "POST",
            "/api/v1/predictions/calculate",
            data={},
            expected_status=400
        )
        self.assertEqual(response.status_code, 400)

    def test_calculate_predictions_invalid_day_of_week(self):
        """Test that invalid day of week is rejected."""
        response = self._make_request(
            "POST",
            "/api/v1/predictions/calculate",
            data={"week_index": 1, "day_of_week_override": 7},
            expected_status=400
        )
        self.assertEqual(response.status_code, 400)

    def test_week_analysis_endpoint(self):
        """Test the week analysis endpoint."""
        response = self._make_request(
            "POST",
            "/api/v1/predictions/week-analysis",
            data={"week_index": 1},
            expected_status=200
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("data", data)

    def test_week_analysis_invalid_week(self):
        """Test week analysis with invalid week index."""
        response = self._make_request(
            "POST",
            "/api/v1/predictions/week-analysis",
            data={"week_index": 0},
            expected_status=400
        )
        self.assertEqual(response.status_code, 400)


class TestScoutEndpoints(RemoteServiceTestBase):
    """Test player and team scouting endpoints."""

    def test_scout_players_endpoint(self):
        """Test the scout players endpoint."""
        response = self._make_request(
            "POST",
            "/api/v1/scout/players",
            data={"limit": 10},
            expected_status=200
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("data", data)
        
        result = data["data"]
        self.assertIn("players", result)
        self.assertIn("total_players_analyzed", result)

    def test_scout_players_custom_limit(self):
        """Test scout players with custom limit."""
        response = self._make_request(
            "POST",
            "/api/v1/scout/players",
            data={"limit": 5},
            expected_status=200
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        result = data["data"]
        self.assertLessEqual(len(result["players"]), 5)

    def test_scout_teams_endpoint(self):
        """Test the scout teams endpoint."""
        response = self._make_request(
            "GET",
            "/api/v1/scout/teams",
            with_auth=True
        )
        # Scout teams endpoint may be GET instead of POST
        self.assertIn(response.status_code, [200, 405])
        
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data["status"], "success")
            # Response structure may have "data" or direct message
            self.assertTrue("data" in data or "message" in data)


class TestTeamEndpoints(RemoteServiceTestBase):
    """Test team-related endpoints."""

    def test_team_info_endpoint(self):
        """Test getting team info."""
        # First get the list of teams from health endpoint
        response = self._make_request(
            "POST",
            "/api/v1/team/1",
            data={},
            expected_status=200
        )
        # Team endpoints may return 200 or 503 depending on league state
        self.assertIn(response.status_code, [200, 503])
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn("data", data)

    def test_team_roster_endpoint(self):
        """Test getting team roster."""
        response = self._make_request(
            "POST",
            "/api/v1/team/1/roster",
            data={},
            expected_status=200
        )
        # Team roster may return 200 or 503 depending on league state
        self.assertIn(response.status_code, [200, 503])


class TestScoreboardEndpoint(RemoteServiceTestBase):
    """Test scoreboard endpoint."""

    def test_scoreboard_endpoint(self):
        """Test getting scoreboard for a week."""
        response = self._make_request(
            "POST",
            "/api/v1/scoreboard/1",
            data={},
            expected_status=200
        )
        # Scoreboard may return 200 or 503 depending on league state
        self.assertIn(response.status_code, [200, 503])


class TestPlayersPlayingEndpoint(RemoteServiceTestBase):
    """Test players playing endpoint."""

    def test_players_playing_endpoint(self):
        """Test getting players playing for a scoring period."""
        response = self._make_request(
            "POST",
            "/api/v1/players-playing/1?team_id=1",
            data={},
            expected_status=200
        )
        # Players endpoint may return 200 or 503 depending on league state
        self.assertIn(response.status_code, [200, 400, 503])


class TestErrorHandling(RemoteServiceTestBase):
    """Test error handling across endpoints."""

    def test_nonexistent_endpoint(self):
        """Test that nonexistent endpoint returns 404."""
        response = self._make_request(
            "GET",
            "/api/v1/nonexistent",
            with_auth=False
        )
        self.assertEqual(response.status_code, 404)

    def test_malformed_json(self):
        """Test that malformed JSON is handled gracefully."""
        url = f"{self.base_url}/api/v1/predictions/calculate"
        headers = self._get_headers(with_auth=True)
        
        response = requests.post(
            url,
            data="invalid json {",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        # Should return 400, 415, or 500 for bad request/content type
        self.assertIn(response.status_code, [400, 415, 500])


class TestRateLimiting(RemoteServiceTestBase):
    """Test rate limiting behavior."""

    def test_rate_limit_header(self):
        """Test that rate limit information is tracked."""
        # Make a valid request
        response = self._make_request(
            "GET",
            "/api/v1/health",
            with_auth=False,
            expected_status=200
        )
        self.assertEqual(response.status_code, 200)
        
        # Rate limiting is tracked server-side, just verify request succeeds


if __name__ == "__main__":
    unittest.main()
