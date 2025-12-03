"""Extended unit tests for RosterWeekPredictor module"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import math
import statistics
from predict.internal.roster_week_predictor import RosterWeekPredictor
from common.week import Week


class TestRosterWeekPredictorStats(unittest.TestCase):
    """Test cases for RosterWeekPredictor statistical methods"""

    def test_get_fantasy_pts_complete_stats(self):
        """Test fantasy points calculation with complete stats"""
        stats = {
            'PTS': 20,
            '3PTM': 2,
            'FGA': 15,
            'FGM': 8,
            'FTA': 5,
            'FTM': 4,
            'REB': 5,
            'AST': 3,
            'STL': 1,
            'BLK': 1,
            'TO': 2
        }
        result = RosterWeekPredictor.get_fantasy_pts(stats)
        expected = 20 + 2 - 15 + 8*2 - 5 + 4 + 5 + 3*2 + 1*4 + 1*4 - 2*2
        self.assertEqual(result, expected)

    def test_get_fantasy_pts_missing_optional_stats(self):
        """Test fantasy points calculation with missing optional stats"""
        stats = {
            'PTS': 15,
            'FGA': 10,
            'FGM': 6,
            'FTA': 3,
            'FTM': 2,
            'REB': 4,
            'AST': 2,
            'TO': 1,
            'STL': 0,
            'BLK': 0
        }
        result = RosterWeekPredictor.get_fantasy_pts(stats)
        expected = 15 + 0 - 10 + 6*2 - 3 + 2 + 4 + 2*2 + 0*4 + 0*4 - 1*2
        self.assertEqual(result, expected)

    def test_get_stat_in_category_exists(self):
        """Test retrieving existing stat category"""
        stats = {'PTS': 20, '3PTM': 3, 'REB': 5}
        result = RosterWeekPredictor.get_stat_in_category(stats, 'PTS')
        self.assertEqual(result, 20)

    def test_get_stat_in_category_missing(self):
        """Test retrieving missing stat category returns 0"""
        stats = {'PTS': 20, 'REB': 5}
        result = RosterWeekPredictor.get_stat_in_category(stats, 'BLK')
        self.assertEqual(result, 0)

    def test_get_stat_from_stat_period_exists(self):
        """Test retrieving stat from existing period"""
        mock_player = Mock()
        mock_player.stats = {
            '2026_last_30': {
                'avg': {'PTS': 20, 'REB': 5, 'FGA': 10, 'FGM': 5, 'FTA': 2, 'FTM': 1, 'AST': 2, 'STL': 1, 'BLK': 1, 'TO': 1}
            }
        }
        result = RosterWeekPredictor.get_stat_from_stat_period(mock_player, '2026_last_30')
        self.assertIsNotNone(result)
        self.assertGreater(result, 0)

    def test_get_stat_from_stat_period_missing_period(self):
        """Test retrieving stat from missing period returns None"""
        mock_player = Mock()
        mock_player.stats = {}
        result = RosterWeekPredictor.get_stat_from_stat_period(mock_player, '2026_last_30')
        self.assertIsNone(result)

    def test_get_stat_from_stat_period_missing_avg(self):
        """Test retrieving stat when avg is missing returns None"""
        mock_player = Mock()
        mock_player.stats = {
            '2026_last_30': {}
        }
        result = RosterWeekPredictor.get_stat_from_stat_period(mock_player, '2026_last_30')
        self.assertIsNone(result)

    def test_get_avg_variance_stats_with_data(self):
        """Test average and variance calculation with available data"""
        mock_player = Mock()
        mock_player.stats = {
            '2026_last_30': {
                'avg': {'PTS': 20, 'REB': 5, 'FGA': 10, 'FGM': 5, 'FTA': 2, 'FTM': 1, 'AST': 2, 'STL': 1, 'BLK': 1, 'TO': 1}
            },
            '2026_last_15': {
                'avg': {'PTS': 22, 'REB': 6, 'FGA': 11, 'FGM': 6, 'FTA': 2, 'FTM': 1, 'AST': 2, 'STL': 1, 'BLK': 1, 'TO': 1}
            },
            '2026_last_7': {
                'avg': {'PTS': 18, 'REB': 4, 'FGA': 9, 'FGM': 4, 'FTA': 2, 'FTM': 1, 'AST': 2, 'STL': 1, 'BLK': 1, 'TO': 1}
            }
        }
        avg, var = RosterWeekPredictor.get_avg_variance_stats(mock_player)
        self.assertGreater(avg, 0)
        self.assertGreaterEqual(var, 0)

    def test_get_avg_variance_stats_no_data(self):
        """Test average and variance calculation with no data returns zeros"""
        mock_player = Mock()
        mock_player.stats = {}
        avg, var = RosterWeekPredictor.get_avg_variance_stats(mock_player)
        self.assertEqual(avg, 0)
        self.assertEqual(var, 0)

    def test_get_avg_variance_stats_single_data_point(self):
        """Test variance with single data point is 0"""
        mock_player = Mock()
        mock_player.stats = {
            '2026_last_30': {
                'avg': {'PTS': 20, 'REB': 5, 'FGA': 10, 'FGM': 5, 'FTA': 2, 'FTM': 1, 'AST': 2, 'STL': 1, 'BLK': 1, 'TO': 1}
            }
        }
        avg, var = RosterWeekPredictor.get_avg_variance_stats(mock_player)
        self.assertGreater(avg, 0)
        self.assertEqual(var, 0.0)


class TestRosterWeekPredictorMethods(unittest.TestCase):
    """Test cases for RosterWeekPredictor instance methods"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_league = Mock()
        self.mock_week = Mock(spec=Week)
        self.mock_week.scoring_period = (0, 7)
        self.mock_week.team_game_list = [
            ['LAL', 'GSW'],
            ['LAL', 'MIA'],
            ['BOS', 'GSW'],
            ['LAL'],
            ['MIA'],
            ['BOS'],
            ['GSW'],
            ['MIA']
        ]

    def test_init(self):
        """Test RosterWeekPredictor initialization"""
        roster = []
        predictor = RosterWeekPredictor(roster, self.mock_week)
        self.assertEqual(predictor.roster, roster)
        self.assertEqual(predictor.week, self.mock_week)

    def test_players_with_game_match(self):
        """Test players_with_game returns players from playing teams"""
        mock_player1 = Mock()
        mock_player1.proTeam = 'LAL'
        mock_player2 = Mock()
        mock_player2.proTeam = 'GSW'
        mock_player3 = Mock()
        mock_player3.proTeam = 'BOS'
        
        roster = [mock_player1, mock_player2, mock_player3]
        predictor = RosterWeekPredictor(roster, self.mock_week)
        
        result = predictor.players_with_game(0)
        self.assertEqual(len(result), 2)
        self.assertIn(mock_player1, result)
        self.assertIn(mock_player2, result)

    def test_players_with_game_no_match(self):
        """Test players_with_game returns empty list when no players match"""
        mock_player = Mock()
        mock_player.proTeam = 'CHI'
        
        roster = [mock_player]
        predictor = RosterWeekPredictor(roster, self.mock_week)
        
        result = predictor.players_with_game(0)
        self.assertEqual(len(result), 0)

    def test_players_with_game_different_days(self):
        """Test players_with_game for different scoring days"""
        mock_player1 = Mock()
        mock_player1.proTeam = 'LAL'
        mock_player2 = Mock()
        mock_player2.proTeam = 'MIA'
        
        roster = [mock_player1, mock_player2]
        predictor = RosterWeekPredictor(roster, self.mock_week)
        
        day_0_result = predictor.players_with_game(0)
        day_1_result = predictor.players_with_game(1)
        
        self.assertEqual(len(day_0_result), 1)
        self.assertIn(mock_player1, day_0_result)
        self.assertEqual(len(day_1_result), 2)

    @patch('predict.internal.roster_week_predictor.RosterWeekPredictor.get_avg_variance_stats')
    def test_predict_returns_tuple(self, mock_stats):
        """Test predict returns tuple of (points, std_dev)"""
        mock_stats.return_value = (10.0, 4.0)
        
        mock_player = Mock()
        mock_player.proTeam = 'LAL'
        mock_player.injuryStatus = 'ACTIVE'
        
        roster = [mock_player]
        predictor = RosterWeekPredictor(roster, self.mock_week)
        
        result = predictor.predict()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], (int, float))
        self.assertIsInstance(result[1], float)

    @patch('predict.internal.roster_week_predictor.RosterWeekPredictor.get_avg_variance_stats')
    def test_predict_with_injury_filter(self, mock_stats):
        """Test predict filters out injured players"""
        mock_stats.return_value = (10.0, 4.0)
        
        mock_player_active = Mock()
        mock_player_active.proTeam = 'LAL'
        mock_player_active.injuryStatus = 'ACTIVE'
        
        mock_player_injured = Mock()
        mock_player_injured.proTeam = 'LAL'
        mock_player_injured.injuryStatus = 'OUT'
        
        roster = [mock_player_active, mock_player_injured]
        predictor = RosterWeekPredictor(roster, self.mock_week)
        
        result = predictor.predict(injuryStatusList=['ACTIVE'])
        self.assertGreater(result[0], 0)

    def test_get_total_number_of_games_basic(self):
        """Test get_total_number_of_games counts available players"""
        mock_player1 = Mock()
        mock_player1.proTeam = 'LAL'
        mock_player1.injuryStatus = 'ACTIVE'
        
        mock_player2 = Mock()
        mock_player2.proTeam = 'GSW'
        mock_player2.injuryStatus = 'ACTIVE'
        
        mock_player3 = Mock()
        mock_player3.proTeam = 'BOS'
        mock_player3.injuryStatus = 'ACTIVE'
        
        roster = [mock_player1, mock_player2, mock_player3]
        predictor = RosterWeekPredictor(roster, self.mock_week)
        
        total = predictor.get_total_number_of_games(daily_active_size=2)
        self.assertGreater(total, 0)

    def test_get_total_number_of_games_respects_daily_cap(self):
        """Test get_total_number_of_games respects daily player cap"""
        # Create 15 players, all playing each day
        roster = []
        for i in range(15):
            mock_player = Mock()
            mock_player.proTeam = 'LAL'
            mock_player.injuryStatus = 'ACTIVE'
            roster.append(mock_player)
        
        # Mock week with 8 days where LAL plays all days
        mock_week = Mock(spec=Week)
        mock_week.scoring_period = (0, 7)
        mock_week.team_game_list = [['LAL'] for _ in range(8)]
        
        predictor = RosterWeekPredictor(roster, mock_week)
        total = predictor.get_total_number_of_games(daily_active_size=5)
        
        # 8 days (0-7) * 5 max per day = 40
        self.assertEqual(total, 40)


if __name__ == '__main__':
    unittest.main()
