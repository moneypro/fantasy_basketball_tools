from espn_api.basketball import League
from test_utils.create_league import create_league

def get_all_players_team_map(league, year):
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

def passes_filters(player_2025, player_2026):
    # Rule-based filter: extend this function for more rules
    if player_2025['avg_fpts'] < 10:
        return False
    if player_2026['team_abbr'] == "FA":
        return False
    return True

def main():
    league_2025 = create_league(year=2025)
    league_2026 = create_league(year=2026)

    players_2025 = get_all_players_team_map(league_2025, 2025)
    players_2026 = get_all_players_team_map(league_2026, 2026)

    # Collect filtered players who changed teams
    changed_players = []
    for pid, info_2025 in players_2025.items():
        info_2026 = players_2026.get(pid)
        if info_2026 and info_2025['team_abbr'] != info_2026['team_abbr']:
            if passes_filters(info_2025, info_2026):
                changed_players.append({
                    'name': info_2025['name'],
                    'avg_fpts': info_2025['avg_fpts'],
                    'from_team': info_2025['team_abbr'],
                    'to_team': info_2026['team_abbr']
                })

    # Sort by avg_fpts descending
    changed_players.sort(key=lambda x: x['avg_fpts'], reverse=True)

    print("Players who changed NBA teams from 2025 to 2026 (filtered & ranked by avg FPTS):")
    for player in changed_players:
        print(f"{player['name']}: {player['from_team']} (2025, {player['avg_fpts']:.1f} avg) -> {player['to_team']} (2026)")

    print("\nRookies in 2026 (not present in 2025, filtered):")
    for pid, info_2026 in players_2026.items():
        if pid not in players_2025:
            if info_2026['team_abbr'] != "FA":
                print(f"{info_2026['name']}: {info_2026['team_abbr']} (2026)")

    print("\nPlayers who left the league after 2025 (filtered):")
    for pid, info_2025 in players_2025.items():
        if pid not in players_2026:
            if info_2025['avg_fpts'] >= 10:
                print(f"{info_2025['name']}: {info_2025['team_abbr']} (2025, {info_2025['avg_fpts']:.1f} avg)")

if __name__ == '__main__':
    main()