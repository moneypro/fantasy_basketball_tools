"""Free agent scouting and analysis functions."""

from typing import Dict, List, Any, Set
from espn_api.basketball import League
from datetime import timedelta, date
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


def check_team_has_game(nba_team: str, scoring_period: int, pro_schedule_data: Dict, league: League) -> bool:
    """Check if NBA team has a game on a specific scoring period.

    Args:
        nba_team: NBA team abbreviation
        scoring_period: Scoring period number
        pro_schedule_data: Cached pro schedule
        league: League object

    Returns:
        True if team has game, False otherwise
    """
    try:
        from espn_api.basketball.constant import PRO_TEAM_MAP

        # Get pro team ID
        nba_team_id = None
        for team_id, team_abbr in PRO_TEAM_MAP.items():
            if team_abbr == nba_team:
                nba_team_id = team_id
                break

        if not nba_team_id:
            return False

        # Check schedule
        if pro_schedule_data:
            pro_teams = pro_schedule_data['settings']['proTeams']
            for team in pro_teams:
                if team['id'] == nba_team_id:
                    pro_games = team.get('proGamesByScoringPeriod', {})
                    return str(scoring_period) in pro_games

        return False
    except:
        return False


def get_schedule_next_7_days(league: League, nba_team: str, week_index: int, pro_schedule_data: Dict = None) -> List[Dict[str, Any]]:
    """Get 7-day schedule for an NBA team with back-to-back detection.

    Args:
        league: The fantasy basketball league
        nba_team: NBA team abbreviation (e.g., 'LAL', 'BOS')
        week_index: Fantasy matchup week (1-23)
        pro_schedule_data: Cached pro schedule data

    Returns:
        List of 7 dicts (one per day) with:
        - date: ISO 8601 date string (YYYY-MM-DD)
        - has_game: bool
        - is_back_to_back: bool (true if team played previous day)
    """
    from utils.date_utils import DateScoringPeriodConverter

    # Get date range for this week
    start_date, end_date = DateScoringPeriodConverter.matchup_week_to_date_range(week_index)

    schedule = []
    prev_day_had_game = False

    # Iterate through 7 days
    for day_offset in range(7):
        current_date = start_date + timedelta(days=day_offset)
        scoring_period = DateScoringPeriodConverter.date_to_scoring_period(current_date)

        # Check if team has game this day
        has_game = check_team_has_game(nba_team, scoring_period, pro_schedule_data, league)

        # Detect back-to-back
        is_back_to_back = prev_day_had_game and has_game

        schedule.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "has_game": has_game,
            "is_back_to_back": is_back_to_back
        })

        prev_day_had_game = has_game

    return schedule


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


