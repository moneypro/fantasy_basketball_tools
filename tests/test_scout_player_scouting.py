"""Tests for refactored player scouting module."""
import unittest
from unittest.mock import Mock, patch, MagicMock
from scout.player_scouting_refactored import (
    calculate_final_score,
    get_team_rankings,
    scout_players,
    PlayerStats,
    PlayerUpside,
    ScoutingResult
)
import config


class TestCalculateFinalScore(unittest.TestCase):
    """Test final score calculation."""
    
    def test_basic_score_calculation(self):
        """Test basic score calculation without games played penalty."""
        # avg_recent=100, avg_proj=90, gp_proj=82 (full season, no penalty)
        score = calculate_final_score(100, 90, 82)
        # base_score = 0.6 * 100 + 0.4 * 90 = 60 + 36 = 96
        # penalty_factor = 1 - ADJUSTER * (82-82)/82 = 1
        # final = 96 * 1 = 96, but actual config values may differ
        self.assertGreater(score, 90)
        self.assertLess(score, 100)
    
    def test_score_with_games_penalty(self):
        """Test score calculation with games played penalty."""
        # avg_recent=100, avg_proj=90, gp_proj=50 (less than 82, applies penalty)
        score = calculate_final_score(100, 90, 50)
        # base_score = 0.6 * 100 + 0.4 * 90 = 96
        # penalty_factor = 1 - ADJUSTER * (82-50)/82 = 1 - ADJUSTER * 32/82
        # This depends on config.ADJUSTER value
        self.assertGreater(score, 0)
        self.assertLess(score, 100)
    
    def test_zero_recent_average(self):
        """Test with zero recent average."""
        score = calculate_final_score(0, 50, 82)
        # base_score = RECENT_STATS_RATIO * 0 + (1 - RECENT_STATS_RATIO) * 50
        # With config values, this depends on RECENT_STATS_RATIO
        # penalty_factor = 1 (gp_proj == 82)
        self.assertGreater(score, 0)
        self.assertLess(score, 50)


class TestGetTeamRankings(unittest.TestCase):
    """Test team ranking calculation."""
    
    def test_single_team_ranking(self):
        """Test ranking calculation for a single team."""
        # Create mock player data
        player_points = [
            (1, "Player1", 20, 100, 5, 10, 25, 20, 50),  # player_id=1
            (2, "Player2", 15, 80, 4, 8, 20, 20, 40),   # player_id=2
        ]
        standardized = [100, 50]  # Player1 is ranked higher
        
        # Mock players_2026
        mock_player1 = Mock()
        mock_player1.proTeam = "LAL"
        mock_player2 = Mock()
        mock_player2.proTeam = "LAL"
        
        players_2026 = {1: mock_player1, 2: mock_player2}
        
        ranks = get_team_rankings(player_points, standardized, players_2026)
        
        self.assertEqual(ranks[1], 1)  # Player1 is #1 on team
        self.assertEqual(ranks[2], 2)  # Player2 is #2 on team
    
    def test_multiple_teams_ranking(self):
        """Test ranking calculation for multiple teams."""
        player_points = [
            (1, "Player1", 20, 100, 5, 10, 25, 20, 50),
            (2, "Player2", 15, 80, 4, 8, 20, 20, 40),
            (3, "Player3", 18, 90, 5, 9, 22, 20, 45),
        ]
        standardized = [100, 50, 75]
        
        mock_player1 = Mock()
        mock_player1.proTeam = "LAL"
        mock_player2 = Mock()
        mock_player2.proTeam = "LAL"
        mock_player3 = Mock()
        mock_player3.proTeam = "GSW"
        
        players_2026 = {1: mock_player1, 2: mock_player2, 3: mock_player3}
        
        ranks = get_team_rankings(player_points, standardized, players_2026)
        
        # LAL team: Player1 (100) is #1, Player2 (50) is #2
        self.assertEqual(ranks[1], 1)
        self.assertEqual(ranks[2], 2)
        # GSW team: Player3 (75) is #1 (only player)
        self.assertEqual(ranks[3], 1)


class TestScoutPlayersDataStructure(unittest.TestCase):
    """Test scout_players return data structure."""
    
    def test_scouting_result_structure(self):
        """Test that ScoutingResult is properly structured."""
        result = ScoutingResult(
            players=[],
            upside_differences=[],
            total_players_analyzed=100,
            limit_returned=0
        )
        
        self.assertEqual(result.total_players_analyzed, 100)
        self.assertEqual(result.limit_returned, 0)
        self.assertEqual(len(result.players), 0)
        self.assertEqual(len(result.upside_differences), 0)
    
    def test_player_stats_dataclass(self):
        """Test PlayerStats dataclass."""
        player = PlayerStats(
            player_id=1,
            name="LeBron James",
            avg_recent=35.5,
            total_30=200,
            gp_30=10,
            gp_year=50,
            avg_proj=34.0,
            gp_proj=75,
            standardized_score=95.5,
            potential_upside=98.2,
            team_rank=1,
            eligibility={'PG': True, 'SG': False, 'SF': True, 'PF': True, 'C': False, 'G': True, 'F': True}
        )
        
        self.assertEqual(player.player_id, 1)
        self.assertEqual(player.name, "LeBron James")
        self.assertEqual(player.avg_recent, 35.5)
        self.assertTrue(player.eligibility['SF'])
        self.assertFalse(player.eligibility['C'])
    
    def test_player_upside_dataclass(self):
        """Test PlayerUpside dataclass."""
        upside = PlayerUpside(
            name="Luka Doncic",
            standardized_score=92.0,
            potential_upside=98.5,
            difference=6.5
        )
        
        self.assertEqual(upside.name, "Luka Doncic")
        self.assertEqual(upside.difference, 6.5)
        self.assertGreater(upside.potential_upside, upside.standardized_score)


class TestPlayerStatsAsDict(unittest.TestCase):
    """Test converting PlayerStats to dictionary for JSON serialization."""
    
    def test_player_stats_dict_conversion(self):
        """Test that PlayerStats can be converted to dict."""
        player = PlayerStats(
            player_id=1,
            name="Test Player",
            avg_recent=25.0,
            total_30=150,
            gp_30=8,
            gp_year=40,
            avg_proj=26.0,
            gp_proj=70,
            standardized_score=85.0,
            potential_upside=90.0,
            team_rank=2,
            eligibility={'PG': True, 'SG': False, 'SF': False, 'PF': False, 'C': False, 'G': True, 'F': False}
        )
        
        from dataclasses import asdict
        player_dict = asdict(player)
        
        self.assertIsInstance(player_dict, dict)
        self.assertEqual(player_dict['player_id'], 1)
        self.assertEqual(player_dict['name'], "Test Player")
        self.assertTrue(player_dict['eligibility']['PG'])


if __name__ == '__main__':
    unittest.main()
