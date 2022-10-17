import tabulate

from common.aws_email import send_email
from common.io import get_match_up_output_html_path
from common.styling import get_table_css
from common.week import Week
from predict.internal.roster_week_predictor import RosterWeekPredictor
from test_utils.create_league import create_league
from IPython.display import HTML, display


def get_tuple_average(tup):
    return (tup[0] + tup[1]) / 2


def predict_all(week_index: int = 1):
    predicted_points_team_name_map = {}
    number_of_games_team_name_map = {}
    league = create_league()
    team_scores = {}
    week = Week(league, week_index)
    for team in league.teams:
        predictor = RosterWeekPredictor(team.roster, week)
        predicted_points_team_name_map[team.team_name] = predictor.predict()
        number_of_games_team_name_map[team.team_name] = predictor.get_total_number_of_games()
    for team in league.teams:
        predicted_points = predicted_points_team_name_map[team.team_name]
        team_scores[team.team_name] = predicted_points[0], predicted_points[1], get_tuple_average(predicted_points)
    table_output = []
    for team_name, scores in team_scores.items():
        lo, hi, avg = scores
        table_output.append((team_name, number_of_games_team_name_map[team_name], lo, hi, avg))
    table_output.sort(reverse=True, key=lambda x: x[-1])
    table_output.insert(0, ("Team Name", "# of games", "Low", "High", "Avg"))
    table_content = tabulate.tabulate(table_output, tablefmt='html') + get_table_css()
    html = HTML(table_content)

    data = html.data
    with open(get_match_up_output_html_path(league.league_id, week_index), 'w') as f:
        f.write(data)
    send_email("Week {} Outlook for League {}".format(week_index, league.league_id), data)

if __name__ == '__main__':
    predict_all()
