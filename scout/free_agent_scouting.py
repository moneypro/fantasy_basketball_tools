"""Free agent scouting and analysis functions."""

from typing import Dict, List, Any, Set
from espn_api.basketball import League
import requests
import json


def get_waiver_player_ids(league: League) -> Set[int]:
    """Get all player IDs currently on waivers using ESPN API.
    
    Args:
        league: The fantasy basketball league
        
    Returns:
        Set of player IDs that are currently on waivers
    """
    waiver_player_ids = set()
    
    try:
        # Use requests directly with league's cookies for waiver filter
        # Note: league.espn_request.league_get() has issues with certain headers
        x_fantasy_filter = {
            "players": {
                "filterStatus": {"value": ["WAIVERS"]}
            }
        }
        
        headers = {
            "x-fantasy-filter": json.dumps(x_fantasy_filter),
            "x-fantasy-platform": "espn-fantasy-web",
            "x-fantasy-source": "kona"
        }
        
        params = {
            "view": "kona_player_info"
        }
        
        response = requests.get(
            league.espn_request.LEAGUE_ENDPOINT,
            params=params,
            headers=headers,
            cookies=league.espn_request.cookies
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract player IDs from waivers
        if isinstance(data, dict) and 'players' in data:
            for player in data['players']:
                if 'id' in player:
                    waiver_player_ids.add(player['id'])
    
    except Exception as e:
        print(f"Warning: Could not fetch waiver players: {e}")
    
    return waiver_player_ids


def get_games_next_5_periods(league: League, nba_team: str, pro_schedule_data: Dict = None) -> List[int]:
    """Get which of the next 5 scoring periods the NBA team has games.
    
    Args:
        league: The fantasy basketball league
        nba_team: NBA team abbreviation (e.g., 'LAL', 'BOS')
        pro_schedule_data: Cached pro schedule data (fetched once to avoid repeated API calls)
        
    Returns:
        List of scoring periods (49-53) when the team has games
    """
    games_periods = []
    
    try:
        from espn_api.basketball.constant import PRO_TEAM_MAP
        
        current_period = league.scoringPeriodId if hasattr(league, 'scoringPeriodId') else 48
        
        # If schedule data not provided, fetch it
        if pro_schedule_data is None:
            pro_schedule_response = league.espn_request.get_pro_schedule()
        else:
            pro_schedule_response = pro_schedule_data
        
        pro_teams = pro_schedule_response['settings']['proTeams']
        
        # Get the pro team ID for this NBA team abbreviation
        nba_team_id = None
        for team_id, team_abbr in PRO_TEAM_MAP.items():
            if team_abbr == nba_team:
                nba_team_id = team_id
                break
        
        if nba_team_id:
            # Check which periods this team has games
            for team in pro_teams:
                if team['id'] == nba_team_id:
                    pro_games = team.get('proGamesByScoringPeriod', {})
                    for period_str in pro_games.keys():
                        try:
                            period = int(period_str)
                            # Include periods from current to current+5 (next 5 days)
                            if current_period <= period <= current_period + 5:
                                games_periods.append(period)
                        except ValueError:
                            pass
                    break
    
    except Exception as e:
        # Return empty list on error
        pass
    
    return sorted(games_periods)


def get_team_injuries(all_players: Dict[int, Any], nba_team: str, exclude_player_id: int = None) -> List[Dict[str, Any]]:
    """Get all OUT and DAY_TO_DAY players on a specific NBA team.
    
    Args:
        all_players: Dictionary of all players (key: playerId, value: player object)
        nba_team: NBA team abbreviation (e.g., 'LAL', 'BOS')
        exclude_player_id: Player ID to exclude from results (e.g., the free agent themselves)
        
    Returns:
        List of dicts with injured player info: name, position, injury_status, avg_points
    """
    injuries = []
    
    # Find players on the specified NBA team with injury status
    for player_id, player in all_players.items():
        # Skip the excluded player (usually the free agent themselves)
        if exclude_player_id and player_id == exclude_player_id:
            continue
        
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


def build_free_agent_data(all_players: Dict[int, Any], free_agent_player: Any, waiver_player_ids: Set[int] = None, recent_transactions: List[Any] = None, league: League = None, pro_schedule_data: Dict = None) -> Dict[str, Any]:
    """Build complete free agent data including stats and team injuries.
    
    Args:
        all_players: Dictionary of all players (for injury lookup)
        free_agent_player: The free agent player object
        waiver_player_ids: Set of player IDs currently on waivers
        recent_transactions: List of recent transactions (to find drop date)
        league: League object (for getting schedule info)
        pro_schedule_data: Cached pro schedule data (to avoid repeated API calls)
        
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
    
    # Get position eligibility from eligibleSlots
    # Extract the 5 primary positions: PG, SG, SF, PF, C
    # Also include G if player has PG or SG, and F if player has SF or PF
    primary_positions = {'PG', 'SG', 'SF', 'PF', 'C'}
    
    eligible_slots = getattr(free_agent_player, 'eligibleSlots', [])
    positions_set = set()  # Use set to avoid duplicates
    has_guard = False
    has_forward = False
    
    for slot in eligible_slots:
        if '/' in slot:
            # Expand combo positions like "PG/SG" or "SF/PF/C"
            for pos in slot.split('/'):
                if pos in primary_positions:
                    positions_set.add(pos)
                    if pos in {'PG', 'SG'}:
                        has_guard = True
                    if pos in {'SF', 'PF'}:
                        has_forward = True
        elif slot in primary_positions:
            positions_set.add(slot)
            if slot in {'PG', 'SG'}:
                has_guard = True
            if slot in {'SF', 'PF'}:
                has_forward = True
        # Ignore G, F, UT, BE, IR and other non-primary positions
    
    # Add G if they have guard positions, F if they have forward positions
    if has_guard:
        positions_set.add('G')
    if has_forward:
        positions_set.add('F')
    
    positions_eligible = sorted(list(positions_set))
    
    # Get injury status
    injury_status = getattr(free_agent_player, 'injuryStatus', 'ACTIVE')
    if not injury_status:
        injury_status = 'ACTIVE'
    
    # Check if injured
    injured = getattr(free_agent_player, 'injured', False)
    
    # Get NBA team
    nba_team = getattr(free_agent_player, 'proTeam', 'UNKNOWN')
    
    # Get next 5 periods schedule (which periods this player's team has games)
    games_next_5_periods = []
    if nba_team != 'UNKNOWN' and league:
        games_next_5_periods = get_games_next_5_periods(league, nba_team, pro_schedule_data)
    
    # Get team injuries for this player's NBA team (excluding the player themselves)
    team_injuries = []
    if nba_team != 'UNKNOWN':
        team_injuries = get_team_injuries(all_players, nba_team, exclude_player_id=player_id)
    
    # Check if player is on waivers (from ESPN API waiver list)
    on_waivers = False
    waiver_clear_period = None
    if waiver_player_ids and player_id in waiver_player_ids:
        on_waivers = True
        
        # Find when player was dropped
        if recent_transactions:
            for trans in recent_transactions:
                if hasattr(trans, 'type') and trans.type == 'FREEAGENT' and hasattr(trans, 'items'):
                    for item in trans.items:
                        item_str = str(item)
                        if 'DROP' in item_str and free_agent_player.name in item_str:
                            # Store the scoring period when player was dropped
                            waiver_clear_period = trans.scoring_period if hasattr(trans, 'scoring_period') else None
                            break
    
    return {
        'player_id': player_id,
        'name': free_agent_player.name,
        'nba_team': nba_team,
        'injury_status': injury_status,
        'injured': injured,
        'on_waivers': on_waivers,
        'waiver_clear_period': waiver_clear_period,
        'positions_eligible': positions_eligible,
        'games_next_5_periods': games_next_5_periods,
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
    # Build all players dict once (for efficiency)
    all_players = {}
    for team in league.teams:
        for player in team.roster:
            all_players[player.playerId] = player
    
    # Get all free agents
    free_agents_list = league.free_agents(size=1000)
    for player in free_agents_list:
        all_players[player.playerId] = player
    
    # Get waiver player IDs from ESPN API
    waiver_player_ids = get_waiver_player_ids(league)
    
    # Get recent transactions to find drop dates for waivers
    recent_transactions = []
    try:
        current_period = league.scoringPeriodId if hasattr(league, 'scoringPeriodId') else 1
        recent_transactions.extend(league.transactions())
        for period in range(max(1, current_period - 7), current_period):
            try:
                recent_transactions.extend(league.transactions(scoring_period=period))
            except:
                pass
    except:
        pass
    
    # Fetch pro schedule once to avoid repeated API calls
    pro_schedule_data = None
    try:
        pro_schedule_data = league.espn_request.get_pro_schedule()
    except:
        pass
    
    free_agents_dict = {}
    
    # Build data for each free agent
    for player in free_agents_list:
        avg_last_30 = player.stats.get('2026_last_30', {}).get('applied_avg', 0.0)
        
        # Filter by minimum average points
        if avg_last_30 >= min_avg_points:
            player_data = build_free_agent_data(all_players, player, waiver_player_ids, recent_transactions, league, pro_schedule_data)
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
