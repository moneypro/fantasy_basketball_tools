"""Players changed team analysis - refactored for API use."""
from dataclasses import dataclass
from typing import List, Dict, Any

from espn_api.basketball import League
from utils.create_league import create_league


@dataclass
class PlayerTeamChange:
    """Player who changed NBA teams."""
    name: str
    avg_fpts: float
    from_team: str
    to_team: str


@dataclass
class PlayerRookie:
    """Rookie player in 2026."""
    name: str
    team: str
    avg_fpts: float


@dataclass
class PlayerDeparture:
    """Player who left the league."""
    name: str
    last_team: str
    avg_fpts: float


@dataclass
class TeamChangesResult:
    """Complete team changes analysis."""
    changed_teams: List[PlayerTeamChange]
    rookies: List[PlayerRookie]
    departures: List[PlayerDeparture]
    total_changed: int
    total_rookies: int
    total_departures: int


def get_all_players_team_map(league: League, year: int) -> Dict[int, Dict[str, Any]]:
    """Get all players and their team mapping for a given year.
    
    Args:
        league: ESPN League object
        year: Year to get players for
        
    Returns:
        Dictionary of player_id -> {name, team_abbr, avg_fpts}
    """
    player_team = {}
    # Add all players from team rosters
    for team in league.teams:
        for player in team.roster:
            player_team[player.playerId] = {
                'name': player.name,
                'team_abbr': getattr(player, 'proTeam', 'Unknown'),
                'avg_fpts': player.stats.get(f'{year}_total', {}).get('applied_avg', 0.0)
            }
    # Add all free agents (may overwrite, but that's fine for this validation)
    for player in league.free_agents(size=1000):
        player_team[player.playerId] = {
            'name': player.name,
            'team_abbr': getattr(player, 'proTeam', 'Unknown'),
            'avg_fpts': player.stats.get(f'{year}_total', {}).get('applied_avg', 0.0)
        }
    return player_team


def passes_filters(player_2025: Dict[str, Any], player_2026: Dict[str, Any]) -> bool:
    """Check if a player passes filtering criteria.
    
    Args:
        player_2025: Player info from 2025
        player_2026: Player info from 2026
        
    Returns:
        True if player passes filters, False otherwise
    """
    # Rule-based filter: extend this function for more rules
    if player_2025['avg_fpts'] < 10:
        return False
    if player_2026['team_abbr'] == "FA":
        return False
    return True


def analyze_team_changes() -> TeamChangesResult:
    """Analyze players who changed teams between 2025 and 2026.
    
    Returns:
        TeamChangesResult with detailed breakdown
    """
    league_2025 = create_league(year=2025)
    league_2026 = create_league(year=2026)

    players_2025 = get_all_players_team_map(league_2025, 2025)
    players_2026 = get_all_players_team_map(league_2026, 2026)

    # Collect filtered players who changed teams
    changed_teams_list = []
    for pid, info_2025 in players_2025.items():
        info_2026 = players_2026.get(pid)
        if info_2026 and info_2025['team_abbr'] != info_2026['team_abbr']:
            if passes_filters(info_2025, info_2026):
                changed_teams_list.append(PlayerTeamChange(
                    name=info_2025['name'],
                    avg_fpts=round(info_2025['avg_fpts'], 2),
                    from_team=info_2025['team_abbr'],
                    to_team=info_2026['team_abbr']
                ))

    # Sort by avg_fpts descending
    changed_teams_list.sort(key=lambda x: x.avg_fpts, reverse=True)

    # Collect rookies in 2026 (not present in 2025, filtered)
    rookies_list = []
    for pid, info_2026 in players_2026.items():
        if pid not in players_2025:
            if info_2026['team_abbr'] != "FA":
                rookies_list.append(PlayerRookie(
                    name=info_2026['name'],
                    team=info_2026['team_abbr'],
                    avg_fpts=round(info_2026['avg_fpts'], 2)
                ))

    # Sort rookies by avg_fpts descending
    rookies_list.sort(key=lambda x: x.avg_fpts, reverse=True)

    # Collect players who left the league after 2025 (filtered)
    departures_list = []
    for pid, info_2025 in players_2025.items():
        if pid not in players_2026:
            if info_2025['avg_fpts'] >= 10:
                departures_list.append(PlayerDeparture(
                    name=info_2025['name'],
                    last_team=info_2025['team_abbr'],
                    avg_fpts=round(info_2025['avg_fpts'], 2)
                ))

    # Sort departures by avg_fpts descending
    departures_list.sort(key=lambda x: x.avg_fpts, reverse=True)

    return TeamChangesResult(
        changed_teams=changed_teams_list,
        rookies=rookies_list,
        departures=departures_list,
        total_changed=len(changed_teams_list),
        total_rookies=len(rookies_list),
        total_departures=len(departures_list)
    )
