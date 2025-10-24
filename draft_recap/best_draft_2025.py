import collections
from predict.internal.roster_week_predictor import RosterWeekPredictor
from utils.create_league import create_league

def get_player_2025_points(league, player_id):
    return league.player_info(playerId=player_id).stats["2025_total"]['applied_total']

def get_player_name(league, player_id):
    return league.player_info(playerId=player_id).name

def calculate_drafted_team_points_and_top_and_worst_scorers(league, top_n=5, worst_n=3, worst_round_limit=10):
    # Map: team_id -> list of (playerId, round_num)
    team_to_players = collections.defaultdict(list)
    for pick in league.draft:
        team_id = pick.team.team_id
        player_id = pick.playerId
        round_num = pick.round_num
        team_to_players[team_id].append((player_id, round_num))

    # Map: team_id -> (total points, list of (player_name, points, round_num), list of (player_name, points, round_num))
    team_points = {}
    for team_id, player_info_list in team_to_players.items():
        player_points = []
        for player_id, round_num in player_info_list:
            points = get_player_2025_points(league, player_id)
            name = get_player_name(league, player_id)
            player_points.append((name, points, round_num))
        total_points = sum(points for name, points, round_num in player_points)
        # Sort players by points descending and take top N
        sorted_players = sorted(player_points, key=lambda x: x[1], reverse=True)
        top_scorers = sorted_players[:top_n]
        # For worst, only consider players drafted in round 10 or earlier
        eligible_worst = [p for p in sorted_players if p[2] <= worst_round_limit]
        worst_scorers = sorted(eligible_worst, key=lambda x: x[1])[:worst_n] if eligible_worst else []
        team_points[team_id] = (total_points, top_scorers, worst_scorers)
    return team_points

def best_drafted_teams_html(league, output_path="best_draft_2025.html"):
    team_points = calculate_drafted_team_points_and_top_and_worst_scorers(league, top_n=5, worst_n=3, worst_round_limit=10)
    team_id_to_name = {team.team_id: team.team_name for team in league.teams}
    sorted_teams = sorted(team_points.items(), key=lambda x: x[1][0], reverse=True)

    html = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>Drafted Team Rankings (2025 Points)</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; }",
        "table { border-collapse: collapse; margin-bottom: 2em; }",
        "th, td { border: 1px solid #ccc; padding: 8px 12px; }",
        "th { background: #f0f0f0; }",
        ".team-block { margin-bottom: 2em; }",
        ".team-title { font-size: 1.2em; font-weight: bold; margin-bottom: 0.5em; }",
        ".side-by-side { display: flex; gap: 2em; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Drafted Team Rankings (2025 Points)</h1>"
    ]

    for rank, (team_id, (points, top_scorers, worst_scorers)) in enumerate(sorted_teams, 1):
        html.append("<div class='team-block'>")
        html.append(f"<div class='team-title'>{rank}. {team_id_to_name.get(team_id, 'Unknown Team')}: <b>{int(points)}</b> points</div>")
        html.append("<div class='side-by-side'>")
        # Top 5 Scorers Table
        html.append("<table>")
        html.append("<tr><th colspan='3'>Top 5 Scorers</th></tr>")
        html.append("<tr><th>Player</th><th>Points</th><th>Round</th></tr>")
        for name, pts, round_num in top_scorers:
            html.append(f"<tr><td>{name}</td><td>{int(pts)}</td><td>{round_num}</td></tr>")
        html.append("</table>")
        # Worst 3 Players Table
        html.append("<table>")
        html.append("<tr><th colspan='3'>Worst 3 Players (Rounds 1-10)</th></tr>")
        html.append("<tr><th>Player</th><th>Points</th><th>Round</th></tr>")
        for name, pts, round_num in worst_scorers:
            html.append(f"<tr><td>{name}</td><td>{int(pts)}</td><td>{round_num}</td></tr>")
        html.append("</table>")
        html.append("</div>")  # close side-by-side
        html.append("</div>")  # close team-block

    html.append("</body></html>")

    with open(output_path, "w") as f:
        f.write("\n".join(html))
    print(f"HTML output written to {output_path}")

if __name__ == '__main__':
    league = create_league(year=2025, use_local_cache=True)
    best_drafted_teams_html(league)