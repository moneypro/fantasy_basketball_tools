import argparse
from espn_api.basketball import League
from test_utils.create_league import create_league

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
        stats_30 = player.stats.get('2025_last_30', {})
        avg = stats_30.get('applied_avg', 0.0)
        total = stats_30.get('applied_total', 0.0)
        if avg > 0:
            gp = int(round(total / avg))
        else:
            gp = 0
        eligible_slots = ", ".join(player.eligibleSlots) if hasattr(player, "eligibleSlots") else "N/A"
        player_points.append((player.name, avg, total, gp, eligible_slots))
    # Sort by average points descending
    player_points.sort(key=lambda x: x[1], reverse=True)

    # Output
    print(f"{'Player':30} {'Avg FPTS (30d)':>15} {'Total FPTS (30d)':>18} {'GP':>5} {'Eligible Slots':>25}")
    print('-' * 110)
    for name, avg, total, gp, eligible_slots in player_points[:limit]:
        print(f"{name:30} {avg:15.2f} {total:18.2f} {gp:5} {eligible_slots:>25}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scout and rank fantasy basketball players by average and total points (last 30 days).")
    parser.add_argument('--limit', type=int, default=20, help='Number of top players to display')
    args = parser.parse_args()
    main(args.limit)