"""Week management for fantasy basketball league."""
from typing import Optional, Tuple, List, Dict

from espn_api.basketball.constant import PRO_TEAM_MAP
from espn_api.basketball.league import League


class Week:
    """Manages game schedule for a given matchup week.
    
    Attributes:
        league: The fantasy basketball league
        scoring_period: Tuple of (start_period, end_period) indices
        team_game_list: List of lists containing team names playing each day
    """

    scoring_period: Tuple[int, int]
    team_game_list: List[List[str]]

    def __init__(self, league: League, match_up_week: int) -> None:
        """Initialize a Week instance.
        
        Args:
            league: The fantasy basketball league object
            match_up_week: The matchup week number (1-based)
        """
        self.league = league
        self.scoring_period = self._match_up_week_to_scoring_period_convert(match_up_week)
        self.team_game_list = self._get_team_game_list()

    @classmethod
    def create(cls, league: League, week_index: Optional[int]) -> 'Week':
        """Factory method to create a Week instance.
        
        Args:
            league: The fantasy basketball league object
            week_index: The week number, or None to use current matchup period
            
        Returns:
            A Week instance for the specified week
        """
        return Week(league, week_index if week_index else league.currentMatchupPeriod)

    def _get_team_game_list(self) -> List[List[str]]:
        """Get the list of teams playing each day in this week.
        
        Returns:
            List of lists where each inner list contains team names playing that day
        """
        return [[PRO_TEAM_MAP[team_id] for team_id in self.league._get_pro_schedule(scoring_period).keys()] 
                for scoring_period in range(self.scoring_period[0], self.scoring_period[1] + 1)]

    @staticmethod
    def _match_up_week_to_scoring_period_convert(match_up_week: int) -> Tuple[int, int]:
        """Convert matchup week number to scoring period indices.
        
        Note: Only works for 2020-2021 season format.
        
        Args:
            match_up_week: The matchup week number (1-based)
            
        Returns:
            Tuple of (start_period, end_period) inclusive indices
        """
        if match_up_week == 1:
            return 0, 7
        return 7 * (match_up_week - 1), 7 * match_up_week - 1

    def cumulate_number_of_games(self) -> Dict[str, int]:
        """Count the total number of games for each team this week.
        
        Returns:
            Dictionary mapping team names to game counts
        """
        number_of_games_for_team: Dict[str, int] = {}
        for game_day in self.team_game_list:
            for team_name in game_day:
                number_of_games_for_team[team_name] = number_of_games_for_team.get(team_name, 0) + 1
        return number_of_games_for_team
