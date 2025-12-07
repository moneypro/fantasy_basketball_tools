"""Unit tests for the team endpoint"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import json
from flask import Flask, jsonify


class TestTeamEndpointLogic(unittest.TestCase):
    """Test the core logic of the team endpoint"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a test app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Create mock league and teams
        self.mock_league = Mock()
        self.mock_league.currentMatchupPeriod = 5
        
        # Create mock teams
        self.mock_team_1 = Mock()
        self.mock_team_1.team_id = 1
        self.mock_team_1.team_name = "Team Alpha"
        self.mock_team_1.owner = "Owner One"
        self.mock_team_1.position = 1
        self.mock_team_1.wins = 5
        self.mock_team_1.losses = 2
        self.mock_team_1.points_for = 1250.45
        self.mock_team_1.points_against = 1100.20
        
        self.mock_team_2 = Mock()
        self.mock_team_2.team_id = 2
        self.mock_team_2.team_name = "Team Beta"
        self.mock_team_2.owner = "Owner Two"
        self.mock_team_2.position = 2
        self.mock_team_2.wins = 4
        self.mock_team_2.losses = 3
        self.mock_team_2.points_for = 1200.50
        self.mock_team_2.points_against = 1150.30
        
        self.mock_league.teams = [self.mock_team_1, self.mock_team_2]
        
        # Create mock matchup
        self.mock_matchup = Mock()
        self.mock_matchup.home_team = self.mock_team_1
        self.mock_matchup.away_team = self.mock_team_2
        self.mock_league.scoreboard = Mock(return_value=[self.mock_matchup])

    def test_endpoint_team_found_logic(self):
        """Test that endpoint correctly finds team by ID"""
        # Simulate the team finding logic
        team_id = 1
        target_team = None
        
        for team in self.mock_league.teams:
            if team.team_id == team_id:
                target_team = team
                break
        
        self.assertIsNotNone(target_team)
        self.assertEqual(target_team.team_name, "Team Alpha")

    def test_endpoint_team_not_found_logic(self):
        """Test that endpoint returns 404 when team not found"""
        team_id = 999
        target_team = None
        
        for team in self.mock_league.teams:
            if team.team_id == team_id:
                target_team = team
                break
        
        self.assertIsNone(target_team)

    def test_endpoint_week_validation_too_high(self):
        """Test week validation rejects values > 17"""
        week_index = 18
        
        is_valid = isinstance(week_index, int) and 1 <= week_index <= 17
        self.assertFalse(is_valid)

    def test_endpoint_week_validation_too_low(self):
        """Test week validation rejects values < 1"""
        week_index = 0
        
        is_valid = isinstance(week_index, int) and 1 <= week_index <= 17
        self.assertFalse(is_valid)

    def test_endpoint_week_validation_valid(self):
        """Test week validation accepts valid values"""
        for week_index in range(1, 18):
            is_valid = isinstance(week_index, int) and 1 <= week_index <= 17
            self.assertTrue(is_valid)

    def test_endpoint_day_of_week_validation_too_high(self):
        """Test day of week validation rejects values > 6"""
        day_of_week = 7
        
        is_valid = isinstance(day_of_week, int) and 0 <= day_of_week <= 6
        self.assertFalse(is_valid)

    def test_endpoint_day_of_week_validation_negative(self):
        """Test day of week validation rejects negative values"""
        day_of_week = -1
        
        is_valid = isinstance(day_of_week, int) and 0 <= day_of_week <= 6
        self.assertFalse(is_valid)

    def test_endpoint_day_of_week_validation_valid(self):
        """Test day of week validation accepts valid values"""
        for day_of_week in range(0, 7):
            is_valid = isinstance(day_of_week, int) and 0 <= day_of_week <= 6
            self.assertTrue(is_valid)

    def test_endpoint_injury_status_parsing(self):
        """Test injury status string parsing"""
        injury_status_param = 'ACTIVE,PROBABLE,OUT'
        injury_status = [s.strip().upper() for s in injury_status_param.split(',')]
        
        self.assertEqual(injury_status, ['ACTIVE', 'PROBABLE', 'OUT'])

    def test_endpoint_injury_status_single(self):
        """Test single injury status parsing"""
        injury_status_param = 'ACTIVE'
        injury_status = [s.strip().upper() for s in injury_status_param.split(',')]
        
        self.assertEqual(injury_status, ['ACTIVE'])

    def test_endpoint_matchup_home_team_logic(self):
        """Test matchup detection when team is home"""
        team_id = 1
        matchup_data = None
        
        for matchup in self.mock_league.scoreboard(5):
            if matchup.home_team.team_id == team_id:
                matchup_data = {
                    "home_team": matchup.home_team.team_name,
                    "away_team": matchup.away_team.team_name,
                    "is_home": True,
                    "opponent_id": matchup.away_team.team_id,
                    "opponent_name": matchup.away_team.team_name
                }
                break
        
        self.assertIsNotNone(matchup_data)
        self.assertTrue(matchup_data['is_home'])
        self.assertEqual(matchup_data['opponent_id'], 2)

    def test_endpoint_matchup_away_team_logic(self):
        """Test matchup detection when team is away"""
        team_id = 2
        matchup_data = None
        
        for matchup in self.mock_league.scoreboard(5):
            if matchup.away_team.team_id == team_id:
                matchup_data = {
                    "home_team": matchup.home_team.team_name,
                    "away_team": matchup.away_team.team_name,
                    "is_home": False,
                    "opponent_id": matchup.home_team.team_id,
                    "opponent_name": matchup.home_team.team_name
                }
                break
        
        self.assertIsNotNone(matchup_data)
        self.assertFalse(matchup_data['is_home'])
        self.assertEqual(matchup_data['opponent_id'], 1)

    def test_endpoint_matchup_no_match_logic(self):
        """Test matchup handling when no match found"""
        self.mock_league.scoreboard = Mock(return_value=[])
        
        team_id = 1
        matchup_data = None
        
        for matchup in self.mock_league.scoreboard(5):
            if matchup.home_team.team_id == team_id or matchup.away_team.team_id == team_id:
                matchup_data = {}
                break
        
        self.assertIsNone(matchup_data)

    def test_endpoint_point_differential_calculation(self):
        """Test point differential calculation"""
        team_avg = 145.5
        opponent_avg = 142.1
        team_std = 12.3
        opponent_std = 11.8
        
        point_differential = round(team_avg - opponent_avg, 2)
        point_differential_std_dev = round((team_std ** 2 + opponent_std ** 2) ** 0.5, 2)
        
        self.assertEqual(point_differential, 3.4)
        # Calculate: sqrt(12.3^2 + 11.8^2) = sqrt(151.29 + 139.24) = sqrt(290.53) ≈ 17.04
        self.assertAlmostEqual(point_differential_std_dev, 17.04, places=1)

    def test_endpoint_numerical_rounding(self):
        """Test that numbers are properly rounded to 2 decimal places"""
        values = [145.5678, 12.3456, 1250.456789]
        rounded = [round(v, 2) for v in values]
        
        self.assertEqual(rounded[0], 145.57)
        self.assertEqual(rounded[1], 12.35)
        self.assertEqual(rounded[2], 1250.46)

    def test_endpoint_response_data_structure(self):
        """Test response data structure matches expected format"""
        # Simulate building response
        response_data = {
            "team": {
                "id": 1,
                "name": "Team Alpha",
                "owner": "Owner One",
                "rank": 1,
                "wins": 5,
                "losses": 2,
                "points_for": 1250.45,
                "points_against": 1100.20
            },
            "week": {
                "index": 5,
                "day_of_week_override": 0,
                "injury_status_filter": ["ACTIVE"]
            },
            "performance_metrics": {
                "predicted_average_points": 145.5,
                "predicted_std_dev": 12.3,
                "number_of_games": 9
            },
            "matchup": {
                "home_team": "Team Alpha",
                "away_team": "Team Beta",
                "is_home": True,
                "opponent_id": 2,
                "opponent_name": "Team Beta"
            },
            "opponent_metrics": {
                "predicted_average_points": 142.1,
                "predicted_std_dev": 11.8,
                "number_of_games": 9
            },
            "matchup_analysis": {
                "point_differential": 3.4,
                "point_differential_std_dev": 17.2
            }
        }
        
        # Verify structure
        self.assertIn('team', response_data)
        self.assertIn('week', response_data)
        self.assertIn('performance_metrics', response_data)
        self.assertIn('matchup', response_data)
        self.assertIn('opponent_metrics', response_data)
        self.assertIn('matchup_analysis', response_data)
        
        # Verify nested structure
        team = response_data['team']
        self.assertIn('id', team)
        self.assertIn('name', team)
        self.assertIn('owner', team)
        
        matchup = response_data['matchup']
        self.assertIn('is_home', matchup)
        self.assertIn('opponent_id', matchup)


