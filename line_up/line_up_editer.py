from typing import List, Any, Tuple

from espn_api.basketball import League, Player
from espn_api.basketball.constant import POSITION_MAP

from utils.basketball_espn_request import BasketballEspnFantasyRequests
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


class LineUpEditor:

    def __init__(self, league: League, team_id: int):
        self.league = league
        self.team_id = team_id
        self.swid = self.league.espn_request.cookies['SWID']
        self.roster = self.league.get_team_data(self.team_id).roster
        self.game_day_player_getter = GameDayPlayerGetter(league, self.roster, team_id)

    def change_line_up(self, payload) -> Any:
        request = BasketballEspnFantasyRequests.from_espn_fantasy_request(self.league.espn_request)
        data = request.post(payload=payload, extend="/transactions/")
        return data

    def bench_all_players(self, scoring_period: int) -> None:
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

    def fill_line_up(self, scoring_period: int, ignore_injury=False, player_cap=9) -> None:
        """
        Player cap would only return the best possible combination of the players that can play.
        """
        self.bench_all_players(scoring_period)
        players_playing_that_day = self.game_day_player_getter.get_players_playing(scoring_period)
        if not ignore_injury:
            # TODO: Set levels, OUT and DTD can be put up there as long as there are spots, just lower priority.
            players_playing_that_day = [player for player in players_playing_that_day if player.injuryStatus == 'ACTIVE']
        line_up = self.get_optimized_line_up(players_playing_that_day)
        move_command = [{"playerId": player_id, "type": "LINEUP", "toLineupSlotId": to_line_up_slot_id} for player_id, to_line_up_slot_id in line_up]
        if len(move_command) == 0:
            return
        payload = {"isLeagueManager": "false", "teamId": self.team_id, "type": "FUTURE_ROSTER", "memberId": self.swid,
                   "scoringPeriodId": scoring_period, "executionType": "EXECUTE",
                   "items": move_command}
        # print(payload)
        self.change_line_up(payload)

    def get_optimized_line_up(self, players: List[Player]) -> List[Tuple[int, int]]:
        """
        Return list of tuple (player id, to line up slot id).
        This currently only supports when your line up is of PG, SG, SF, PF, C and 5 UTILs.
        We need to consider these factors: players' avg points and their injury status.
        If total player is less than the player cap, we can keep using the current logic.
        If there are more, think of a better strategy...
        Strategy: grouper players by category for a greedy algorithm:
        For each position, list available players, if multiple players are eligible for one spot,
        pick the one that's either only available at that position, or the highest avg score
        if there are multiple.
        """
        fixed_slots = {}
        util_list = []
        assigned_player_id_set = set()
        for player in players:
            positions = LineUpEditor.get_available_position(player.eligibleSlots)
            if len(positions) == 1 and positions[0] not in fixed_slots: # single position, put into the slot
                assigned_player_id_set.add(player.playerId)
                fixed_slots[positions[0]] = player.playerId
        for player in players:
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
    def get_available_position(eligible_slots: List[str]) -> List[str]:
        # PG, SG, SF, PF, C
        available_positions = [POSITION_MAP[i] for i in range(5)]
        return [eligible_slot for eligible_slot in eligible_slots if eligible_slot in available_positions]


    def complete_line_up(self, scoring_periods: List[int]):
        """
        Finish a line up. Return the ones failed.
        """
        # TODO
        pass