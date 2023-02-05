from typing import Optional

import tabulate
from IPython.display import HTML
from espn_api.basketball import League

from predict.internal.roster_week_predictor import RosterWeekPredictor
from test_utils.create_league import create_league
from common.aws_email import send_email
from common.io import get_match_up_output_html_path
from common.styling import get_table_css
from common.week import Week


def get_tuple_average(tup):
    return (tup[0] + tup[1]) / 2


def predict_match_up(league: League, week_index, team_scores, number_of_games_team_name_map) -> str:
    match_up_points = [
        ["Home Team", "Estimate Points", "# of Games", "Away Team", "Estimate Points", "# of Games", "+/-"]]
    for matchup in league.scoreboard(week_index):
        home_team_average = team_scores[matchup.home_team.team_name][-1]
        away_team_average = team_scores[matchup.away_team.team_name][-1]
        match_up_points.append(
            [matchup.home_team.team_name, home_team_average, number_of_games_team_name_map[matchup.home_team.team_name],
             matchup.away_team.team_name, away_team_average, number_of_games_team_name_map[matchup.away_team.team_name],
             home_team_average - away_team_average])
    return tabulate.tabulate(match_up_points, tablefmt='html')


def predict_week(league: League, week_index: int):
    predicted_points_team_name_map = {}
    number_of_games_team_name_map = {}
    team_scores = {}
    week = Week(league, week_index)
    for team in league.teams:
        predictor = RosterWeekPredictor(team.roster, week)
        predicted_points_team_name_map[team.team_name] = predictor.predict()
        number_of_games_team_name_map[team.team_name] = predictor.get_total_number_of_games()
    for team in league.teams:
        predicted_points = predicted_points_team_name_map[team.team_name]
        team_scores[team.team_name] = predicted_points[0], predicted_points[1], get_tuple_average(predicted_points)
    return number_of_games_team_name_map, team_scores


def predict_all(week_index_override: Optional[int] = None):
    league = create_league()
    week_index = week_index_override if week_index_override else league.currentMatchupPeriod
    number_of_games_team_name_map, table_output, team_scores = get_table_output_for_week(league, week_index)
    number_of_games_team_name_map_next, table_output_next, team_scores_next = get_table_output_for_week(league, week_index + 1)
    table_content = (tabulate.tabulate(table_output, tablefmt='html')
    + tabulate.tabulate(table_output_next, tablefmt='html')
                     + get_table_css()
                     + predict_match_up(league, week_index, team_scores, number_of_games_team_name_map)
                     + predict_match_up(league, week_index + 1, team_scores_next, number_of_games_team_name_map_next))
    html = HTML(table_content)

    data = html.data
    with open(get_match_up_output_html_path(league.league_id, week_index), 'w') as f:
        f.write(data)
    send_email("Week {} Outlook for League {}".format(week_index, league.league_id), data)


def get_table_output_for_week(league, week_index):
    number_of_games_team_name_map, team_scores = predict_week(league, week_index)
    table_output = []
    for team_name, scores in team_scores.items():
        lo, hi, avg = scores
        table_output.append((team_name, number_of_games_team_name_map[team_name], lo, hi, avg))
    table_output.sort(reverse=True, key=lambda x: x[-1])
    table_output.insert(0, (
    "Team Name", "# of games", "Week {} Low".format(week_index), "Week {} High".format(week_index),
    "Week {} Avg".format(week_index)))
    return number_of_games_team_name_map, table_output, team_scores


if __name__ == '__main__':
    predict_all()