def get_team_injuries(all_players: Dict[int, Any], nba_team: str, free_agent_positions: List[str] = None, exclude_player_id: int = None) -> List[Dict[str, Any]]:
    """Get all OUT and DAY_TO_DAY players on a specific NBA team.

    Args:
        all_players: Dictionary of all players (key: playerId, value: player object)
        nba_team: NBA team abbreviation (e.g., 'LAL', 'BOS')
        free_agent_positions: List of positions free agent is eligible for (for position matching)
        exclude_player_id: Player ID to exclude from results (e.g., the free agent themselves)

    Returns:
        List of dicts with injured player info: name, position, positions_eligible, injury_status, avg_points, position_match
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

            # Get position eligibility (same logic as free agent positions)
            real_positions = {'PG', 'SG', 'SF', 'PF', 'C', 'G', 'F'}
            eligible_slots = getattr(player, 'eligibleSlots', [])
            positions_eligible = []
            for slot in eligible_slots:
                if '/' in slot:
                    for pos in slot.split('/'):
                        if pos in real_positions and pos not in positions_eligible:
                            positions_eligible.append(pos)
                elif slot in real_positions and slot not in positions_eligible:
                    positions_eligible.append(slot)

            # Check if injured player can play same roster slot as free agent
            position_match = False
            if free_agent_positions and positions_eligible:
                position_match = bool(set(free_agent_positions) & set(positions_eligible))

            injuries.append({
                'player_name': player.name,
                'position': position,
                'positions_eligible': positions_eligible,
                'injury_status': injury_status,
                'avg_points': round(avg_points, 2),
                'position_match': position_match
            })

    return injuries


def build_free_agent_data(all_players: Dict[int, Any], free_agent_player: Any, waiver_player_ids: Set[int] = None, recent_transactions: List[Any] = None, league: League = None, week_index: int = None, pro_schedule_data: Dict = None) -> Dict[str, Any]:
    """Build complete free agent data including stats and team injuries.

    Args:
        all_players: Dictionary of all players (for injury lookup)
        free_agent_player: The free agent player object
        waiver_player_ids: Set of player IDs currently on waivers
        recent_transactions: List of recent transactions (to find drop date)
        league: League object (for getting schedule info)
        week_index: Fantasy matchup week (1-23)
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
    
    # Get position eligibility - expand combo positions to individual positions
    # E.g., "F/C" becomes ["F", "C"], "G" stays ["G"], etc.
    # Filter out non-position slots like BE (Bench), IR (Injured Reserve), UT (Utility), Rookie
    real_positions = {'PG', 'SG', 'SF', 'PF', 'C', 'G', 'F'}
    eligible_slots = getattr(free_agent_player, 'eligibleSlots', [])
    positions_eligible = []
    for slot in eligible_slots:
        if '/' in slot:
            # Expand combo positions like "F/C" to ["F", "C"]
            for pos in slot.split('/'):
                if pos in real_positions and pos not in positions_eligible:
                    positions_eligible.append(pos)
        elif slot in real_positions and slot not in positions_eligible:
            positions_eligible.append(slot)
    
    # Get injury status
    injury_status = getattr(free_agent_player, 'injuryStatus', 'ACTIVE')
    if not injury_status:
        injury_status = 'ACTIVE'

    # Check if injured
    injured = getattr(free_agent_player, 'injured', False)

    # Get expected return date and calculate days until return
    expected_return_date = getattr(free_agent_player, 'expected_return_date', None)
    days_until_return = None
    if expected_return_date:
        days_until_return = (expected_return_date - date.today()).days
    
    # Get NBA team
    nba_team = getattr(free_agent_player, 'proTeam', 'UNKNOWN')

    # Get next 7 days schedule with back-to-back detection
    schedule_next_7_days = []
    total_games_next_7 = 0
    back_to_back_count = 0

    if nba_team != 'UNKNOWN' and league and week_index:
        schedule_next_7_days = get_schedule_next_7_days(league, nba_team, week_index, pro_schedule_data)
        # Count totals
        for day in schedule_next_7_days:
            if day['has_game']:
                total_games_next_7 += 1
            if day['is_back_to_back']:
                back_to_back_count += 1

    # Get team injuries for this player's NBA team (excluding the player themselves)
    # Pass positions for position matching
    team_injuries = []
    if nba_team != 'UNKNOWN':
        team_injuries = get_team_injuries(all_players, nba_team, positions_eligible, exclude_player_id=player_id)
    
    # Check if player is on waivers (from ESPN API waiver list)
    on_waivers = False
    waiver_clear_date = None
    if waiver_player_ids and player_id in waiver_player_ids:
        on_waivers = True

        # Find when player was dropped
        if recent_transactions:
            from utils.date_utils import DateScoringPeriodConverter

            for trans in recent_transactions:
                if hasattr(trans, 'type') and trans.type == 'FREEAGENT' and hasattr(trans, 'items'):
                    for item in trans.items:
                        item_str = str(item)
                        if 'DROP' in item_str and free_agent_player.name in item_str:
                            # Convert scoring period to date
                            if hasattr(trans, 'scoring_period') and trans.scoring_period:
                                waiver_clear_date = DateScoringPeriodConverter.scoring_period_to_date(trans.scoring_period)
                            break
    
    return {
        'player_id': player_id,
        'name': free_agent_player.name,
        'nba_team': nba_team,
        'injury_status': injury_status,
        'injured': injured,
        'expected_return_date': expected_return_date.strftime("%Y-%m-%d") if expected_return_date else None,
        'days_until_return': days_until_return,
        'on_waivers': on_waivers,
        'waiver_clear_date': waiver_clear_date.strftime("%Y-%m-%d") if waiver_clear_date else None,
        'positions_eligible': positions_eligible,
        'schedule_next_7_days': schedule_next_7_days,
        'total_games_next_7': total_games_next_7,
        'back_to_back_count': back_to_back_count,
        'scoring': {
            'avg_last_30': round(avg_last_30, 2),
            'total_30': round(total_30, 2),
            'gp_30': gp_30,
            'avg_year': round(avg_year, 2),
            'avg_projected': round(avg_projected, 2)
        },
        'team_injuries': team_injuries
    }


