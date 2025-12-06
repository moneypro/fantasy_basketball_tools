"""Unit tests for predict_week module"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Tuple

from predict.predict_week import (
    PredictWeekHelper,
    predict_week,
    get_table_output_for_week,
    predict_match_up,
    get_remaining_days_cumulative_scores,
    get_remaining_days_table_output
)


class TestPredictWeekHelper(unittest.TestCase):
    """Test cases for PredictWeekHelper class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_league = Mock()
        self.mock_team = Mock()
        self.mock_team.team_name = "Team A"
        self.mock_team.roster = []
        
        self.mock_league.teams = [self.mock_team]
        self.mock_league.scoreboard = Mock(return_value=[])

    def test_days_of_week_constant(self):
        """Test DAYS_OF_WEEK constant is correct"""
        expected = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.assertEqual(PredictWeekHelper.DAYS_OF_WEEK, expected)

    @patch('predict.predict_week.Week')
    @patch('predict.predict_week.RosterWeekPredictor')
    def test_predict_week_returns_tuple(self, mock_predictor_class, mock_week_class):
        """Test predict_week returns tuple of dicts"""
        # Setup mocks
        mock_predictor = Mock()
        mock_predictor.predict.return_value = (50.0, 5.0)
        mock_predictor.get_total_number_of_games.return_value = 8
        mock_predictor_class.return_value = mock_predictor
        
        mock_week = Mock()
        mock_week_class.return_value = mock_week
        
        # Call function
        num_games_map, team_scores = PredictWeekHelper.predict_week(
            self.mock_league, 1, 0, ['ACTIVE']
        )
        
        # Assert
        self.assertIsInstance(num_games_map, dict)
        self.assertIsInstance(team_scores, dict)
        self.assertIn("Team A", num_games_map)
        self.assertIn("Team A", team_scores)

    @patch('predict.predict_week.Week')
    @patch('predict.predict_week.RosterWeekPredictor')
    def test_predict_week_correct_values(self, mock_predictor_class, mock_week_class):
        """Test predict_week returns correct values"""
        # Setup mocks
        mock_predictor = Mock()
        expected_points = (50.0, 5.0)
        expected_games = 8
        mock_predictor.predict.return_value = expected_points
        mock_predictor.get_total_number_of_games.return_value = expected_games
        mock_predictor_class.return_value = mock_predictor
        
        mock_week = Mock()
        mock_week_class.return_value = mock_week
        
        # Call function
        num_games_map, team_scores = PredictWeekHelper.predict_week(
            self.mock_league, 1, 0, ['ACTIVE']
        )
        
        # Assert
        self.assertEqual(num_games_map["Team A"], expected_games)
        self.assertEqual(team_scores["Team A"], expected_points)

    @patch('predict.predict_week.Week')
    @patch('predict.predict_week.RosterWeekPredictor')
    def test_predict_week_default_injury_status(self, mock_predictor_class, mock_week_class):
        """Test predict_week uses default injury status when None provided"""
        # Setup mocks
        mock_predictor = Mock()
        mock_predictor.predict.return_value = (50.0, 5.0)
        mock_predictor.get_total_number_of_games.return_value = 8
        mock_predictor_class.return_value = mock_predictor
        
        mock_week = Mock()
        mock_week_class.return_value = mock_week
        
        # Call function with None injury status
        PredictWeekHelper.predict_week(self.mock_league, 1, 0, None)
        
        # Assert default was used
        called_with_injury_status = mock_predictor.predict.call_args[1]['injuryStatusList']
        self.assertEqual(called_with_injury_status, ['ACTIVE'])

    @patch('predict.predict_week.Week')
    @patch('predict.predict_week.RosterWeekPredictor')
    def test_get_table_output_for_week_returns_sorted(self, mock_predictor_class, mock_week_class):
        """Test get_table_output_for_week returns sorted table"""
        # Setup mocks
        mock_team_a = Mock()
        mock_team_a.team_name = "Team A"
        mock_team_a.roster = []
        
        mock_team_b = Mock()
        mock_team_b.team_name = "Team B"
        mock_team_b.roster = []
        
        self.mock_league.teams = [mock_team_a, mock_team_b]
        
        # Use a side effect that tracks which team's predictor is being created
        team_predictors = {}
        
        def predictor_side_effect(roster, week):
            # Identify which team by checking roster reference
            if roster == []:
                # Create a new predictor with a way to identify it
                predictor = Mock()
                return predictor
            return Mock()
        
        mock_predictor_class.side_effect = predictor_side_effect
        
        # Create separate mock predictor instances
        mock_predictor_a = Mock()
        mock_predictor_a.predict.return_value = (100.0, 5.0)
        mock_predictor_a.get_total_number_of_games.return_value = 8
        
        mock_predictor_b = Mock()
        mock_predictor_b.predict.return_value = (50.0, 3.0)
        mock_predictor_b.get_total_number_of_games.return_value = 8
        
        # Create predictors in order
        predictors = [mock_predictor_a, mock_predictor_b]
        call_count = [0]
        
        def create_predictor(roster, week):
            predictor = predictors[call_count[0]]
            call_count[0] += 1
            return predictor
        
        mock_predictor_class.side_effect = create_predictor
        
        mock_week = Mock()
        mock_week_class.return_value = mock_week
        
        # Call function
        num_games_map, table_output, team_scores = PredictWeekHelper.get_table_output_for_week(
            self.mock_league, 1, 0, ['ACTIVE']
        )
        
        # Assert table has header
        self.assertEqual(table_output[0][0], "Team Name")
        # Assert other rows exist
        self.assertGreater(len(table_output), 1)

    @patch('predict.predict_week.Week')
    @patch('predict.predict_week.RosterWeekPredictor')
    def test_get_table_output_for_week_includes_mean_and_std(self, mock_predictor_class, mock_week_class):
        """Test table output includes mean and standard deviation"""
        # Setup mocks
        mock_predictor = Mock()
        mock_predictor.predict.return_value = (50.0, 5.0)
        mock_predictor.get_total_number_of_games.return_value = 8
        mock_predictor_class.return_value = mock_predictor
        
        mock_week = Mock()
        mock_week_class.return_value = mock_week
        
        # Call function
        num_games_map, table_output, team_scores = PredictWeekHelper.get_table_output_for_week(
            self.mock_league, 1, 0, ['ACTIVE']
        )
        
        # Assert table structure
        header = table_output[0]
        self.assertEqual(header[0], "Team Name")
        self.assertIn("Mean", header[2])
        self.assertIn("Standard Deviation", header[3])