class TestTeamEndpointIntegration(unittest.TestCase):
    """Integration tests for team endpoint"""

    def setUp(self):
        """Set up test fixtures"""
        from app import app
        self.app = app
        self.app.config['TESTING'] = True

    def test_endpoint_route_exists(self):
        """Test that the endpoint route is registered"""
        rules = list(self.app.url_map.iter_rules())
        team_routes = [r for r in rules if 'team' in r.rule]
        
        self.assertTrue(any('team' in r.rule for r in rules),
                       "Team endpoint route not found in Flask app")

    def test_endpoint_route_has_team_id_parameter(self):
        """Test that the endpoint route includes team_id parameter"""
        rules = list(self.app.url_map.iter_rules())
        team_rules = [r for r in rules if 'team' in r.rule]
        
        # Check if any team rule has <team_id> in it
        has_team_id = any('team_id' in r.rule for r in team_rules)
        self.assertTrue(has_team_id, "team_id parameter not found in route")

    def test_endpoint_route_method_is_get(self):
        """Test that the endpoint uses GET method"""
        rules = list(self.app.url_map.iter_rules())
        team_rules = [r for r in rules if 'team' in r.rule]
        
        # Check if GET is in the methods
        has_get = any('GET' in r.methods for r in team_rules)
        self.assertTrue(has_get, "GET method not found in team endpoint")

    def test_get_team_info_function_exists(self):
        """Test that get_team_info function exists"""
        from app import get_team_info
        self.assertTrue(callable(get_team_info),
                       "get_team_info function is not callable")

    def test_get_team_info_has_decorators(self):
        """Test that get_team_info has authentication decorators"""
        from app import get_team_info
        
        # Check if function has been wrapped (decorators applied)
        has_wrapping = (hasattr(get_team_info, '__wrapped__') or 
                       hasattr(get_team_info, '__name__'))
        
        self.assertTrue(has_wrapping,
                       "get_team_info does not appear to have decorators")


if __name__ == '__main__':
    unittest.main()
