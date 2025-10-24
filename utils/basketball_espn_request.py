import requests
from espn_api.requests.espn_requests import EspnFantasyRequests
from espn_api.utils.logger import Logger


class BasketballEspnFantasyRequests(EspnFantasyRequests):
    def __init__(self, sport: str, year: int, league_id: int, cookies: dict = None, logger: Logger = None):
        super().__init__(sport, year, league_id, cookies, logger)

    @staticmethod
    def from_espn_fantasy_request(request: EspnFantasyRequests) -> 'BasketballEspnFantasyRequests':
        return BasketballEspnFantasyRequests("nba", request.year, request.league_id, request.cookies, request.logger)

    def post(self, payload: dict = None, headers: dict = None, extend: str = ''):
        endpoint = self.LEAGUE_ENDPOINT + extend
        r = requests.post(endpoint, json=payload, headers=headers, cookies=self.cookies)
        # print(str(r.json()))
        self.checkRequestStatus(r.status_code)
        if self.logger:
            self.logger.log_request(endpoint=endpoint, params=payload, headers=headers, response=r.json())
        return r.json() if self.year > 2017 else r.json()[0]

    def get_line_up_for_day(self, team_id, scoring_period_id):
        """https://fantasy.espn.com/apis/v3/games/fba/seasons/2021/segments/0/leagues/30695?forTeamId=2&scoringPeriodId=16&view=mRoster"""
        params = {
            'forTeamId': team_id, 'scoringPeriodId': scoring_period_id, 'view': 'mRoster'
        }
        return self.league_get(params=params)