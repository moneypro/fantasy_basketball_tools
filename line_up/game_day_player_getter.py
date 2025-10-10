from espn_api.basketball import Player, League
from espn_api.basketball.constant import PRO_TEAM_MAP


def get_line_up_for_day(espn_request, team_id, scoring_period_id):
    """https://fantasy.espn.com/apis/v3/games/fba/seasons/2021/segments/0/leagues/30695?forTeamId=2&scoringPeriodId=16&view=mRoster"""
    params = {
        'forTeamId': team_id, 'scoringPeriodId': scoring_period_id, 'view': 'mRoster'
    }
    return espn_request.league_get(params=params)

class GameDayPlayerGetter:
    def __init__(self, league: League, roster: [Player], team_id: int):
        self.roster = roster
        self.league = league
        self.team_id = team_id

    def get_players_playing(self, scoring_period: int) -> [Player]:
        roster_of_the_day = self.get_active_player_list_for_day(scoring_period)
        team_playing = self.get_games(scoring_period)
        return [player for player in roster_of_the_day if player.proTeam in team_playing]

    def get_games(self, scoring_period):
        return [PRO_TEAM_MAP[team_id] for team_id in self.league._get_pro_schedule(scoring_period).keys()]

    def get_active_player_list_for_day(self, scoring_period) -> [Player]:
        line_up = get_line_up_for_day(self.league.espn_request, self.team_id, scoring_period)
        # print (line_up)
        players = [Player(entry, self.league.year) for entry in line_up['teams'][0]['roster']['entries']]
        return [player for player in players if player.lineupSlot != 'IR']