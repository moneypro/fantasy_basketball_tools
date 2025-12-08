"""Free agent scouting and analysis functions."""

from typing import Dict, List, Any
from espn_api.basketball import League


def get_team_injuries(league: League, nba_team: str) -> List[Dict[str, Any]]:
    """Get all OUT and DAY_TO_DAY players on a specific NBA team.
    
    Args:
        league: The fantasy basketball league
        nba_team: NBA team abbreviation (e.g., 'LAL', 'BOS')
        
    Returns:
        List of dicts with injured player info: name, position, injury_status, avg_points
    """
    injuries = []
    
    # Check all players in the league for this NBA team
    all_players = {}
    for team in league.teams:
        for player in team.roster:
            all_players[player.playerId] = player
    
    # Also add free agents
    free_agents = league.free_agents(size=1000)
    for player in free_agents:
        all_players[player.playerId] = player
    
    # Find players on the specified NBA team with injury status
    for player_id, player in all_players.items():
        player_nba_team = getattr(player, 'proTeam', None)
        injury_status = getattr(player, 'injuryStatus', None)
        
        # Check if this player is on the target team and has an injury status
        if player_nba_team == nba_team and injury_status and injury_status in ['OUT', 'DAY_TO_DAY']:
            # Get average points
            stats_30 = player.stats.get('2026_last_30', {})
            avg_points = stats_30.get('applied_avg', 0.0)
            
            # Get position
            position = getattr(player, 'position', 'UNKNOWN')
            
            injuries.append({
                'player_name': player.name,
                'position': position,
                'injury_status': injury_status,
                'avg_points': round(avg_points, 2)
            })
    
    return injuries


def build_free_agent_data(league: League, league_2026: League, free_agent_player: Any) -> Dict[str, Any]:
    """Build complete free agent data including stats and team injuries.
    
    Args:
        league: Current fantasy league (for context)
        league_2026: League for 2026 season (for stats)
        free_agent_player: The free agent player object
        
    Returns:
        Dictionary with free agent data ready for API response
    """
    player_id = free_agent_player.playerId
    
    # Get stats
    stats_30 = free_agent_player.stats.get('2026_last_30', {})
    avg_last_30 = stats_30.get('applied_avg', 0.0)
    total_30 = stats_30.get('applied_total', 0.0)
    gp_30 = int(round(total_30 / avg_last_30)) if avg_last_30 > 0 else 0
    
    stats_year = free_agent_player.stats.get('2026_total', {})
    avg_year = stats_year.get('applied_avg', 0.0)
    
    stats_proj = free_agent_player.stats.get('2026_projected', {})
    avg_projected = stats_proj.get('applied_avg', 0.0)
    
    # Get position eligibility
    positions_eligible = set(free_agent_player.eligibleSlots) if hasattr(free_agent_player, 'eligibleSlots') else set()
    
    # Get injury status
    injury_status = getattr(free_agent_player, 'injuryStatus', 'ACTIVE')
    if not injury_status:
        injury_status = 'ACTIVE'
    
    # Get NBA team
    nba_team = getattr(free_agent_player, 'proTeam', 'UNKNOWN')
    
    # Get team injuries for this player's NBA team
    team_injuries = []
    if nba_team != 'UNKNOWN':
        team_injuries = get_team_injuries(league, nba_team)
    
    return {
        'player_id': player_id,
        'name': free_agent_player.name,
        'nba_team': nba_team,
        'injury_status': injury_status,
        'positions_eligible': list(positions_eligible),
        'scoring': {
            'avg_last_30': round(avg_last_30, 2),
            'total_30': round(total_30, 2),
            'gp_30': gp_30,
            'avg_year': round(avg_year, 2),
            'avg_projected': round(avg_projected, 2)
        },
        'team_injuries': team_injuries
    }


def scout_free_agents(league: League, limit: int = 20, min_avg_points: float = 5.0) -> Dict[str, Any]:
    """Scout all free agents and return ranked data.
    
    Args:
        league: The fantasy basketball league
        limit: Number of free agents to return
        min_avg_points: Minimum avg_last_30 to include (default 5.0)
        
    Returns:
        Dictionary with free agents data sorted by avg_last_30 descending
    """
    free_agents_dict = {}
    
    # Get all free agents
    free_agents_list = league.free_agents(size=1000)
    
    # Build data for each free agent
    for player in free_agents_list:
        avg_last_30 = player.stats.get('2026_last_30', {}).get('applied_avg', 0.0)
        
        # Filter by minimum average points
        if avg_last_30 >= min_avg_points:
            player_data = build_free_agent_data(league, league, player)
            free_agents_dict[player.playerId] = player_data
    
    # Sort by avg_last_30 descending
    sorted_free_agents = sorted(
        free_agents_dict.values(),
        key=lambda x: x['scoring']['avg_last_30'],
        reverse=True
    )
    
    # Return top N
    return {
        'free_agents': sorted_free_agents[:limit],
        'summary': {
            'total_free_agents_analyzed': len(free_agents_list),
            'returned': min(limit, len(sorted_free_agents)),
            'min_avg_points_filter': min_avg_points
        }
    }
