"""Unit tests for common.week module"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from common.week import Week


class TestWeek(unittest.TestCase):
    """Test cases for Week class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_league = Mock()
        self.mock_league._get_pro_schedule = Mock(return_value={
            1: 'team1', 2: 'team2', 3: 'team3'
        })

    def test_week_init_week_1(self):
        """Test Week initialization for week 1"""
        week = Week(self.mock_league, 1)
        self.assertEqual(week.scoring_period, (0, 7))
        self.assertEqual(week.league, self.mock_league)

    def test_week_init_week_2(self):
        """Test Week initialization for week 2"""
        week = Week(self.mock_league, 2)
        self.assertEqual(week.scoring_period, (7, 13))

    def test_week_init_week_3(self):
        """Test Week initialization for week 3"""
        week = Week(self.mock_league, 3)
        self.assertEqual(week.scoring_period, (14, 20))

    def test_match_up_week_to_scoring_period_convert_week_1(self):
        """Test scoring period conversion for week 1"""
        result = Week._match_up_week_to_scoring_period_convert(1)
        self.assertEqual(result, (0, 7))

    def test_match_up_week_to_scoring_period_convert_week_2(self):
        """Test scoring period conversion for week 2"""
        result = Week._match_up_week_to_scoring_period_convert(2)
        self.assertEqual(result, (7, 13))

    def test_match_up_week_to_scoring_period_convert_week_10(self):
        """Test scoring period conversion for week 10"""
        result = Week._match_up_week_to_scoring_period_convert(10)
        self.assertEqual(result, (63, 69))

    @patch('common.week.PRO_TEAM_MAP')
    def test_get_team_game_list(self, mock_pro_team_map):
        """Test _get_team_game_list method"""
        mock_pro_team_map.__getitem__.side_effect = lambda x: f'TEAM{x}'
        # Return same data for all 8 calls (for week 1, scoring periods 0-7)
        self.mock_league._get_pro_schedule.return_value = {1: 'dummy', 2: 'dummy'}
        
        week = Week(self.mock_league, 1)
        # The method should return a list of lists
        self.assertIsInstance(week.team_game_list, list)
        self.assertEqual(len(week.team_game_list), 8)  # week 1 has 8 days

    def test_cumulate_number_of_games_basic(self):
        """Test cumulate_number_of_games with basic input"""
        week = Week(self.mock_league, 1)
        week.team_game_list = [
            ['LAL', 'GSW', 'BOS'],
            ['LAL', 'MIA'],
            ['GSW', 'BOS']
        ]
        
        result = week.cumulate_number_of_games()
        self.assertEqual(result['LAL'], 2)
        self.assertEqual(result['GSW'], 2)
        self.assertEqual(result['BOS'], 2)
        self.assertEqual(result['MIA'], 1)

    def test_cumulate_number_of_games_single_game(self):
        """Test cumulate_number_of_games with single game"""
        week = Week(self.mock_league, 1)
        week.team_game_list = [
            ['LAL']
        ]
        
        result = week.cumulate_number_of_games()
        self.assertEqual(result, {'LAL': 1})

    def test_cumulate_number_of_games_no_games(self):
        """Test cumulate_number_of_games with no games"""
        week = Week(self.mock_league, 1)
        week.team_game_list = [[]]
        
        result = week.cumulate_number_of_games()
        self.assertEqual(result, {})

    def test_create_factory_method_with_week(self):
        """Test create factory method with explicit week"""
        week = Week.create(self.mock_league, 5)
        self.assertEqual(week.scoring_period, (28, 34))

    def test_create_factory_method_with_none(self):
        """Test create factory method with None uses current matchup period"""
        self.mock_league.currentMatchupPeriod = 3
        week = Week.create(self.mock_league, None)
        self.assertEqual(week.scoring_period, (14, 20))


if __name__ == '__main__':
    unittest.main()