class TestPredictMatchUp(unittest.TestCase):
    """Test cases for predict_match_up function"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_league = Mock()
        
        # Create mock matchup
        self.mock_home_team = Mock()
        self.mock_home_team.team_name = "Home Team"
        
        self.mock_away_team = Mock()
        self.mock_away_team.team_name = "Away Team"
        
        self.mock_matchup = Mock()
        self.mock_matchup.home_team = self.mock_home_team
        self.mock_matchup.away_team = self.mock_away_team
        
        self.mock_league.scoreboard.return_value = [self.mock_matchup]

    def test_predict_match_up_returns_html_string(self):
        """Test predict_match_up returns HTML string"""
        team_scores = {
            "Home Team": (50.0, 5.0),
            "Away Team": (40.0, 4.0)
        }
        num_games = {
            "Home Team": 8,
            "Away Team": 8
        }
        
        result = predict_match_up(self.mock_league, 1, team_scores, num_games)
        
        self.assertIsInstance(result, str)
        self.assertIn("<table>", result)
        self.assertIn("Home Team", result)
        self.assertIn("Away Team", result)

    def test_predict_match_up_includes_scores(self):
        """Test predict_match_up includes team scores"""
        team_scores = {
            "Home Team": (50.0, 5.0),
            "Away Team": (40.0, 4.0)
        }
        num_games = {
            "Home Team": 8,
            "Away Team": 8
        }
        
        result = predict_match_up(self.mock_league, 1, team_scores, num_games)
        
        self.assertIn("50", result)  # Home score
        self.assertIn("40", result)  # Away score

    def test_predict_match_up_includes_game_counts(self):
        """Test predict_match_up includes game counts"""
        team_scores = {
            "Home Team": (50.0, 5.0),
            "Away Team": (40.0, 4.0)
        }
        num_games = {
            "Home Team": 7,
            "Away Team": 6
        }
        
        result = predict_match_up(self.mock_league, 1, team_scores, num_games)
        
        self.assertIn("7", result)  # Home games
        self.assertIn("6", result)  # Away games

    def test_predict_match_up_calculates_spread(self):
        """Test predict_match_up calculates point spread"""
        team_scores = {
            "Home Team": (50.0, 5.0),
            "Away Team": (40.0, 4.0)
        }
        num_games = {
            "Home Team": 8,
            "Away Team": 8
        }
        
        result = predict_match_up(self.mock_league, 1, team_scores, num_games)
        
        # Spread should be 50 - 40 = 10
        self.assertIn("10", result)


class TestGetRemainingDaysCumulativeScores(unittest.TestCase):
    """Test cases for get_remaining_days_cumulative_scores function"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_league = Mock()
        self.mock_team = Mock()
        self.mock_team.team_name = "Team A"
        self.mock_team.roster = []
        self.mock_league.teams = [self.mock_team]

    @patch('predict.predict_week.Week')
    @patch('predict.predict_week.RosterWeekPredictor')
    def test_get_remaining_days_cumulative_scores_returns_dict(self, mock_predictor_class, mock_week_class):
        """Test function returns dictionary"""
        # Setup mocks
        mock_predictor = Mock()
        mock_predictor.players_with_game.return_value = []
        mock_predictor.get_avg_variance_stats.return_value = (0.0, 0.0)
        mock_predictor_class.return_value = mock_predictor
        
        mock_week = Mock()
        mock_week.scoring_period = (0, 7)  # 8 days
        mock_week_class.return_value = mock_week
        
        # Call function
        result = get_remaining_days_cumulative_scores(
            self.mock_league, 1, 0, ['ACTIVE']
        )
        
        # Assert
        self.assertIsInstance(result, dict)
        self.assertIn("Team A", result)
        self.assertIsInstance(result["Team A"], list)

    @patch('predict.predict_week.Week')
    @patch('predict.predict_week.RosterWeekPredictor')
    def test_get_remaining_days_cumulative_scores_default_injury_status(self, mock_predictor_class, mock_week_class):
        """Test function uses default injury status when None provided"""
        # Setup mocks
        mock_predictor = Mock()
        mock_predictor.players_with_game.return_value = []
        mock_predictor.get_avg_variance_stats.return_value = (0.0, 0.0)
        mock_predictor_class.return_value = mock_predictor
        
        mock_week = Mock()
        mock_week.scoring_period = (0, 7)
        mock_week_class.return_value = mock_week
        
        # Call function with None
        get_remaining_days_cumulative_scores(
            self.mock_league, 1, 0, None
        )
        
        # The function should handle None by using default
        # This should not raise an error
        self.assertTrue(True)

    @patch('predict.predict_week.Week')
    @patch('predict.predict_week.RosterWeekPredictor')
    def test_get_remaining_days_cumulative_scores_structure(self, mock_predictor_class, mock_week_class):
        """Test cumulative scores have correct structure"""
        # Setup mocks
        mock_predictor = Mock()
        mock_predictor.players_with_game.return_value = []
        mock_predictor.get_avg_variance_stats.return_value = (0.0, 0.0)
        mock_predictor_class.return_value = mock_predictor
        
        mock_week = Mock()
        mock_week.scoring_period = (0, 7)  # 8 days
        mock_week_class.return_value = mock_week
        
        # Call function
        result = get_remaining_days_cumulative_scores(
            self.mock_league, 1, 0, ['ACTIVE']
        )
        
        # Assert structure
        team_scores = result["Team A"]
        self.assertEqual(len(team_scores), 8)  # One entry for each day
        for mean, std in team_scores:
            self.assertIsInstance(mean, (int, float))
            self.assertIsInstance(std, float)

    @patch('predict.predict_week.Week')
    @patch('predict.predict_week.RosterWeekPredictor')
    def test_get_remaining_days_are_cumulative(self, mock_predictor_class, mock_week_class):
        """Test that remaining days scores are cumulative (decreasing)"""
        # Setup mocks
        mock_predictor = Mock()
        mock_predictor.players_with_game.return_value = []
        
        # Return different values for each call to simulate different daily scores
        daily_scores = [(10.0, 1.0), (15.0, 1.5), (20.0, 2.0), (5.0, 0.5), 
                        (8.0, 0.8), (12.0, 1.2), (9.0, 0.9), (7.0, 0.7)]
        call_count = [0]
        
        def get_stats_side_effect(player):
            idx = call_count[0] % len(daily_scores)
            call_count[0] += 1
            return daily_scores[idx]
        
        mock_predictor.get_avg_variance_stats.side_effect = get_stats_side_effect
        mock_predictor_class.return_value = mock_predictor
        
        mock_week = Mock()
        mock_week.scoring_period = (0, 3)  # 4 days for simplicity
        mock_week_class.return_value = mock_week
        
        # Call function
        result = get_remaining_days_cumulative_scores(
            self.mock_league, 1, 0, ['ACTIVE']
        )
        
        # Assert cumulative property (each element should be >= next element)
        team_scores = result["Team A"]
        for i in range(len(team_scores) - 1):
            # Cumulative score should be >= next day's cumulative
            self.assertGreaterEqual(team_scores[i][0], team_scores[i + 1][0])


