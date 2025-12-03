"""Lineup editing and optimization for fantasy basketball."""
from typing import List, Any, Tuple, Dict, Set

from espn_api.basketball import League, Player
from espn_api.basketball.constant import POSITION_MAP

from utils.basketball_espn_request import BasketballEspnFantasyRequests
from .game_day_player_getter import GameDayPlayerGetter


class LineUpEditor:
    """Manages and optimizes lineup for a fantasy basketball team.
    
    Attributes:
        league: The fantasy basketball league
        team_id: The team ID
        swid: The SWID cookie for authentication
        roster: The team's roster
        game_day_player_getter: Helper to get players available for each day
    """

    def __init__(self, league: League, team_id: int) -> None:
        """Initialize the lineup editor.
        
        Args:
            league: The fantasy basketball league object
            team_id: The team ID
        """
        self.league = league
        self.team_id = team_id
        self.swid: str = self.league.espn_request.cookies['SWID']
        self.roster: List[Player] = self.league.get_team_data(self.team_id).roster
        self.game_day_player_getter = GameDayPlayerGetter(league, self.roster, team_id)

    def change_line_up(self, payload: Dict[str, Any]) -> Any:
        """Post a lineup change to ESPN.
        
        Args:
            payload: The lineup change payload
            
        Returns:
            Response from the API
        """
        request = BasketballEspnFantasyRequests.from_espn_fantasy_request(self.league.espn_request)
        data = request.post(payload=payload, extend="/transactions/")
        return data

    def bench_all_players(self, scoring_period: int) -> None:
        """Bench all active players for a scoring period.
        
        Note: This breaks if you have someone on the current roster but have already dropped them.
        
        Args:
            scoring_period: The scoring period ID
        """
        bench_slot_id: int = POSITION_MAP['BE']

        move_to_bench_command: List[Dict[str, Any]] = [
            {"playerId": player.playerId, "type": "LINEUP", "toLineupSlotId": bench_slot_id}
            for player in self.game_day_player_getter.get_active_player_list_for_day(scoring_period) 
            if player.lineupSlot != 'BE'
        ]
        
        if len(move_to_bench_command) == 0:
            return
            
        payload: Dict[str, Any] = {
            "isLeagueManager": "false",
            "teamId": self.team_id,
            "type": "FUTURE_ROSTER",
            "memberId": self.swid,
            "scoringPeriodId": scoring_period,
            "executionType": "EXECUTE",
            "items": move_to_bench_command
        }
        self.change_line_up(payload)

    def fill_line_up(self, scoring_period: int, ignore_injury: bool = False, player_cap: int = 9) -> None:
        """Fill the lineup optimally for a scoring period.
        
        Args:
            scoring_period: The scoring period ID
            ignore_injury: Whether to ignore injury status (default: False)
            player_cap: Maximum number of players to use (default: 9)
        """
        self.bench_all_players(scoring_period)
        players_playing_that_day = self.game_day_player_getter.get_players_playing(scoring_period)
        
        if not ignore_injury:
            players_playing_that_day = [
                player for player in players_playing_that_day 
                if player.injuryStatus == 'ACTIVE'
            ]
            
        line_up = self.get_optimized_line_up(players_playing_that_day)
        move_command: List[Dict[str, Any]] = [
            {"playerId": player_id, "type": "LINEUP", "toLineupSlotId": to_line_up_slot_id} 
            for player_id, to_line_up_slot_id in line_up
        ]
        
        if len(move_command) == 0:
            return
            
        payload: Dict[str, Any] = {
            "isLeagueManager": "false",
            "teamId": self.team_id,
            "type": "FUTURE_ROSTER",
            "memberId": self.swid,
            "scoringPeriodId": scoring_period,
            "executionType": "EXECUTE",
            "items": move_command
        }
        self.change_line_up(payload)

    def get_optimized_line_up(self, players: List[Player]) -> List[Tuple[int, int]]:
        """Generate an optimized lineup from available players.
        
        Uses a greedy algorithm to assign players to positions based on eligibility.
        Supports PG, SG, SF, PF, C positions plus 4 UTIL spots.
        
        Args:
            players: List of available players
            
        Returns:
            List of (player_id, position_slot_id) tuples
        """
        fixed_slots: Dict[str, int] = {}
        util_list: List[int] = []
        assigned_player_id_set: Set[int] = set()
        
        # First pass: assign players with single position eligibility
        for player in players:
            positions = LineUpEditor.get_available_position(player.eligibleSlots)
            if len(positions) == 1 and positions[0] not in fixed_slots:
                assigned_player_id_set.add(player.playerId)
                fixed_slots[positions[0]] = player.playerId
                
        # Second pass: assign remaining players to available positions
        for player in players:
            if player.playerId not in assigned_player_id_set and len(assigned_player_id_set) < 10:
                positions = LineUpEditor.get_available_position(player.eligibleSlots)
                for position in positions:
                    if position not in fixed_slots:
                        fixed_slots[position] = player.playerId
                        assigned_player_id_set.add(player.playerId)
                        break
                        
                # If no position slot available, add to UTIL if space exists
                if player.playerId not in assigned_player_id_set and len(util_list) < 4:
                    util_list.append(player.playerId)
                    assigned_player_id_set.add(player.playerId)
                    
        # Build lineup output
        line_up: List[Tuple[int, int]] = []
        for position, player_id in fixed_slots.items():
            line_up.append((player_id, POSITION_MAP[position]))
        for player_id in util_list:
            line_up.append((player_id, POSITION_MAP['UT']))
            
        return line_up

    @staticmethod
    def get_available_position(eligible_slots: List[str]) -> List[str]:
        """Get eligible positional slots from the full eligible slots list.
        
        Filters to only primary positions (PG, SG, SF, PF, C).
        
        Args:
            eligible_slots: List of all eligible slots for a player
            
        Returns:
            List of eligible primary positions
        """
        available_positions: List[str] = [POSITION_MAP[i] for i in range(5)]
        return [eligible_slot for eligible_slot in eligible_slots if eligible_slot in available_positions]

    def complete_line_up(self, scoring_periods: List[int]) -> None:
        """Complete lineup for multiple scoring periods.
        
        Args:
            scoring_periods: List of scoring period IDs
            
        Note:
            TODO: Implement this method to handle multiple periods
        """
        pass