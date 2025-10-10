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
    return list(unique_players.values())

def main(limit):
    league = create_league(year=2025)
    players = get_all_players(league)
    player_points = []
    for player in players:
        # Last 30 days stats
        stats_30 = player.stats.get('2025_last_30', {})
        avg_30 = stats_30.get('applied_avg', 0.0)
        total_30 = stats_30.get('applied_total', 0.0)
        gp_30 = int(round(total_30 / avg_30)) if avg_30 > 0 else 0

        # Full season stats
        stats_total = player.stats.get('2025_total', {})
        avg_year = stats_total.get('applied_avg', 0.0)
        total_year = stats_total.get('applied_total', 0.0)
        gp_year = int(round(total_year / avg_year)) if avg_year > 0 else 0

        eligible = set(player.eligibleSlots) if hasattr(player, "eligibleSlots") else set()
        eligibility = [str(pos in eligible) for pos in POSITIONS]
        player_points.append((player.name, avg_30, total_30, gp_30, gp_year, *eligibility))
    # Sort by average points descending (last 30 days)
    player_points.sort(key=lambda x: x[1], reverse=True)

    # Output header
    print("Player\tAvg FPTS (30d)\tTotal FPTS (30d)\tGP (Last 30)\tGP\tPG\tSG\tSF\tPF\tC\tG\tF")
    for row in player_points[:limit]:
        print("\t".join([str(x) for x in row]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scout and rank fantasy basketball players by average and total points (last 30 days).")
    parser.add_argument('--limit', type=int, default=100, help='Number of top players to display')
    args = parser.parse_args()
    main(args.limit)