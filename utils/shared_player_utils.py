"""Shared utilities for player and team data management."""
from typing import Dict, List

from espn_api.basketball import League
from nba_api.stats.static import teams as nba_teams_static


def get_all_players(league: League) -> Dict[int, any]:
    """Get all players from a league including free agents.
    
    Combines roster players from all teams with free agents,
    returning a deduplicated dictionary by player ID.
    
    Args:
        league: The fantasy basketball league
        
    Returns:
        Dictionary mapping player IDs to player objects
    """
    players: List[any] = []
    for team in league.teams:
        players.extend(team.roster)
    players.extend(league.free_agents(size=1000))
    unique_players: Dict[int, any] = {p.playerId: p for p in players}
    return unique_players


def build_team_id_map() -> Dict[str, int]:
    """Build a mapping of NBA team abbreviations to team IDs.
    
    Returns:
        Dictionary mapping team abbreviations to NBA team IDs
    """
    nba_teams = nba_teams_static.get_teams()
    abbr_to_id: Dict[str, int] = {}
    for t in nba_teams:
        abbr_to_id[t['abbreviation']] = t['id']
    return abbr_to_id
