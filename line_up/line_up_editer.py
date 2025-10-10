import requests
from espn_api.basketball import League, Player
from espn_api.basketball.constant import POSITION_MAP
from espn_api.requests.espn_requests import checkRequestStatus

from .game_day_player_getter import GameDayPlayerGetter

'''
{"isLeagueManager":false,"teamId":2,"type":"ROSTER","memberId":"{3C4A75B6-F84B-48AE-8A75-B6F84B48AE47}","scoringPeriodId":7,"executionType":"EXECUTE","items":[{"playerId":4277905,"type":"LINEUP","fromLineupSlotId":0,"toLineupSlotId":11},{"playerId":4066636,"type":"LINEUP","fromLineupSlotId":11,"toLineupSlotId":0}]}
Line up slot:
PG: 0,
SG: 1,
SF: 2,
PF: 3,
C: 4,
UTIL: 11.
'''


def league_post(espn_request, payload: dict = None, headers: dict = None, extend: str = ''):
    endpoint = espn_request.LEAGUE_ENDPOINT + extend
    r = requests.post(endpoint, json=payload, headers=headers, cookies=espn_request.cookies)
    print(str(r.json()))
    checkRequestStatus(r.status_code)
    if espn_request.logger:
        espn_request.logger.log_request(endpoint=endpoint, params=payload, headers=headers, response=r.json())
    return r.json() if espn_request.year > 2017 else r.json()[0]

class LineUpEditor:

    def __init__(self, league: League, team_id: int):
        self.league = league
        self.team_id = team_id
        self.swid = self.league.espn_request.cookies['SWID']
        self.roster = self.league.get_team_data(self.team_id).roster
        self.game_day_player_getter = GameDayPlayerGetter(league, self.roster, team_id)

    def change_line_up(self, payload):
        data = league_post(self.league.espn_request, payload=payload, extend="/transactions/")
        return data

    def bench_all_players(self, scoring_period):
        """
        This breaks if you have someone on the current roster but you have already dropped. i.e. inconsistency between current roster and future roster
        """
        bench_slot_id = POSITION_MAP['BE']
        # TODO: See below. Also, ignore IR player.

        move_to_bench_command = [{"playerId": player.playerId, "type": "LINEUP", "toLineupSlotId": bench_slot_id}
                                 for player in self.game_day_player_getter.get_active_player_list_for_day(scoring_period) if player.lineupSlot != 'BE']
        if len(move_to_bench_command) == 0:
            return
        payload = {"isLeagueManager": "false", "teamId": self.team_id, "type": "FUTURE_ROSTER", "memberId": self.swid,
                       "scoringPeriodId": scoring_period, "executionType": "EXECUTE",
                       "items": move_to_bench_command}
        self.change_line_up(payload)

    def fill_line_up(self, scoring_period, sort_stats_by='002021', ignore_injury=False):
        """
        Undefined behavior for active player > 10. TODO: Manage by avg stats.
        """
        self.bench_all_players(scoring_period)
        players_playing_that_day = self.game_day_player_getter.get_players_playing(scoring_period)
        if not ignore_injury:
            players_playing_that_day = [player for player in players_playing_that_day if player.injuryStatus == 'ACTIVE']
        line_up = self.get_optimized_line_up(players_playing_that_day)
        move_command = [{"playerId": player_id, "type": "LINEUP", "toLineupSlotId": to_line_up_slot_id} for player_id, to_line_up_slot_id in line_up]
        if len(move_command) == 0:
            return
        payload = {"isLeagueManager": "false", "teamId": self.team_id, "type": "FUTURE_ROSTER", "memberId": self.swid,
                   "scoringPeriodId": scoring_period, "executionType": "EXECUTE",
                   "items": move_command}
        # TODO: Breaks when no one is playing that day
        print(payload)
        self.change_line_up(payload)

    def get_optimized_line_up(self, active_players: [Player], sort_stats_by='002021') -> [(str, int)]:
        """
        Return list of tuple (player id, to line up slot id).
        This currently only supports when your line up is of PG, SG, SF, PF, C and 5 UTILs.
        """
        fixed_slots = {}
        util_list = []
        assigned_player_id_set = set()
        for player in active_players:
            positions = LineUpEditor.get_available_position(player.eligibleSlots)
            if len(positions) == 1 and positions[0] not in fixed_slots: # single position, put into the slot
                assigned_player_id_set.add(player.playerId)
                fixed_slots[positions[0]] = player.playerId
        for player in active_players:
            if player.playerId not in assigned_player_id_set and len(assigned_player_id_set) < 10:
                positions = LineUpEditor.get_available_position(player.eligibleSlots)
                for position in positions:
                    if position not in fixed_slots:
                        fixed_slots[position] = player.playerId
                        assigned_player_id_set.add(player.playerId)
                if player.playerId not in assigned_player_id_set and len(util_list) < 4:
                    util_list.append(player.playerId)
                    assigned_player_id_set.add(player.playerId)
        line_up = []
        [line_up.append((playerId, POSITION_MAP[position])) for position, playerId in fixed_slots.items()]
        [line_up.append((playerId, POSITION_MAP['UT'])) for playerId in util_list]
        return line_up

    @staticmethod
    def get_available_position(eligible_slots: [str]):
        # PG, SG, SF, PF, C
        available_positions = [POSITION_MAP[i] for i in range(5)]
        return [eligible_slot for eligible_slot in eligible_slots if eligible_slot in available_positions]


    def complete_line_up(self, scoring_periods: [int]):
        """
        Finish a line up. Return the ones failed.
        """
        # TODO
        pass