"""Tests for team changes analysis module."""
import unittest
from unittest.mock import Mock, patch, MagicMock
from scout.players_changed_team_refactored import (
    get_all_players_team_map,
    passes_filters,
    PlayerTeamChange,
    PlayerRookie,
    PlayerDeparture,
    TeamChangesResult
)


class TestGetAllPlayersTeamMap(unittest.TestCase):
    """Test player team map creation."""
    
    def test_empty_league(self):
        """Test with empty league."""
        mock_league = Mock()
        mock_league.teams = []
        mock_league.free_agents.return_value = []
        
        result = get_all_players_team_map(mock_league, 2025)
        
        self.assertEqual(result, {})
        mock_league.free_agents.assert_called_once_with(size=1000)
    
    def test_single_player_from_roster(self):
        """Test with single player from roster."""
        mock_player = Mock()
        mock_player.playerId = 1
        mock_player.name = "Test Player"
        mock_player.proTeam = "LAL"
        mock_player.stats = {
            '2025_total': {'applied_avg': 25.5}
        }
        
        mock_team = Mock()
        mock_team.roster = [mock_player]
        
        mock_league = Mock()
        mock_league.teams = [mock_team]
        mock_league.free_agents.return_value = []
        
        result = get_all_players_team_map(mock_league, 2025)
        
        self.assertEqual(len(result), 1)
        self.assertIn(1, result)
        self.assertEqual(result[1]['name'], "Test Player")
        self.assertEqual(result[1]['team_abbr'], "LAL")
        self.assertEqual(result[1]['avg_fpts'], 25.5)
    
    def test_free_agents_override_roster(self):
        """Test that free agents override roster players."""
        # Roster player
        mock_roster_player = Mock()
        mock_roster_player.playerId = 1
        mock_roster_player.name = "Test Player"
        mock_roster_player.proTeam = "LAL"
        mock_roster_player.stats = {'2025_total': {'applied_avg': 25.5}}
        
        # Free agent with same ID
        mock_fa_player = Mock()
        mock_fa_player.playerId = 1
        mock_fa_player.name = "Test Player"
        mock_fa_player.proTeam = "FA"
        mock_fa_player.stats = {'2025_total': {'applied_avg': 0.0}}
        
        mock_team = Mock()
        mock_team.roster = [mock_roster_player]
        
        mock_league = Mock()
        mock_league.teams = [mock_team]
        mock_league.free_agents.return_value = [mock_fa_player]
        
        result = get_all_players_team_map(mock_league, 2025)
        
        # Free agent should override
        self.assertEqual(result[1]['team_abbr'], "FA")


class TestPassesFilters(unittest.TestCase):
    """Test player filtering logic."""
    
    def test_passes_filters_valid_player(self):
        """Test player that passes all filters."""
        player_2025 = {'avg_fpts': 15.0, 'team_abbr': 'LAL'}
        player_2026 = {'avg_fpts': 16.0, 'team_abbr': 'GSW'}
        
        result = passes_filters(player_2025, player_2026)
        
        self.assertTrue(result)
    
    def test_fails_filters_low_avg_fpts(self):
        """Test player with low avg_fpts fails filter."""
        player_2025 = {'avg_fpts': 5.0, 'team_abbr': 'LAL'}
        player_2026 = {'avg_fpts': 6.0, 'team_abbr': 'GSW'}
        
        result = passes_filters(player_2025, player_2026)
        
        self.assertFalse(result)
    
    def test_fails_filters_free_agent_destination(self):
        """Test player moving to free agency fails filter."""
        player_2025 = {'avg_fpts': 15.0, 'team_abbr': 'LAL'}
        player_2026 = {'avg_fpts': 0.0, 'team_abbr': 'FA'}
        
        result = passes_filters(player_2025, player_2026)
        
        self.assertFalse(result)
    
    def test_boundary_avg_fpts(self):
        """Test boundary case for avg_fpts filter (exactly 10)."""
        player_2025 = {'avg_fpts': 10.0, 'team_abbr': 'LAL'}
        player_2026 = {'avg_fpts': 11.0, 'team_abbr': 'GSW'}
        
        result = passes_filters(player_2025, player_2026)
        
        # Filter is < 10, so 10.0 should pass the filter (returns True)
        self.assertTrue(result)


