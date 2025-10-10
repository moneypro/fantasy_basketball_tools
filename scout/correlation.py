import argparse
from espn_api.basketball import League
from test_utils.create_league import create_league
from collections import defaultdict
from nba_api.stats.endpoints import leaguedashteamstats
from nba_api.stats.static import teams as nba_teams_static
import pandas as pd
from scipy.stats import pearsonr
from sklearn.decomposition import PCA

def get_all_players(league):
    players = []
    for team in league.teams:
        players.extend(team.roster)
    players.extend(league.free_agents(size=1000))
    unique_players = {p.playerId: p for p in players}
    return list(unique_players.values())

def get_team_advanced_stats(season='2024-25'):
    stats = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        measure_type_detailed_defense='Advanced',
        last_n_games=30,
    )
    df = stats.get_data_frames()[0]
    # Use TEAM_ID for matching
    return df.set_index('TEAM_ID')[['TEAM_NAME', 'OFF_RATING', 'DEF_RATING', 'PACE']]

def build_team_id_map():
    nba_teams = nba_teams_static.get_teams()
    # Map abbreviation to TEAM_ID
    abbr_to_id = {}
    for t in nba_teams:
        abbr_to_id[t['abbreviation']] = t['id']
    return abbr_to_id

def main():
    league = create_league(year=2025)
    players = get_all_players(league)

    # Build abbreviation to TEAM_ID map
    abbr_to_id = build_team_id_map()

    # Aggregate fantasy stats by team abbreviation
    team_fantasy = defaultdict(lambda: {'total_fpts': 0.0, 'total_games': 0})

    for player in players:
        stats = player.stats.get('2025_total', {})
        total_fpts = stats.get('applied_total', 0.0)
        avg_fpts = stats.get('applied_avg', 0.0)
        gp = int(round(total_fpts / avg_fpts)) if avg_fpts > 0 else 0
        nba_team_abbr = getattr(player, 'proTeam', 'Unknown')
        team_fantasy[nba_team_abbr]['total_fpts'] += total_fpts
        team_fantasy[nba_team_abbr]['total_games'] += gp

    # Get advanced stats from nba_api
    adv_stats_df = get_team_advanced_stats(season='2024-25')

    # Merge fantasy and advanced stats
    data = []
    for abbr, stats in team_fantasy.items():
        team_id = abbr_to_id.get(abbr)
        if team_id in adv_stats_df.index:
            adv_row = adv_stats_df.loc[team_id]
            data.append({
                'abbr': abbr,
                'team_name': adv_row['TEAM_NAME'],
                'total_fpts': stats['total_fpts'],
                'off_rating': adv_row['OFF_RATING'],
                'def_rating': adv_row['DEF_RATING'],
                'pace': adv_row['PACE']
            })

    df = pd.DataFrame(data)

    # Print merged data
    print("Abbr\tTeam Name\tTotal FPTS\tOffensive Rating (Last 30)\tDefensive Rating (Last 30)\tPace (Last 30)")
    for _, row in df.iterrows():
        print(f"{row['abbr']}\t{row['team_name']}\t{row['total_fpts']:.2f}\t{row['off_rating']:.2f}\t{row['def_rating']:.2f}\t{row['pace']:.2f}")

    # Correlation analysis
    corr_fpts_off = df['total_fpts'].corr(df['off_rating'])
    corr_fpts_def = df['total_fpts'].corr(df['def_rating'])
    corr_fpts_pace = df['total_fpts'].corr(df['pace'])

    print("\nCorrelation Results:")
    print(f"Correlation between Total FPTS and Offensive Rating: {corr_fpts_off:.3f}")
    print(f"Correlation between Total FPTS and Defensive Rating: {corr_fpts_def:.3f}")
    print(f"Correlation between Total FPTS and Pace: {corr_fpts_pace:.3f}")

    # Optional: PCA
    features = df[['total_fpts', 'off_rating', 'def_rating', 'pace']]
    pca = PCA(n_components=2)
    principal_components = pca.fit_transform(features)
    explained_var = pca.explained_variance_ratio_

    print("\nPCA Explained Variance Ratios:")
    print(f"PC1: {explained_var[0]:.3f}, PC2: {explained_var[1]:.3f}")
    print("PCA Components (loadings):")
    print(pd.DataFrame(pca.components_, columns=features.columns, index=['PC1', 'PC2']))

    # Show each team's projection onto the principal components
    df_pca = df.copy()
    df_pca['PC1'] = principal_components[:, 0]
    df_pca['PC2'] = principal_components[:, 1]
    print("\nTeams projected onto principal components:")
    print(df_pca[['abbr', 'team_name', 'PC1', 'PC2']])

if __name__ == '__main__':
    main()