def build_roster_data(team: Any, league: League, week_index: int, pro_schedule_data: Dict = None) -> Dict[str, Any]:
    """Build roster data with schedules for all players.

    Args:
        team: Fantasy team object
        league: League object
        week_index: Fantasy matchup week
        pro_schedule_data: Cached pro schedule

    Returns:
        Dictionary with roster data including schedules
    """
    roster_players = []

    for player in team.roster:
        # Get stats
        stats_30 = player.stats.get('2026_last_30', {})
        avg_last_30 = stats_30.get('applied_avg', 0.0)

        stats_year = player.stats.get('2026_total', {})
        avg_year = stats_year.get('applied_avg', 0.0)

        stats_proj = player.stats.get('2026_projected', {})
        avg_projected = stats_proj.get('applied_avg', 0.0)

        # Get NBA team
        nba_team = getattr(player, 'proTeam', 'UNKNOWN')

        # Get schedule
        schedule_next_7_days = []
        total_games_next_7 = 0
        back_to_back_count = 0

        if nba_team != 'UNKNOWN':
            schedule_next_7_days = get_schedule_next_7_days(
                league, nba_team, week_index, pro_schedule_data
            )
            for day in schedule_next_7_days:
                if day['has_game']:
                    total_games_next_7 += 1
                if day['is_back_to_back']:
                    back_to_back_count += 1

        roster_players.append({
            'player_id': player.playerId,
            'name': player.name,
            'nba_team': nba_team,
            'position': getattr(player, 'position', 'UNKNOWN'),
            'injury_status': getattr(player, 'injuryStatus', 'ACTIVE') or 'ACTIVE',
            'scoring': {
                'avg_last_30': round(avg_last_30, 2),
                'avg_year': round(avg_year, 2),
                'avg_projected': round(avg_projected, 2)
            },
            'schedule_next_7_days': schedule_next_7_days,
            'total_games_next_7': total_games_next_7,
            'back_to_back_count': back_to_back_count
        })

    return {
        'team_id': team.team_id,
        'team_name': team.team_name,
        'total_players': len(roster_players),
        'players': roster_players
    }


def scout_free_agents(league: League, team_id: int = None, week_index: int = None, limit: int = 20, min_avg_points: float = 5.0) -> Dict[str, Any]:
    """Scout all free agents and return ranked data with roster context.

    Args:
        league: The fantasy basketball league
        team_id: User's team ID for roster context (optional)
        week_index: Fantasy matchup week (1-23), defaults to current
        limit: Number of free agents to return
        min_avg_points: Minimum avg_last_30 to include (default 5.0)

    Returns:
        Dictionary with free agents data, roster context, and matchup info
    """
    from utils.date_utils import DateScoringPeriodConverter

    # Default to current week if not provided
    # Use date-based calculation instead of cached league.currentMatchupPeriod
    if not week_index:
        week_index = DateScoringPeriodConverter.get_current_matchup_week()

    # Get date range for matchup context
    start_date, end_date = DateScoringPeriodConverter.matchup_week_to_date_range(week_index)

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

    # Build roster context if team_id provided
    roster_data = None
    if team_id:
        target_team = None
        for team in league.teams:
            if team.team_id == team_id:
                target_team = team
                break

        if target_team:
            roster_data = build_roster_data(
                target_team, league, week_index, pro_schedule_data
            )

    free_agents_dict = {}

    # Build data for each free agent
    for player in free_agents_list:
        avg_last_30 = player.stats.get('2026_last_30', {}).get('applied_avg', 0.0)

        # Filter by minimum average points
        if avg_last_30 >= min_avg_points:
            player_data = build_free_agent_data(
                all_players, player, waiver_player_ids,
                recent_transactions, league, week_index,
                pro_schedule_data
            )
            free_agents_dict[player.playerId] = player_data

    # Sort by avg_last_30 descending
    sorted_free_agents = sorted(
        free_agents_dict.values(),
        key=lambda x: x['scoring']['avg_last_30'],
        reverse=True
    )

    # Build response
    response = {
        'matchup_context': {
            'week_index': week_index,
            'date_range': {
                'start_date': start_date.strftime("%Y-%m-%d"),
                'end_date': end_date.strftime("%Y-%m-%d")
            },
            'days_in_period': 7
        },
        'free_agents': sorted_free_agents[:limit],
        'summary': {
            'total_free_agents_analyzed': len(free_agents_list),
            'returned': min(limit, len(sorted_free_agents)),
            'min_avg_points_filter': min_avg_points
        }
    }

    # Add roster if available
    if roster_data:
        response['roster'] = roster_data

    return response
