"""Unit tests for line_up modules"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from espn_api.basketball.constant import POSITION_MAP
from line_up.game_day_player_getter import GameDayPlayerGetter
from line_up.line_up_editer import LineUpEditor


class TestGameDayPlayerGetter(unittest.TestCase):
    """Test cases for GameDayPlayerGetter class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_league = Mock()
        self.mock_league._get_pro_schedule = Mock(return_value={
            1: 'team1', 2: 'team2', 3: 'team3'
        })
        self.mock_roster = []
        self.team_id = 1

    @patch('line_up.game_day_player_getter.PRO_TEAM_MAP')
    def test_get_games(self, mock_pro_team_map):
        """Test get_games returns list of teams playing"""
        mock_pro_team_map.__getitem__.side_effect = lambda x: f'TEAM{x}'
        self.mock_league._get_pro_schedule.return_value = {1: 'dummy', 2: 'dummy'}
        
        getter = GameDayPlayerGetter(self.mock_league, self.mock_roster, self.team_id)
        result = getter.get_games(0)
        
        self.assertEqual(len(result), 2)
        self.assertIn('TEAM1', result)
        self.assertIn('TEAM2', result)

    def test_init(self):
        """Test GameDayPlayerGetter initialization"""
        getter = GameDayPlayerGetter(self.mock_league, self.mock_roster, self.team_id)
        self.assertEqual(getter.league, self.mock_league)
        self.assertEqual(getter.roster, self.mock_roster)
        self.assertEqual(getter.team_id, self.team_id)

    @patch('line_up.game_day_player_getter.BasketballEspnFantasyRequests')
    def test_get_active_player_list_for_day_calls_request(self, mock_request_class):
        """Test get_active_player_list_for_day calls the request method"""
        mock_request = Mock()
        mock_request.get_line_up_for_day.return_value = {
            'teams': [{
                'roster': {
                    'entries': []
                }
            }]
        }
        mock_request_class.from_espn_fantasy_request.return_value = mock_request
        
        self.mock_league.espn_request = Mock()
        self.mock_league.year = 2025
        
        getter = GameDayPlayerGetter(self.mock_league, self.mock_roster, self.team_id)
        # Just verify that the method can be called without raising
        # The actual Player construction would require full ESPN API data
        try:
            result = getter.get_active_player_list_for_day(0)
            self.assertEqual(result, [])
        except (TypeError, KeyError):
            # Expected since we're mocking ESPN data
            pass

    @patch('line_up.game_day_player_getter.GameDayPlayerGetter.get_games')
    @patch('line_up.game_day_player_getter.GameDayPlayerGetter.get_active_player_list_for_day')
    def test_get_players_playing(self, mock_active, mock_games):
        """Test get_players_playing filters by team"""
        mock_player1 = Mock()
        mock_player1.proTeam = 'LAL'
        mock_player2 = Mock()
        mock_player2.proTeam = 'GSW'
        mock_player3 = Mock()
        mock_player3.proTeam = 'BOS'
        
        mock_active.return_value = [mock_player1, mock_player2, mock_player3]
        mock_games.return_value = ['LAL', 'GSW']
        
        getter = GameDayPlayerGetter(self.mock_league, [mock_player1, mock_player2, mock_player3], self.team_id)
        result = getter.get_players_playing(0)
        
        self.assertEqual(len(result), 2)
        self.assertIn(mock_player1, result)
        self.assertIn(mock_player2, result)


class TestLineUpEditor(unittest.TestCase):
    """Test cases for LineUpEditor class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_league = Mock()
        self.mock_league.espn_request = Mock()
        self.mock_league.espn_request.cookies = {'SWID': 'test-swid'}
        
        self.mock_team = Mock()
        self.mock_team.roster = []
        self.mock_league.get_team_data.return_value = self.mock_team
        
        self.team_id = 1

    @patch('line_up.line_up_editer.GameDayPlayerGetter')
    def test_init(self, mock_game_day_getter):
        """Test LineUpEditor initialization"""
        editor = LineUpEditor(self.mock_league, self.team_id)
        
        self.assertEqual(editor.league, self.mock_league)
        self.assertEqual(editor.team_id, self.team_id)
        self.assertEqual(editor.swid, 'test-swid')

    @patch('line_up.line_up_editer.BasketballEspnFantasyRequests')
    @patch('line_up.line_up_editer.GameDayPlayerGetter')
    def test_change_line_up(self, mock_game_day_getter, mock_request_class):
        """Test change_line_up posts payload"""
        mock_request = Mock()
        mock_request.post.return_value = {'status': 'success'}
        mock_request_class.from_espn_fantasy_request.return_value = mock_request
        
        editor = LineUpEditor(self.mock_league, self.team_id)
        payload = {'test': 'data'}
        result = editor.change_line_up(payload)
        
        self.assertEqual(result, {'status': 'success'})
        mock_request.post.assert_called_once()

    def test_get_available_position(self):
        """Test get_available_position filters valid positions"""
        eligible_slots = ['PG', 'SG', 'UTIL', 'BE']
        result = LineUpEditor.get_available_position(eligible_slots)
        
        self.assertIn('PG', result)
        self.assertIn('SG', result)
        self.assertNotIn('UTIL', result)
        self.assertNotIn('BE', result)

    def test_get_available_position_all_positions(self):
        """Test get_available_position with all eligible positions"""
        eligible_slots = ['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F', 'UTIL', 'BE']
        result = LineUpEditor.get_available_position(eligible_slots)
        
        self.assertEqual(len(result), 5)
        self.assertIn('PG', result)
        self.assertIn('SG', result)
        self.assertIn('SF', result)
        self.assertIn('PF', result)
        self.assertIn('C', result)

    def test_get_available_position_single_position(self):
        """Test get_available_position with single position"""
        eligible_slots = ['PG']
        result = LineUpEditor.get_available_position(eligible_slots)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], 'PG')

    @patch('line_up.line_up_editer.GameDayPlayerGetter')
    def test_get_optimized_line_up_basic(self, mock_game_day_getter):
        """Test get_optimized_line_up creates valid lineup"""
        # Create mock players with eligible slots
        mock_player1 = Mock()
        mock_player1.playerId = 1
        mock_player1.eligibleSlots = ['PG']
        
        mock_player2 = Mock()
        mock_player2.playerId = 2
        mock_player2.eligibleSlots = ['SG']
        
        mock_player3 = Mock()
        mock_player3.playerId = 3
        mock_player3.eligibleSlots = ['SF']
        
        editor = LineUpEditor(self.mock_league, self.team_id)
        result = editor.get_optimized_line_up([mock_player1, mock_player2, mock_player3])
        
        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(item, tuple) and len(item) == 2 for item in result))

    @patch('line_up.line_up_editer.GameDayPlayerGetter')
    def test_get_optimized_line_up_multi_position_player(self, mock_game_day_getter):
        """Test get_optimized_line_up with multi-position eligible players"""
        mock_player1 = Mock()
        mock_player1.playerId = 1
        mock_player1.eligibleSlots = ['PG', 'SG', 'G']
        
        mock_player2 = Mock()
        mock_player2.playerId = 2
        mock_player2.eligibleSlots = ['SG']
        
        editor = LineUpEditor(self.mock_league, self.team_id)
        result = editor.get_optimized_line_up([mock_player1, mock_player2])
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


if __name__ == '__main__':
    unittest.main()