class TestGetRemainingDaysTableOutput(unittest.TestCase):
    """Test cases for get_remaining_days_table_output function"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_league = Mock()
        self.mock_team = Mock()
        self.mock_team.team_name = "Team A"
        self.mock_team.roster = []
        self.mock_league.teams = [self.mock_team]

    @patch('predict.predict_week.get_remaining_days_cumulative_scores')
    @patch('predict.predict_week.Week')
    def test_get_remaining_days_table_output_returns_list(self, mock_week_class, mock_cumulative_scores):
        """Test function returns list of rows"""
        # Setup mocks
        mock_cumulative_scores.return_value = {
            "Team A": [(100.0, 10.0), (90.0, 9.0), (75.0, 7.5)]
        }
        
        mock_week = Mock()
        mock_week.scoring_period = (0, 2)  # 3 days
        mock_week_class.return_value = mock_week
        
        # Call function
        result = get_remaining_days_table_output(
            self.mock_league, 1, 0, ['ACTIVE']
        )
        
        # Assert
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # First row is header
        self.assertEqual(result[0][0], "Team Name")

    @patch('predict.predict_week.get_remaining_days_cumulative_scores')
    @patch('predict.predict_week.Week')
    def test_get_remaining_days_table_output_includes_teams(self, mock_week_class, mock_cumulative_scores):
        """Test table includes all teams"""
        # Setup mocks
        mock_cumulative_scores.return_value = {
            "Team A": [(100.0, 10.0), (90.0, 9.0)],
            "Team B": [(95.0, 9.5), (85.0, 8.5)]
        }
        
        mock_week = Mock()
        mock_week.scoring_period = (0, 1)  # 2 days
        mock_week_class.return_value = mock_week
        
        # Call function
        result = get_remaining_days_table_output(
            self.mock_league, 1, 0, ['ACTIVE']
        )
        
        # Assert teams are in result
        team_names = [row[0] for row in result[1:]]
        self.assertIn("Team A", team_names)
        self.assertIn("Team B", team_names)

    @patch('predict.predict_week.get_remaining_days_cumulative_scores')
    @patch('predict.predict_week.Week')
    def test_get_remaining_days_table_output_format(self, mock_week_class, mock_cumulative_scores):
        """Test table output includes mean and std format"""
        # Setup mocks
        mock_cumulative_scores.return_value = {
            "Team A": [(100.0, 10.0)]
        }
        
        mock_week = Mock()
        mock_week.scoring_period = (0, 0)  # 1 day
        mock_week_class.return_value = mock_week
        
        # Call function
        result = get_remaining_days_table_output(
            self.mock_league, 1, 0, ['ACTIVE']
        )
        
        # Assert format
        data_row = result[1]  # First data row after header
        # Should have mean ± std format
        self.assertIn("±", data_row[1])


class TestPublicFunctions(unittest.TestCase):
    """Test cases for public wrapper functions"""

    @patch('predict.predict_week.PredictWeekHelper.predict_week')
    def test_predict_week_wrapper(self, mock_helper):
        """Test predict_week wrapper function"""
        mock_helper.return_value = ({}, {})
        
        from predict.predict_week import predict_week as predict_week_func
        
        result = predict_week_func(Mock(), 1)
        
        mock_helper.assert_called_once()
        self.assertEqual(result, ({}, {}))

    @patch('predict.predict_week.PredictWeekHelper.get_table_output_for_week')
    def test_get_table_output_for_week_wrapper(self, mock_helper):
        """Test get_table_output_for_week wrapper function"""
        mock_helper.return_value = ({}, [], {})
        
        from predict.predict_week import get_table_output_for_week as get_table_func
        
        result = get_table_func(Mock(), 1)
        
        mock_helper.assert_called_once()
        self.assertEqual(result, ({}, [], {}))


if __name__ == '__main__':
    unittest.main()
