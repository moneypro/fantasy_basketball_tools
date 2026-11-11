"""Lineup editing and optimization for fantasy basketball."""
from __future__ import annotations
from typing import List, Any, Tuple, Dict, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from espn_api.basketball import League, Player

# Keep legacy dependency injection points while allowing the stdlib CLI to run
# without the optional espn_api package installed.
GameDayPlayerGetter = None
BasketballEspnFantasyRequests = None


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
        global GameDayPlayerGetter
        if GameDayPlayerGetter is None:
            from .game_day_player_getter import GameDayPlayerGetter
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
        global BasketballEspnFantasyRequests
        if BasketballEspnFantasyRequests is None:
            from utils.basketball_espn_request import BasketballEspnFantasyRequests
        request = BasketballEspnFantasyRequests.from_espn_fantasy_request(self.league.espn_request)
        data = request.post(payload=payload, extend="/transactions/")
        return data

    def bench_all_players(self, scoring_period: int) -> None:
        """Bench all active players for a scoring period.
        
        Note: This breaks if you have someone on the current roster but have already dropped them.
        
        Args:
            scoring_period: The scoring period ID
        """
        from espn_api.basketball.constant import POSITION_MAP
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
        from espn_api.basketball.constant import POSITION_MAP
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
        from espn_api.basketball.constant import POSITION_MAP
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


def plan_explicit_moves(api, team_id, period, moves):
    """Validate a minimal atomic lineup change using live settings and locks."""
    from collections import Counter
    from add_drop import require, normalize_owner, roster_summary, now
    league = api.get('?view=mSettings&view=mTeam')
    require(league['id'] == api.league and league['seasonId'] == api.season, 'League/season mismatch')
    require(period >= league['scoringPeriodId'], 'Cannot edit a past scoring period')
    require(period <= league['status']['finalScoringPeriod'], 'Period beyond season')
    team = next(t for t in league['teams'] if t['id'] == team_id)
    owners = [team.get('primaryOwner'), *team.get('owners', [])]
    require(api.owner in {normalize_owner(o) for o in owners if o}, 'Session does not own this team')
    require(not team.get('isTransactionLocked'), 'Team transactions locked')
    before = roster_summary(api.roster(period, team_id))
    old = {p['id']: p['slot'] for p in before}
    require(bool(moves) and set(moves) <= set(old), 'Move players must be on the target roster')
    pool = api.players(period, list(moves))
    settings = league['settings']['rosterSettings']
    counts = {int(k): v for k, v in settings['lineupSlotCounts'].items()}
    items = []
    for pid, target in moves.items():
        entry = pool[pid]
        require(entry['onTeamId'] == team_id and entry['status'] == 'ONTEAM', 'Ownership changed')
        require(target in counts and counts[target] > 0, 'Slot unavailable in this league')
        require(target in entry['player']['eligibleSlots'], 'Player is ineligible for target slot')
        require(target not in (13, 14) and old[pid] not in (13, 14), 'IR moves require separate review')
        if old[pid] == target:
            continue
        require(entry.get('lineupLocked') is False, 'Player lineup is locked')
        require(target == 12 or entry['player'].get('injuryStatus', 'ACTIVE') not in
                ('OUT', 'INJURY_RESERVE', 'SUSPENSION'), 'Cannot activate a ruled-out player')
        items.append({'playerId': pid, 'type': 'LINEUP', 'fromLineupSlotId': old[pid],
                      'toLineupSlotId': target})
    expected = {**old, **moves}
    for slot, count in Counter(expected.values()).items():
        require(slot == 12 and settings.get('isBenchUnlimited') or count <= counts.get(slot, 0),
                'Result exceeds league slot capacity')
    return {'season': api.season, 'league': api.league, 'team': team_id, 'period': period,
            'before': before, 'expectedSlots': expected, 'checkedAt': now(),
            'payload': {'isLeagueManager': False, 'teamId': team_id,
                        'type': 'ROSTER' if period == league['scoringPeriodId'] else 'FUTURE_ROSTER',
                        'scoringPeriodId': period, 'executionType': 'EXECUTE', 'items': items}}


def verify_explicit_moves(api, plan, submission):
    from add_drop import roster_summary, now
    roster = roster_summary(api.roster(plan['period'], plan['team']))
    expected = {int(k): v for k, v in plan['expectedSlots'].items()}
    observed = {p['id']: p['slot'] for p in roster}
    response = submission.get('response', {})
    executed = response.get('status') == 'EXECUTED' and response.get('isPending') is False
    if not executed:
        executed = any(t.get('id') == response.get('id') and t.get('status') == 'EXECUTED'
                       and t.get('isPending') is False for t in api.transactions())
    return {'state': 'verified_completed' if observed == expected and executed else 'unverified',
            'period': plan['period'], 'lineup': roster, 'checkedAt': now()}


def explicit_cli():
    """Preview by default; --execute sends one date-appropriate lineup request, never retries."""
    import argparse
    import json
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / '.agents/skills/espn-add-drop/scripts'))
    from add_drop import ESPN, DEFAULT_ENV, Refused, require, write_json
    parser = argparse.ArgumentParser(description=explicit_cli.__doc__)
    parser.add_argument('--season', type=int)
    parser.add_argument('--league', type=int, default=30695)
    parser.add_argument('--team', type=int, default=2)
    parser.add_argument('--period', type=int)
    parser.add_argument('--move', action='append', default=[], help='PLAYER_ID:SLOT_ID; repeat for swaps')
    parser.add_argument('--env-file', default=DEFAULT_ENV)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--journal', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    try:
        if args.verify:
            require(not args.execute, 'Verification cannot execute')
            plan = json.loads((args.verify / 'plan.json').read_text())
            api = ESPN(plan['season'], plan['league'], args.env_file)
            path = args.verify / 'submission.json'
            result = verify_explicit_moves(api, plan, json.loads(path.read_text()) if path.exists() else {})
            write_json(args.verify / 'verification.json', result)
        else:
            require(args.season and args.period and args.move, 'Season, period and moves required')
            pairs = [tuple(map(int, move.split(':'))) for move in args.move]
            require(all(len(p) == 2 for p in pairs), 'Use PLAYER_ID:SLOT_ID')
            moves = dict(pairs)
            require(len(moves) == len(pairs), 'Duplicate player move')
            api = ESPN(args.season, args.league, args.env_file)
            plan = plan_explicit_moves(api, args.team, args.period, moves)
            result = {'state': 'preview_only', 'plan': plan}
            if args.execute:
                require(args.journal is not None, 'Execution requires a unique journal')
                if not plan['payload']['items']:
                    result = {'state': 'already_set', 'plan': plan}
                else:
                    args.journal.mkdir(parents=True, exist_ok=False)
                    write_json(args.journal / 'plan.json', plan)
                    write_json(args.journal / 'attempt.json', {'state': 'attempting_once'})
                    submission = api.post(plan['payload'])
                    write_json(args.journal / 'submission.json', submission)
                    result = verify_explicit_moves(api, plan, submission)
                    result['submission'] = submission
                    write_json(args.journal / 'result.json', result)
        print(json.dumps(result, indent=2))
        return 0 if result['state'] in ('preview_only', 'verified_completed', 'already_set') else 2
    except (Refused, OSError, ValueError, KeyError, StopIteration) as exc:
        print(json.dumps({'state': 'stopped', 'reason': str(exc) if isinstance(exc, Refused)
                          else type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(explicit_cli())
