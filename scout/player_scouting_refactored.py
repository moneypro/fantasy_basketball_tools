"""Player scouting and evaluation utilities - refactored for API use.

This module provides data structure returns instead of stdout printing.
"""
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, Tuple, List, Any, Optional

from nba_api.stats.endpoints import leaguedashteamstats

from utils.create_league import create_league
from utils.shared_player_utils import get_all_players, build_team_id_map
import config

# Constants from original code
ALPHA = 0.3  # Team context weight
BETA = 0.2   # Offensive rating weight


@dataclass
class PlayerStats:
    """Statistics for a single player."""
    player_id: int
    name: str
    avg_recent: float  # Average FPTS from recent games
    total_30: float    # Total FPTS in last 30 days
    gp_30: int         # Games played in last 30 days
    gp_year: int       # Games played this year
    avg_proj: float    # Projected average FPTS
    gp_proj: int       # Projected games played
    standardized_score: float  # Standardized score (0-100)
    potential_upside: float    # Potential upside score
    team_rank: int     # Rank within their NBA team
    eligibility: Dict[str, bool]  # Position eligibility (PG, SG, SF, PF, C, G, F)


@dataclass
class PlayerUpside:
    """Player with upside difference analysis."""
    name: str
    standardized_score: float
    potential_upside: float
    difference: float  # potential_upside - standardized_score


@dataclass
class ScoutingResult:
    """Complete scouting result for a set of players."""
    players: List[PlayerStats]
    upside_differences: List[PlayerUpside]
    total_players_analyzed: int
    limit_returned: int


def calculate_final_score(avg_recent: float, avg_proj: float, gp_proj: int) -> float:
    """Calculate final player score with games played adjustment.
    
    Args:
        avg_recent: Average fantasy points from recent games
        avg_proj: Projected average fantasy points
        gp_proj: Projected games played
        
    Returns:
        Adjusted final score
    """
    base_score = config.RECENT_STATS_RATIO * avg_recent + (1 - config.RECENT_STATS_RATIO) * avg_proj
    penalty_factor = 1 - config.ADJUSTER * (82 - gp_proj) / 82 if gp_proj <= 82 else 1
    return base_score * penalty_factor


def get_team_context(players: Dict[int, Any], player_scores: Dict[int, float]) -> Tuple[Dict, Dict, float, float]:
    """Get team context for player evaluation.
    
    Args:
        players: Dictionary of players by ID
        player_scores: Dictionary of player scores by ID
        
    Returns:
        Tuple of (team_talent, team_off_rating, max_team_talent, avg_off_rating)
    """
    # Group player scores by team
    team_to_scores: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
    for pid, player in players.items():
        abbr = getattr(player, 'proTeam', 'Unknown')
        if abbr != 'Unknown' and abbr != 'FA':
            team_to_scores[abbr].append((pid, player_scores.get(pid, 0.0)))

    # For each team, sum top N teammate scores (excluding self)
    team_talent: Dict[str, float] = {}
    for abbr, pid_scores in team_to_scores.items():
        scores = sorted([score for pid, score in pid_scores], reverse=True)
        team_talent[abbr] = sum(scores[:config.TOP_TEAMMATES_COUNT])

    max_team_talent = max(team_talent.values()) if team_talent else 1.0

    # Get offensive ratings
    abbr_to_id = build_team_id_map()
    adv_stats = leaguedashteamstats.LeagueDashTeamStats(
        season=config.DEFAULT_STATS_SEASON,
        measure_type_detailed_defense='Advanced',
        last_n_games=30,
    ).get_data_frames()[0]
    adv_stats_dict = adv_stats.set_index('TEAM_ID')[['OFF_RATING']].to_dict(orient='index')
    team_off_rating: Dict[str, float] = {}
    for abbr in team_talent:
        team_id = abbr_to_id.get(abbr)
        team_off_rating[abbr] = adv_stats_dict.get(team_id, {}).get('OFF_RATING', 110.0)

    avg_off_rating = sum(team_off_rating.values()) / len(team_off_rating) if team_off_rating else 110.0

    return team_talent, team_off_rating, max_team_talent, avg_off_rating


def get_team_rankings(player_points, standardized_scores, players_2026):
    """Returns a dict: player_id -> rank (1 = top option on team)"""
    # Build team -> list of (player_id, standardized_score)
    team_to_players = defaultdict(list)
    for i, row in enumerate(player_points):
        player_id = row[0]
        player_obj = players_2026.get(player_id)
        team = getattr(player_obj, 'proTeam', 'Unknown') if player_obj else 'Unknown'
        team_to_players[team].append((player_id, standardized_scores[i]))
    # For each team, sort and assign rank
    player_rank = {}
    for team, plist in team_to_players.items():
        plist_sorted = sorted(plist, key=lambda x: x[1], reverse=True)
        for rank, (pid, _) in enumerate(plist_sorted, 1):
            player_rank[pid] = rank
    return player_rank


