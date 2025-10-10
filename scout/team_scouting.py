from espn_api.basketball import League
from test_utils.create_league import create_league
from collections import defaultdict
from nba_api.stats.endpoints import leaguedashteamstats
from nba_api.stats.static import teams as nba_teams_static

def get_all_players(league):
    players = []
    for team in league.teams:
        players.extend(team.roster)
    players.extend(league.free_agents(size=1000))
    unique_players = {p.playerId: p for p in players}
    return unique_players

def build_team_id_map():
    nba_teams = nba_teams_static.get_teams()
    abbr_to_id = {}
    for t in nba_teams:
        abbr_to_id[t['abbreviation']] = t['id']
    return abbr_to_id

def main():
    league_2025 = create_league(year=2025)
    league_2026 = create_league(year=2026)
    players_2025 = get_all_players(league_2025)
    players_2026 = get_all_players(league_2026)

    # 1. Total FPTS from original 2025 roster
    team_fpts_2025 = defaultdict(float)
    for player in players_2025.values():
        stats_2025 = player.stats.get('2025_total', {})
        total_fpts = stats_2025.get('applied_total', 0.0)
        pro_team_2025 = getattr(player, 'proTeam', 'Unknown')
        if pro_team_2025 != 'Unknown' and pro_team_2025 != 'FA':
            team_fpts_2025[pro_team_2025] += total_fpts

    # 2. Total FPTS from new 2026 roster (using 2025 stats)
    # Map playerId to 2026 pro team
    playerid_to_2026_team = {pid: getattr(player, 'proTeam', 'Unknown') for pid, player in players_2026.items()}
    team_fpts_2026 = defaultdict(float)
    for player_id, player in players_2025.items():
        pro_team_2026 = playerid_to_2026_team.get(player_id, 'Unknown')
        stats_2025 = player.stats.get('2025_total', {})
        total_fpts = stats_2025.get('applied_total', 0.0)
        if pro_team_2026 != 'Unknown' and pro_team_2026 != 'FA':
            team_fpts_2026[pro_team_2026] += total_fpts

    abbr_to_id = build_team_id_map()
    # Get advanced stats for reference
    adv_stats = leaguedashteamstats.LeagueDashTeamStats(
        season='2024-25',
        measure_type_detailed_defense='Advanced',
        last_n_games=30,
    ).get_data_frames()[0]
    adv_stats = adv_stats.set_index('TEAM_ID')[['OFF_RATING']].to_dict(orient='index')

    # Union of all team abbreviations in either year
    all_team_abbrs = set(team_fpts_2025.keys()) | set(team_fpts_2026.keys())

    print("NBA Team\t2025 Roster FPTS\t2026 Roster FPTS\tDifference\tOffensive Rating Last 30")
    for abbr in sorted(all_team_abbrs):
        fpts_2025 = team_fpts_2025.get(abbr, 0.0)
        fpts_2026 = team_fpts_2026.get(abbr, 0.0)
        diff = fpts_2026 - fpts_2025
        team_id = abbr_to_id.get(abbr)
        off_rating = adv_stats.get(team_id, {}).get('OFF_RATING', '')
        print(f"{abbr}\t{fpts_2025:.2f}\t{fpts_2026:.2f}\t{diff:+.2f}\t{off_rating}")

if __name__ == '__main__':
    main()