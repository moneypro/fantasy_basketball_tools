from typing import Optional, Dict, List, Tuple
import tabulate
import html
import math
from espn_api.basketball import League
from predict.internal.roster_week_predictor import RosterWeekPredictor
from utils.create_league import create_league
from common.styling import get_table_css
from common.week import Week
import os


class PredictWeekHelper:
    """Helper class for week prediction operations."""
    
    DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    @staticmethod
    def predict_week(league: League, week_index: int, day_of_week_override: int = 0, 
                     injuryStatusList: List[str] = None) -> Tuple[Dict[str, int], Dict[str, Tuple[float, float]]]:
        """Predict points for all teams in the league for a given week.
        
        Args:
            league: The ESPN League object
            week_index: The week number to predict
            day_of_week_override: Starting day override (0=Monday)
            injuryStatusList: List of injury statuses to include
            
        Returns:
            Tuple of (number_of_games_map, team_scores_map)
        """
        if injuryStatusList is None:
            injuryStatusList = ['ACTIVE']
            
        number_of_games_team_name_map = {}
        team_scores = {}
        week = Week(league, week_index)
        
        for team in league.teams:
            predictor = RosterWeekPredictor(team.roster, week)
            predicted_points = predictor.predict(
                daily_active_size=9, 
                starting_day=day_of_week_override, 
                injuryStatusList=injuryStatusList
            )
            team_scores[team.team_name] = predicted_points
            
            number_of_games = predictor.get_total_number_of_games(
                starting_day=day_of_week_override, 
                injuryStatusList=injuryStatusList
            )
            number_of_games_team_name_map[team.team_name] = number_of_games
            
        return number_of_games_team_name_map, team_scores
    
    @staticmethod
    def get_table_output_for_week(league: League, week_index: int, day_of_week_override: int = 0, 
                                  injuryStatusList: List[str] = None) -> Tuple[Dict[str, int], List[Tuple], Dict[str, Tuple[float, float]]]:
        """Get formatted table output for week predictions.
        
        Args:
            league: The ESPN League object
            week_index: The week number to predict
            day_of_week_override: Starting day override (0=Monday)
            injuryStatusList: List of injury statuses to include
            
        Returns:
            Tuple of (number_of_games_map, table_output, team_scores)
        """
        if injuryStatusList is None:
            injuryStatusList = ['ACTIVE']
            
        number_of_games_team_name_map, team_scores = PredictWeekHelper.predict_week(
            league, week_index, day_of_week_override, injuryStatusList
        )
        
        table_output = []
        for team_name, scores in team_scores.items():
            avg, std = scores
            table_output.append((
                team_name, 
                number_of_games_team_name_map[team_name], 
                round(avg), 
                round(std)
            ))
        
        table_output.sort(reverse=True, key=lambda x: x[2])  # Sort by mean points
        table_output.insert(0, (
            "Team Name", 
            "# of games", 
            f"Week {week_index} Mean", 
            f"Week {week_index} Standard Deviation"
        ))
        
        return number_of_games_team_name_map, table_output, team_scores


def predict_match_up(league: League, week_index: int, team_scores: Dict[str, Tuple[float, float]], 
                     number_of_games_team_name_map: Dict[str, int]) -> str:
    """Generate HTML table of matchups with point predictions.
    
    Args:
        league: The ESPN League object
        week_index: The week number
        team_scores: Dictionary mapping team names to (avg, std) tuples
        number_of_games_team_name_map: Dictionary mapping team names to game counts
        
    Returns:
        HTML string of matchup table
    """
    match_up_points = [
        ["Home Team", "Estimate Points", "# of Games", "Away Team", "Estimate Points", "# of Games", "+/-"]
    ]
    
    for matchup in league.scoreboard(week_index):
        home_team_name = matchup.home_team.team_name
        away_team_name = matchup.away_team.team_name
        
        home_team_average = round(team_scores[home_team_name][0])
        away_team_average = round(team_scores[away_team_name][0])
        
        match_up_points.append([
            home_team_name,
            home_team_average,
            number_of_games_team_name_map[home_team_name],
            away_team_name,
            away_team_average,
            number_of_games_team_name_map[away_team_name],
            home_team_average - away_team_average
        ])
    
    return tabulate.tabulate(match_up_points, tablefmt='html', headers="firstrow")