def scout_players(limit: int = 200) -> ScoutingResult:
    """Scout and analyze players, returning structured data.
    
    Args:
        limit: Number of top players to return
        
    Returns:
        ScoutingResult containing player stats and upside analysis
    """
    league_2026 = create_league(year=2026)
    players_2026 = get_all_players(league_2026)

    # Use dictionary instead of tuple for cleaner data structure
    players_data = {}

    # 1. Calculate player scores using only 2026 data
    for player_id, player_2026 in players_2026.items():
        # Get current season stats (2026_total)
        stats_total = player_2026.stats.get('2026_total', {})
        avg_year = stats_total.get('applied_avg', 0.0)
        total_year = stats_total.get('applied_total', 0.0)
        gp_year = int(round(total_year / avg_year)) if avg_year > 0 else 0

        # Get last 30 days stats
        stats_30 = player_2026.stats.get('2026_last_30', {})
        avg_30 = stats_30.get('applied_avg', 0.0)
        total_30 = stats_30.get('applied_total', 0.0)
        gp_30 = int(round(total_30 / avg_30)) if avg_30 > 0 else 0

        # Get projected stats
        stats_proj = player_2026.stats.get('2026_projected', {})
        avg_proj = stats_proj.get('applied_avg', 0.0)
        total_proj = stats_proj.get('applied_total', 0.0)
        gp_proj = int(round(total_proj / avg_proj)) if avg_proj > 0 else 0

        # Use last 30 days if available, otherwise use year average
        avg_recent = avg_30 if gp_30 >= 5 else avg_year
        final_score = calculate_final_score(avg_recent, avg_proj, gp_proj)

        eligible = set(player_2026.eligibleSlots) if hasattr(player_2026, "eligibleSlots") else set()
        eligibility_dict = {pos: pos in eligible for pos in config.PRIMARY_POSITIONS}
        
        # Only add player if they have meaningful stats or projections
        if avg_year > 0 or avg_proj > 0:
            players_data[player_id] = {
                'player_id': player_id,
                'name': player_2026.name,
                'avg_recent': avg_recent,
                'total_30': total_30,
                'gp_30': gp_30,
                'gp_year': gp_year,
                'avg_proj': avg_proj,
                'gp_proj': gp_proj,
                'final_score': final_score,
                'eligibility': eligibility_dict,
                'is_rookie': avg_year == 0 and avg_proj > 0  # Rookie if no year stats but has projections
            }

    # 2. Standardize final scores to [0, 100]
    scores = [p['final_score'] for p in players_data.values()]
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 1
    
    if max_score > min_score:
        for player_id in players_data:
            raw_score = players_data[player_id]['final_score']
            players_data[player_id]['standardized_score'] = 100 * (raw_score - min_score) / (max_score - min_score)
    else:
        for player_id in players_data:
            players_data[player_id]['standardized_score'] = 100.0

    # 3. Build player_scores dict for team context
    player_scores = {player_id: data['standardized_score'] for player_id, data in players_data.items()}

    # 4. Get team context
    team_talent, team_off_rating, max_team_talent, avg_off_rating = get_team_context(players_2026, player_scores)
    player_rank = get_team_rankings_refactored(players_data, players_2026)
    
    # 5. Calculate potential_upside for each player
    for player_id, data in players_data.items():
        player_obj = players_2026.get(player_id)
        team = getattr(player_obj, 'proTeam', 'Unknown') if player_obj else 'Unknown'
        player_score = data['standardized_score']
        team_score = team_talent.get(team, 0.0) - player_score
        off_rating = team_off_rating.get(team, avg_off_rating)
        potential_upside = player_score * (1 + ALPHA * (1 - team_score / max_team_talent)) * (off_rating / avg_off_rating) ** BETA
        rank = player_rank.get(player_id, 0)
        
        data['potential_upside'] = potential_upside
        data['team_rank'] = rank

    # 6. Sort by standardized score descending
    sorted_players = sorted(players_data.items(), key=lambda x: x[1]['standardized_score'], reverse=True)

    # 7. Build result structure
    players_list = []
    for player_id, data in sorted_players[:limit]:
        player = PlayerStats(
            player_id=player_id,
            name=data['name'],
            avg_recent=data['avg_recent'],
            total_30=data['total_30'],
            gp_30=data['gp_30'],
            gp_year=data['gp_year'],
            avg_proj=data['avg_proj'],
            gp_proj=data['gp_proj'],
            standardized_score=round(data['standardized_score'], 2),
            potential_upside=round(data['potential_upside'], 2),
            team_rank=data['team_rank'],
            eligibility=data['eligibility']
        )
        players_list.append(player)

    # 8. Calculate upside differences
    upside_diffs = []
    for player_id, data in sorted_players:
        name = data['name']
        standardized_score = data['standardized_score']
        potential_upside = data['potential_upside']
        diff = potential_upside - standardized_score
        upside_diffs.append((diff, name, standardized_score, potential_upside))

    # Sort by absolute difference, descending
    upside_diffs.sort(key=lambda x: abs(x[0]), reverse=True)

    upside_list = [
        PlayerUpside(
            name=name,
            standardized_score=round(std_score, 2),
            potential_upside=round(pot_upside, 2),
            difference=round(diff, 2)
        )
        for diff, name, std_score, pot_upside in upside_diffs[:20]
    ]

    return ScoutingResult(
        players=players_list,
        upside_differences=upside_list,
        total_players_analyzed=len(players_data),
        limit_returned=min(limit, len(players_list))
    )


def get_team_rankings_refactored(players_data: Dict, players_2026: Dict) -> Dict:
    """Returns a dict: player_id -> rank (1 = top option on team)"""
    # Build team -> list of (player_id, standardized_score)
    team_to_players = defaultdict(list)
    for player_id, data in players_data.items():
        player_obj = players_2026.get(player_id)
        team = getattr(player_obj, 'proTeam', 'Unknown') if player_obj else 'Unknown'
        team_to_players[team].append((player_id, data['standardized_score']))
    
    # For each team, sort and assign rank
    player_rank = {}
    for team, plist in team_to_players.items():
        plist_sorted = sorted(plist, key=lambda x: x[1], reverse=True)
        for rank, (pid, _) in enumerate(plist_sorted, 1):
            player_rank[pid] = rank
    return player_rank
