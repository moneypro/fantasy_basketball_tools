from espn_api.basketball import Player, League
from espn_api.basketball.constant import PRO_TEAM_MAP
from utils.espn_cache import cached_pro_schedule


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
        return [PRO_TEAM_MAP[team_id] for team_id in cached_pro_schedule(self.league, scoring_period).keys()]

    def get_active_player_list_for_day(self, scoring_period) -> [Player]:
        line_up = self.league.espn_request.get_line_up_for_day(self.team_id, scoring_period)
        players = [Player(entry) for entry in line_up['teams'][0]['roster']['entries']]
        return [player for player in players if player.lineUpSlotId != 13]