import argparse
from espn_api.basketball import League
from test_utils.create_league import create_league
from collections import defaultdict

def get_all_players(league):
    players = []
    for team in league.teams:
        players.extend(team.roster)
    players.extend(league.free_agents(size=1000))
    unique_players = {p.playerId: p for p in players}
    return list(unique_players.values())

def main():
    league = create_league(year=2025)
    players = get_all_players(league)

    # Dictionary to hold team stats
    team_stats = defaultdict(lambda: {'total_fpts': 0.0, 'total_games': 0})

    for player in players:
        stats = player.stats.get('2025_total', {})
        total_fpts = stats.get('applied_total', 0.0)
        avg_fpts = stats.get('applied_avg', 0.0)
        # Calculate games played for this player
        gp = int(round(total_fpts / avg_fpts)) if avg_fpts > 0 else 0
        nba_team = getattr(player, 'proTeam', 'Unknown')
        team_stats[nba_team]['total_fpts'] += total_fpts
        team_stats[nba_team]['total_games'] += gp

    # Output header
    print("NBA Team\tTotal FPTS\tTotal Games\tAvg FPTS per Game")
    for team, stats in sorted(team_stats.items()):
        total_fpts = stats['total_fpts']
        total_games = stats['total_games']
        avg_fpts_per_game = total_fpts / total_games if total_games > 0 else 0.0
        print(f"{team}\t{total_fpts:.2f}\t{total_games}\t{avg_fpts_per_game:.2f}")

if __name__ == '__main__':
    main()