from typing import Optional
import tabulate
from IPython.display import HTML
from espn_api.basketball import League
from predict.internal.roster_week_predictor import RosterWeekPredictor
from test_utils.create_league import create_league
from common.styling import get_table_css
from common.week import Week
import os

def get_tuple_average(tup):
    return (tup[0] + tup[1]) / 2

def predict_match_up(league: League, week_index, team_scores, number_of_games_team_name_map) -> str:
    match_up_points = [
        ["Home Team", "Estimate Points", "# of Games", "Away Team", "Estimate Points", "# of Games", "+/-"]
    ]
    for matchup in league.scoreboard(week_index):
        home_team_average = round(team_scores[matchup.home_team.team_name][-1])
        away_team_average = round(team_scores[matchup.away_team.team_name][-1])
        match_up_points.append(
            [
                matchup.home_team.team_name,
                home_team_average,
                number_of_games_team_name_map[matchup.home_team.team_name],
                matchup.away_team.team_name,
                away_team_average,
                number_of_games_team_name_map[matchup.away_team.team_name],
                home_team_average - away_team_average
            ]
        )
    return tabulate.tabulate(match_up_points, tablefmt='html', headers="firstrow")

def predict_week(league: League, week_index: int, day_of_week_override: int = 0, injuryStatusList=['ACTIVE']):
    predicted_points_team_name_map = {}
    number_of_games_team_name_map = {}
    team_scores = {}
    week = Week(league, week_index)
    for team in league.teams:
        predictor = RosterWeekPredictor(team.roster, week)
        predicted_points_team_name_map[team.team_name] = predictor.predict(
            daily_active_size=9, starting_day=day_of_week_override, injuryStatusList=injuryStatusList)
        number_of_games_team_name_map[team.team_name] = predictor.get_total_number_of_games(
            starting_day=day_of_week_override, injuryStatusList=injuryStatusList)
    for team in league.teams:
        predicted_points = predicted_points_team_name_map[team.team_name]
        team_scores[team.team_name] = predicted_points[0], predicted_points[1], get_tuple_average(predicted_points)
    return number_of_games_team_name_map, team_scores

def get_table_output_for_week(league, week_index, day_of_week_override: int = 0, injuryStatusList=['ACTIVE']):
    number_of_games_team_name_map, team_scores = predict_week(league, week_index, day_of_week_override, injuryStatusList)
    table_output = []
    for team_name, scores in team_scores.items():
        lo, hi, avg = scores
        table_output.append((team_name, number_of_games_team_name_map[team_name], lo, hi, avg))
    table_output.sort(reverse=True, key=lambda x: x[-1])
    table_output.insert(0, (
        "Team Name", "# of games", "Week {} Low".format(week_index), "Week {} High".format(week_index),
        "Week {} Avg".format(week_index)))
    return number_of_games_team_name_map, table_output, team_scores

def build_week_html(league, week_index, day_of_week_override=0):
    # Table 1: Active only
    _, table_active, team_scores_active = get_table_output_for_week(league, week_index, day_of_week_override, ['ACTIVE'])
    # Table 2: Active + DTD
    _, table_dtd, team_scores_dtd = get_table_output_for_week(league, week_index, day_of_week_override, ['ACTIVE', 'DAY_TO_DAY'])
    # Table 3: Active + DTD + OUT
    _, table_out, team_scores_out = get_table_output_for_week(league, week_index, day_of_week_override, ['ACTIVE', 'DAY_TO_DAY', 'OUT'])
    num_games_active_dict = {row[0]: row[1] for row in table_active[1:]}
    num_games_dtd_dict = {row[0]: row[1] for row in table_dtd[1:]}
    num_games_out_dict = {row[0]: row[1] for row in table_out[1:]}

    html = (
            f"<h2>Week {week_index} - Active Players Only</h2>"
            + tabulate.tabulate(table_active, tablefmt='html', headers="firstrow")
            + f"<h2>Week {week_index} - Including Day-to-Day (DTD)</h2>"
            + tabulate.tabulate(table_dtd, tablefmt='html', headers="firstrow")
            + f"<h2>Week {week_index} - Including OUT</h2>"
            + tabulate.tabulate(table_out, tablefmt='html', headers="firstrow")
            + get_table_css()
            + f"<h2>Week {week_index} Matchups (Active Only)</h2>"
            + predict_match_up(league, week_index, team_scores_active, num_games_active_dict)
            + f"<h2>Week {week_index} Matchups (DTD Included)</h2>"
            + predict_match_up(league, week_index, team_scores_dtd, num_games_dtd_dict)
            + f"<h2>Week {week_index} Matchups (OUT Included)</h2>"
            + predict_match_up(league, week_index, team_scores_out, num_games_out_dict)
    )
    return HTML(html).data

def save_week_forecast(league, week_index, day_of_week_override, output_dir):
    week_folder = os.path.join(output_dir, f"week_{week_index}_forecast")
    os.makedirs(week_folder, exist_ok=True)
    week_html = build_week_html(league, week_index, day_of_week_override)
    output_path = os.path.join(week_folder, "index.html")
    with open(output_path, 'w') as f:
        f.write(week_html)
    print(f"Forecast for week {week_index} written to {output_path}")

def predict_all(
        week_index_override: Optional[int] = None,
        day_of_week_override: int = 0,
        output_dir: str = "./forecasts"
):
    league = create_league(use_local_cache=False)
    week_index = week_index_override if week_index_override else league.currentMatchupPeriod

    save_week_forecast(league, week_index, day_of_week_override, output_dir)
    save_week_forecast(league, week_index + 1, day_of_week_override, output_dir)

if __name__ == '__main__':
    predict_all(day_of_week_override=4)