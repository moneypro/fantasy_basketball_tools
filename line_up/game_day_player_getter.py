"""Game day player management."""
from typing import List, Dict, Any

from espn_api.basketball import Player, League
from espn_api.basketball.constant import PRO_TEAM_MAP

from utils.basketball_espn_request import BasketballEspnFantasyRequests


class GameDayPlayerGetter:
    """Gets available players for a given scoring period.
    
    Attributes:
        league: The fantasy basketball league
        roster: List of players in the roster
        team_id: The team ID
    """

    def __init__(self, league: League, roster: List[Player], team_id: int) -> None:
        """Initialize the player getter.
        
        Args:
            league: The fantasy basketball league object
            roster: List of Player objects
            team_id: The team ID
        """
        self.roster = roster
        self.league = league
        self.team_id = team_id

    def get_players_playing(self, scoring_period: int) -> List[Player]:
        """Get players whose teams are playing on a given scoring period.
        
        Args:
            scoring_period: The scoring period ID
            
        Returns:
            List of players from teams playing that period
        """
        roster_of_the_day = self.get_active_player_list_for_day(scoring_period)
        team_playing = self.get_games(scoring_period)
        return [player for player in roster_of_the_day if player.proTeam in team_playing]

    def get_games(self, scoring_period: int) -> List[str]:
        """Get list of teams playing on a given scoring period.
        
        Args:
            scoring_period: The scoring period ID
            
        Returns:
            List of team abbreviations playing that period
        """
        return [PRO_TEAM_MAP[team_id] for team_id in self.league._get_pro_schedule(scoring_period).keys()]

    def get_active_player_list_for_day(self, scoring_period: int) -> List[Player]:
        """Get active players (non-IR) for a given scoring period.
        
        Args:
            scoring_period: The scoring period ID
            
        Returns:
            List of active players in the roster for that period
        """
        request = BasketballEspnFantasyRequests.from_espn_fantasy_request(self.league.espn_request)
        line_up: Dict[str, Any] = request.get_line_up_for_day(self.team_id, scoring_period)
        players = [Player(entry, self.league.year) for entry in line_up['teams'][0]['roster']['entries']]
        return [player for player in players if player.lineupSlot != 'IR']