import argparse
from espn_api.basketball import League
from test_utils.create_league import create_league

POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F']

def get_all_players(league):
    players = []
    for team in league.teams:
        players.extend(team.roster)
    players.extend(league.free_agents(size=1000))
    unique_players = {p.playerId: p for p in players}
    return unique_players

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

        eligible = set(player_2025.eligibleSlots) if hasattr(player_2025, "eligibleSlots") else set()
        eligibility = [str(pos in eligible) for pos in POSITIONS]
        player_points.append((
            player_2025.name, avg_30, total_30, gp_30, gp_year, avg_proj, gp_proj, *eligibility
        ))

    # Sort by average points descending (last 30 days)
    player_points.sort(key=lambda x: x[1], reverse=True)

    # Output header
    print("Player\tAvg FPTS (30d)\tTotal FPTS (30d)\tGP (Last 30)\tGP\t2026 Avg FPTS\tGP projected\tPG\tSG\tSF\tPF\tC\tG\tF")
    for row in player_points[:limit]:
        print("\t".join([str(x) for x in row]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scout and rank fantasy basketball players by average and total points (last 30 days), and 2026 projections.")
    parser.add_argument('--limit', type=int, default=100, help='Number of top players to display')
    args = parser.parse_args()
    main(args.limit)