class TestDataClasses(unittest.TestCase):
    """Test data class structures."""
    
    def test_player_team_change(self):
        """Test PlayerTeamChange dataclass."""
        change = PlayerTeamChange(
            name="LeBron James",
            avg_fpts=35.5,
            from_team="LAL",
            to_team="GSW"
        )
        
        self.assertEqual(change.name, "LeBron James")
        self.assertEqual(change.avg_fpts, 35.5)
        self.assertEqual(change.from_team, "LAL")
        self.assertEqual(change.to_team, "GSW")
    
    def test_player_rookie(self):
        """Test PlayerRookie dataclass."""
        rookie = PlayerRookie(
            name="Victor Wembanyama",
            team="SAS",
            avg_fpts=18.5
        )
        
        self.assertEqual(rookie.name, "Victor Wembanyama")
        self.assertEqual(rookie.team, "SAS")
        self.assertEqual(rookie.avg_fpts, 18.5)
    
    def test_player_departure(self):
        """Test PlayerDeparture dataclass."""
        departure = PlayerDeparture(
            name="Retired Player",
            last_team="LAL",
            avg_fpts=20.0
        )
        
        self.assertEqual(departure.name, "Retired Player")
        self.assertEqual(departure.last_team, "LAL")
        self.assertEqual(departure.avg_fpts, 20.0)
    
    def test_team_changes_result(self):
        """Test TeamChangesResult dataclass."""
        changes = [PlayerTeamChange("P1", 15.0, "LAL", "GSW")]
        rookies = [PlayerRookie("R1", "SAS", 10.0)]
        departures = [PlayerDeparture("D1", "LAL", 12.0)]
        
        result = TeamChangesResult(
            changed_teams=changes,
            rookies=rookies,
            departures=departures,
            total_changed=1,
            total_rookies=1,
            total_departures=1
        )
        
        self.assertEqual(result.total_changed, 1)
        self.assertEqual(result.total_rookies, 1)
        self.assertEqual(result.total_departures, 1)
        self.assertEqual(len(result.changed_teams), 1)


class TestDataclassDictConversion(unittest.TestCase):
    """Test converting dataclasses to dicts for JSON serialization."""
    
    def test_team_change_to_dict(self):
        """Test PlayerTeamChange dict conversion."""
        from dataclasses import asdict
        
        change = PlayerTeamChange(
            name="Test Player",
            avg_fpts=25.0,
            from_team="LAL",
            to_team="GSW"
        )
        
        change_dict = asdict(change)
        
        self.assertIsInstance(change_dict, dict)
        self.assertEqual(change_dict['name'], "Test Player")
        self.assertEqual(change_dict['avg_fpts'], 25.0)
    
    def test_team_changes_result_to_dict(self):
        """Test TeamChangesResult dict conversion."""
        from dataclasses import asdict
        
        changes = [PlayerTeamChange("P1", 15.0, "LAL", "GSW")]
        result = TeamChangesResult(
            changed_teams=changes,
            rookies=[],
            departures=[],
            total_changed=1,
            total_rookies=0,
            total_departures=0
        )
        
        # Note: asdict on nested dataclasses requires special handling
        result_dict = {
            'total_changed': result.total_changed,
            'total_rookies': result.total_rookies,
            'total_departures': result.total_departures,
            'changed_teams': [asdict(c) for c in result.changed_teams],
            'rookies': [asdict(r) for r in result.rookies],
            'departures': [asdict(d) for d in result.departures]
        }
        
        self.assertEqual(result_dict['total_changed'], 1)
        self.assertEqual(len(result_dict['changed_teams']), 1)


if __name__ == '__main__':
    unittest.main()