def predict_week(league: League, week_index: int, day_of_week_override: int = 0, injuryStatusList: List[str] = None):
    """Predict points for all teams in the league for a given week.
    
    Args:
        league: The ESPN League object
        week_index: The week number to predict
        day_of_week_override: Starting day override (0=Monday)
        injuryStatusList: List of injury statuses to include
        
    Returns:
        Tuple of (number_of_games_map, team_scores_map)
    """
    return PredictWeekHelper.predict_week(league, week_index, day_of_week_override, injuryStatusList)


def get_table_output_for_week(league: League, week_index: int, day_of_week_override: int = 0, 
                              injuryStatusList: List[str] = None):
    """Get formatted table output for week predictions.
    
    Args:
        league: The ESPN League object
        week_index: The week number to predict
        day_of_week_override: Starting day override (0=Monday)
        injuryStatusList: List of injury statuses to include
        
    Returns:
        Tuple of (number_of_games_map, table_output, team_scores)
    """
    return PredictWeekHelper.get_table_output_for_week(league, week_index, day_of_week_override, injuryStatusList)

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

    # Get remaining days cumulative scores tables
    remaining_days_active = get_remaining_days_table_output(league, week_index, day_of_week_override, ['ACTIVE'])
    remaining_days_dtd = get_remaining_days_table_output(league, week_index, day_of_week_override, ['ACTIVE', 'DAY_TO_DAY'])
    remaining_days_out = get_remaining_days_table_output(league, week_index, day_of_week_override, ['ACTIVE', 'DAY_TO_DAY', 'OUT'])

    non_healthy_table = get_non_healthy_players_table(league)
    non_healthy_html = (
            f"<h2>Week {week_index} - Non-Healthy Players by Status</h2>"
            + tabulate.tabulate(non_healthy_table, tablefmt='html', headers="firstrow")
    )
    non_healthy_html = html.unescape(non_healthy_html)

    body_html = (
            f"<h1>Week {week_index} Summary</h1>"
            + non_healthy_html
            + f"<h2>Week {week_index} - Active Players Only</h2>"
            + tabulate.tabulate(table_active, tablefmt='html', headers="firstrow")
            + f"<h2>Week {week_index} - Remaining Days Cumulative (Active Only)</h2>"
            + tabulate.tabulate(remaining_days_active, tablefmt='html', headers="firstrow")
            + f"<h2>Week {week_index} - Including Day-to-Day (DTD)</h2>"
            + tabulate.tabulate(table_dtd, tablefmt='html', headers="firstrow")
            + f"<h2>Week {week_index} - Remaining Days Cumulative (DTD Included)</h2>"
            + tabulate.tabulate(remaining_days_dtd, tablefmt='html', headers="firstrow")
            + f"<h2>Week {week_index} - Including OUT</h2>"
            + tabulate.tabulate(table_out, tablefmt='html', headers="firstrow")
            + f"<h2>Week {week_index} - Remaining Days Cumulative (OUT Included)</h2>"
            + tabulate.tabulate(remaining_days_out, tablefmt='html', headers="firstrow")
            + f"<h2>Week {week_index} Matchups (Active Only)</h2>"
            + predict_match_up(league, week_index, team_scores_active, num_games_active_dict)
            + f"<h2>Week {week_index} Matchups (DTD Included)</h2>"
            + predict_match_up(league, week_index, team_scores_dtd, num_games_dtd_dict)
            + f"<h2>Week {week_index} Matchups (OUT Included)</h2>"
            + predict_match_up(league, week_index, team_scores_out, num_games_out_dict)
    )

    _html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Week {week_index} Fantasy Forecast</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    {get_table_css()}
</head>
<body>
    {body_html}
