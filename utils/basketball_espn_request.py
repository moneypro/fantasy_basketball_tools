"""ESPN fantasy basketball API request utilities."""
from typing import Dict, Any, Optional

import requests
from espn_api.requests.espn_requests import EspnFantasyRequests
from espn_api.utils.logger import Logger


class BasketballEspnFantasyRequests(EspnFantasyRequests):
    """Custom ESPN fantasy requests for basketball with additional methods.
    
    Extends the base EspnFantasyRequests class with basketball-specific functionality.
    """

    def __init__(self, sport: str, year: int, league_id: int, cookies: Optional[Dict[str, str]] = None,
                 logger: Optional[Logger] = None) -> None:
        """Initialize the basketball ESPN requests handler.
        
        Args:
            sport: The sport type (e.g., 'nba')
            year: The league year
            league_id: The league ID
            cookies: Optional cookies for authentication
            logger: Optional logger instance
        """
        super().__init__(sport, year, league_id, cookies, logger)

    @staticmethod
    def from_espn_fantasy_request(request: EspnFantasyRequests) -> 'BasketballEspnFantasyRequests':
        """Create from an existing EspnFantasyRequests instance.
        
        Args:
            request: An existing EspnFantasyRequests instance
            
        Returns:
            A new BasketballEspnFantasyRequests instance
        """
        return BasketballEspnFantasyRequests("nba", request.year, request.league_id, 
                                              request.cookies, request.logger)

    def post(self, payload: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
             extend: str = '') -> Any:
        """Make a POST request to the ESPN fantasy API.
        
        Args:
            payload: The request payload
            headers: Optional custom headers
            extend: URL extension to append to the league endpoint
            
        Returns:
            The JSON response from the API
        """
        endpoint: str = self.LEAGUE_ENDPOINT + extend
        r = requests.post(endpoint, json=payload, headers=headers, cookies=self.cookies)
        self.checkRequestStatus(r.status_code)
        if self.logger:
            self.logger.log_request(endpoint=endpoint, params=payload, headers=headers, response=r.json())
        return r.json() if self.year > 2017 else r.json()[0]

    def get_line_up_for_day(self, team_id: int, scoring_period_id: int) -> Dict[str, Any]:
        """Get the lineup for a team on a specific scoring period.
        
        Args:
            team_id: The team ID
            scoring_period_id: The scoring period ID
            
        Returns:
            Dictionary containing the lineup data
        """
        params: Dict[str, Any] = {
            'forTeamId': team_id,
            'scoringPeriodId': scoring_period_id,
            'view': 'mRoster'
        }
        return self.league_get(params=params)