import argparse
import math

from espn_api.basketball import League
from test_utils.create_league import create_league

POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F']

# Set your ratio and adjuster here
RATIO = 0.5      # e.g., 0.5 for equal weighting
ADJUSTER = 1.0   # e.g., 1.0 for full penalty, 0.5 for half penalty

def get_all_players(league):
    players = []
    for team in league.teams:
        players.extend(team.roster)
    players.extend(league.free_agents(size=1000))
    unique_players = {p.playerId: p for p in players}
    return unique_players

def calculate_final_score(avg_recent, avg_proj, gp_proj, ratio, adjuster):
    base_score = ratio * avg_recent + (1 - ratio) * avg_proj
    penalty_factor = 1 - adjuster * (82 - gp_proj) / 82 if gp_proj <= 82 else 1
    return base_score * penalty_factor

def main(limit):
    # Create both leagues
    league_2025 = create_league(year=2025)
    league_2026 = create_league(year=2026)

    # Get all players from both leagues, keyed by playerId
    players_2025 = get_all_players(league_2025)
    players_2026 = get_all_players(league_2026)

    player_points = []
    for player_id, player_2025 in players_2025.items():
        # Last 30 days stats (2025)
        stats_30 = player_2025.stats.get('2025_last_30', {})
        avg_30 = stats_30.get('applied_avg', 0.0)
        total_30 = stats_30.get('applied_total', 0.0)
        gp_30 = int(round(total_30 / avg_30)) if avg_30 > 0 else 0

        # Full season stats (2025)
        stats_total = player_2025.stats.get('2025_total', {})
        avg_year = stats_total.get('applied_avg', 0.0)
        total_year = stats_total.get('applied_total', 0.0)
        gp_year = int(round(total_year / avg_year)) if avg_year > 0 else 0

        # 2026 projected stats (from 2026 league, if available)
        player_2026 = players_2026.get(player_id)
        avg_proj = 0.0
        total_proj = 0.0
        gp_proj = 0
        if player_2026:
            stats_proj = player_2026.stats.get('2026_projected', {})
            avg_proj = stats_proj.get('applied_avg', 0.0)
            total_proj = stats_proj.get('applied_total', 0.0)
            gp_proj = int(round(total_proj / avg_proj)) if avg_proj > 0 else 0

        # Use season average if last 30 games played is too low
        avg_recent = avg_30 if gp_30 >= 5 else avg_year

        # Calculate final score
        final_score = calculate_final_score(avg_recent, avg_proj, gp_proj, RATIO, ADJUSTER)

        eligible = set(player_2025.eligibleSlots) if hasattr(player_2025, "eligibleSlots") else set()
        eligibility = [str(pos in eligible) for pos in POSITIONS]
        player_points.append((
            player_2025.name, avg_recent, total_30, gp_30, gp_year, avg_proj, gp_proj, final_score, *eligibility
        ))

    # Add rookies (in 2026 but not in 2025)
    for player_id, player_2026 in players_2026.items():
        if player_id not in players_2025:
            stats_proj = player_2026.stats.get('2026_projected', {})
            avg_proj = stats_proj.get('applied_avg', 0.0)
            total_proj = stats_proj.get('applied_total', 0.0)
            gp_proj = int(round(total_proj / avg_proj)) if avg_proj > 0 else 0

            if avg_proj > 0 and gp_proj > 0:
                avg_recent = "N/A"
                total_30 = "N/A"
                gp_30 = "N/A"
                gp_year = "N/A"
                # Use only projection for both avg_recent and avg_proj
                final_score = calculate_final_score(avg_proj, avg_proj, gp_proj, 0.0, ADJUSTER)
                eligible = set(player_2026.eligibleSlots) if hasattr(player_2026, "eligibleSlots") else set()
                eligibility = [str(pos in eligible) for pos in POSITIONS]
                player_points.append((
                    player_2026.name, avg_recent, total_30, gp_30, gp_year, avg_proj, gp_proj, final_score, *eligibility
                ))

    # Standardize final scores to [0, 100]
    scores = [x[7] for x in player_points]
    min_score = min(scores)
    max_score = max(scores)
    if max_score > min_score:
        standardized = [100 * (s - min_score) / (max_score - min_score) for s in scores]
    else:
        standardized = [100 for _ in scores]

    # Add standardized score to each row (replace final_score column)
    player_points = [
        row[:7] + (math.floor(standardized[i]),) + row[8:]
        for i, row in enumerate(player_points)
    ]

    # Sort by standardized score descending
    player_points.sort(key=lambda x: x[7], reverse=True)

    # Output header
    print("Player\tAvg FPTS (recent)\tTotal FPTS (30d)\tGP (Last 30)\tGP (2025)\t2026 Avg FPTS\tGP (2026)\tStandardized Score\tPG\tSG\tSF\tPF\tC\tG\tF")
    for row in player_points[:limit]:
        print("\t".join([str(x) for x in row]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scout and rank fantasy basketball players by custom score using last 30 days, projections, and missing games penalty.")
    parser.add_argument('--limit', type=int, default=200, help='Number of top players to display')
    args = parser.parse_args()
    main(args.limit)