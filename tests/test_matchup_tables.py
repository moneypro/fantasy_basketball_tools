import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from matchup_tables import remaining_fraction, surname, build_tables


class TableTests(unittest.TestCase):
    def test_clock_and_overtime(self):
        self.assertEqual(remaining_fraction({'period': 2, 'displayClock': '0.0'}), .5)
        self.assertEqual(remaining_fraction({'period': 3, 'displayClock': '6:00'}), .375)
        self.assertIsNone(remaining_fraction({'period': 5, 'displayClock': '3:00'}))
        self.assertIsNone(remaining_fraction({'period': 3}))

    def test_names(self):
        self.assertEqual(surname('Tristan da Silva'), 'da Silva')
        self.assertEqual(surname('Scotty Pippen Jr.'), 'Pippen Jr.')

    def test_live_points_not_double_counted_bench_excluded_and_injury_override(self):
        roster = [{'id': i, 'name': n, 'slot': slot, 'nbaTeamId': 1, 'injury': 'ACTIVE',
                   'seasonBaseline': 40, 'recentBlend': 30, 'baselineSource': 'test'}
                  for i, n, slot in [(1, 'One Player', 0), (2, 'Bench Player', 12)]]
        days = [{'period': 6, 'date': ['2026-10-25'], 'players': [], 'missingBaselines': []}]
        team = {'roster': roster, 'liveScore': 100, 'models': {
            m: {'includingDTD': {'days': days}} for m in ['seasonBaseline', 'recentBlend']}}
        p = {'teams': {'2': team, '19': team}, 'teamId': 2, 'opponentId': 19, 'currentScoringPeriod': 6}
        schedule = {6: {1: {'state': 'in', 'eventId': 'g'}}}
        stats = {'PTS': '10', 'REB': '1', 'AST': '1', 'STL': '0', 'BLK': '0', 'TO': '0',
                 'FG': '4-5', 'FT': '2-2', '3PT': '0-0'}
        boxes = {'g': {'status': {'period': 2, 'displayClock': '0.0', 'type': {'state': 'in'}},
                       'players': {'1': {'stats': stats, 'didNotPlay': False}}}}
        result = build_tables(p, schedule, boxes, {0: 1})['teams']['2']
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['currentSubtotal'], 10)
        self.assertEqual(result['models']['seasonBaseline']['final'], 120)
        stopped = build_tables(p, schedule, boxes, {0: 1}, {'1': {'reason': 'out', 'source': 'test'}})
        self.assertEqual(stopped['teams']['2']['models']['seasonBaseline']['final'], 100)
        boxes['g']['status'].pop('displayClock')
        unknown = build_tables(p, schedule, boxes, {0: 1})
        self.assertIsNone(unknown['teams']['2']['models']['seasonBaseline']['final'])


if __name__ == '__main__':
    unittest.main()