</body>
</html>
"""
    return _html

def build_week_json(league: League, week_index: int, day_of_week_override: int = 0) -> Dict:
    """Build week analysis data as JSON (agent-friendly format).
    
    Returns structured data instead of HTML for better agent compatibility.
    Includes all three injury status configurations (Active, DTD, OUT).
    """
    # Table 1: Active only
    _, table_active, team_scores_active = get_table_output_for_week(league, week_index, day_of_week_override, ['ACTIVE'])
    # Table 2: Active + DTD
    _, table_dtd, team_scores_dtd = get_table_output_for_week(league, week_index, day_of_week_override, ['ACTIVE', 'DAY_TO_DAY'])
    # Table 3: Active + DTD + OUT
    _, table_out, team_scores_out = get_table_output_for_week(league, week_index, day_of_week_override, ['ACTIVE', 'DAY_TO_DAY', 'OUT'])
    num_games_active_dict = {row[0]: row[1] for row in table_active[1:]}
    num_games_dtd_dict = {row[0]: row[1] for row in table_dtd[1:]}
    num_games_out_dict = {row[0]: row[1] for row in table_out[1:]}

    # Get remaining days cumulative scores tables
    remaining_days_active = get_remaining_days_table_output(league, week_index, day_of_week_override, ['ACTIVE'])
    remaining_days_dtd = get_remaining_days_table_output(league, week_index, day_of_week_override, ['ACTIVE', 'DAY_TO_DAY'])
    remaining_days_out = get_remaining_days_table_output(league, week_index, day_of_week_override, ['ACTIVE', 'DAY_TO_DAY', 'OUT'])

    non_healthy_table = get_non_healthy_players_table(league)

    def table_to_dict(table_data):
        """Convert tabulate table to list of dicts"""
        if not table_data or len(table_data) < 2:
            return []
        headers = table_data[0]
        rows = table_data[1:]
        return [dict(zip(headers, row)) for row in rows]

    return {
        "week_index": week_index,
        "summary": {
            "non_healthy_players": table_to_dict(non_healthy_table)
        },
        "active_only": {
            "predictions": table_to_dict(table_active),
            "remaining_days": table_to_dict(remaining_days_active)
        },
        "day_to_day_included": {
            "predictions": table_to_dict(table_dtd),
            "remaining_days": table_to_dict(remaining_days_dtd)
        },
        "out_included": {
            "predictions": table_to_dict(table_out),
            "remaining_days": table_to_dict(remaining_days_out)
        }
    }

def save_week_forecast(league, week_index, day_of_week_override, output_dir):
    week_folder = os.path.join(output_dir, f"week_{week_index}_forecast")
    os.makedirs(week_folder, exist_ok=True)
    week_html = build_week_html(league, week_index, day_of_week_override)
    output_path = os.path.join(week_folder, "index.html")
    with open(output_path, 'w') as f:
        f.write(week_html)
    print(f"Forecast for week {week_index} written to {output_path}")

def get_remaining_days_cumulative_scores(league: League, week_index: int, day_of_week_override: int = 0,
                                         injuryStatusList: List[str] = None) -> Dict[str, List[Tuple[float, float]]]:
    """Calculate cumulative scores for remaining days in the week.
    
    For each team and each day, calculates the sum of predicted points from that day through Sunday.
    Returns both mean and standard deviation for each cumulative period.
    
    Args:
        league: The ESPN League object
        week_index: The week number to predict
        day_of_week_override: Starting day override (0=Monday)
        injuryStatusList: List of injury statuses to include
        
    Returns:
        Dictionary mapping team names to list of (mean, std) tuples for each remaining day
        where index 0 = Monday through Sunday, 1 = Tuesday through Sunday, etc.
    """
    if injuryStatusList is None:
        injuryStatusList = ['ACTIVE']
    
    week = Week(league, week_index)
    cumulative_scores: Dict[str, List[Tuple[float, float]]] = {}
    
    # Calculate daily predictions for each team
    daily_predictions: Dict[str, List[Tuple[float, float]]] = {}
    
    for team in league.teams:
        predictor = RosterWeekPredictor(team.roster, week)
        daily_scores: List[Tuple[float, float]] = []
        
        # Get predictions for each day of the week
        num_days = week.scoring_period[1] - week.scoring_period[0] + 1
        for day in range(day_of_week_override, num_days):
            players_with_game = [
                player for player in predictor.players_with_game(day)
                if getattr(player, 'injuryStatus', 'ACTIVE') in injuryStatusList
            ]
            
            # Get (avg, var, player) for each eligible player
            player_stats = [
                (predictor.get_avg_variance_stats(player)[0], 
                 predictor.get_avg_variance_stats(player)[1], 
                 player)
                for player in players_with_game
            ]
            
            # Sort by avg descending and take top 9
            player_stats.sort(reverse=True, key=lambda x: x[0])
            top_stats = player_stats[:9]
            
            # Sum their avg and variance
            day_points = sum(avg for avg, var, player in top_stats)
            day_variance = sum(var for avg, var, player in top_stats)
            
            daily_scores.append((day_points, day_variance))
        
        daily_predictions[team.team_name] = daily_scores
    
    # Calculate cumulative scores for each remaining day
    for team_name, daily_scores in daily_predictions.items():
        cumulative: List[Tuple[float, float]] = []
        
        # For each starting day
        for start_day in range(len(daily_scores)):
            cumulative_mean = sum(score[0] for score in daily_scores[start_day:])
            # Variance adds when summing independent variables
            cumulative_variance = sum(score[1] for score in daily_scores[start_day:])
            
            # Convert variance back to standard deviation
            cumulative_std = math.sqrt(cumulative_variance)
            
            cumulative.append((cumulative_mean, cumulative_std))
        
        cumulative_scores[team_name] = cumulative
    
    return cumulative_scores


def get_remaining_days_table_output(league: League, week_index: int, day_of_week_override: int = 0,
                                    injuryStatusList: List[str] = None) -> List[List]:
    """Get formatted table output for remaining days cumulative scores.
    
    Args:
        league: The ESPN League object
        week_index: The week number to predict
        day_of_week_override: Starting day override (0=Monday)
        injuryStatusList: List of injury statuses to include
        
    Returns:
        List of rows for HTML table
    """
    if injuryStatusList is None:
        injuryStatusList = ['ACTIVE']
    
    cumulative_scores = get_remaining_days_cumulative_scores(
        league, week_index, day_of_week_override, injuryStatusList
    )
    
    # Get number of days in the week
    week = Week(league, week_index)
    num_days = week.scoring_period[1] - week.scoring_period[0] + 1
    
    # Create table with headers
    days_available = PredictWeekHelper.DAYS_OF_WEEK[day_of_week_override:day_of_week_override + num_days]
    
    table_output = []
    header = ["Team Name"]
    
    # Add day headers showing cumulative period
    for i, day in enumerate(days_available):
        remaining_days = " to ".join(days_available[i:])
        header.append(f"{day} ({remaining_days})")
    
    table_output.append(header)
    
    # Add team rows
    for team_name in sorted(cumulative_scores.keys()):
        row = [team_name]
        for mean, std in cumulative_scores[team_name]:
            row.append(f"{round(mean)} ± {round(std)}")
        table_output.append(row)
    
    return table_output


def get_non_healthy_players_table(league):
    status_columns = ['DAY_TO_DAY', 'OUT']
    table = []
    header = ['Team Name'] + status_columns
    for team in league.teams:
        # Group players by status
        status_to_names = {status: [] for status in status_columns}
        for player in team.roster:
            status = getattr(player, 'injuryStatus', 'ACTIVE')
            if status in status_columns:
                status_to_names[status].append(player.name)
        row = [team.team_name] + [", ".join(status_to_names[status]) for status in status_columns]
        table.append(row)
    table.sort(key=lambda x: x[0])  # Sort by team name
    table.insert(0, header)
    return table

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
    predict_all()