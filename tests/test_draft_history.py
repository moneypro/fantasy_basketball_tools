import unittest

from draft_recap.history import season_recap


class DraftHistoryTests(unittest.TestCase):
    def league(self, scoring_type='H2H_POINTS'):
        return {
            'settings': {'name': 'Test', 'scoringSettings': {'scoringType': scoring_type, 'scoringItems': [{'statId': 0, 'points': 2}]}},
            'teams': [{'id': 1, 'name': '<Team one>'}, {'id': 2, 'name': 'Team two'}],
            'status': {'latestScoringPeriod': 201, 'finalScoringPeriod': 200},
            'draftDetail': {'picks': [
                {'playerId': 1, 'teamId': 1, 'roundId': 1, 'overallPickNumber': 1},
                {'playerId': 2, 'teamId': 2, 'roundId': 1, 'overallPickNumber': 2},
                {'playerId': 3, 'teamId': 1, 'roundId': 11, 'overallPickNumber': 3},
            ]},
        }

    def player(self, player_id, points, year=2025, **extra):
        stats = {'seasonId': year, 'statSourceId': 0, 'statSplitTypeId': 0, 'appliedTotal': points, 'stats': {'0': 100}}
        stats.update(extra)
        return {'id': player_id, 'player': {'fullName': f'Player {player_id}', 'stats': [stats]}}

    def test_original_picks_totals_and_awards(self):
        players = [self.player(1, 10), self.player(2, 30), self.player(3, 20)]
        recap = season_recap(2025, self.league(), players, [])
        self.assertEqual([t['totalPoints'] for t in recap['teams']], [30, 30])
        self.assertEqual([t['rank'] for t in recap['teams']], [1, 1])
        self.assertEqual(recap['steals'][0]['playerId'], 2)
        self.assertEqual(recap['steals'][0]['value'], 1)
        self.assertEqual(recap['busts'][0]['playerId'], 1)
        self.assertEqual(len(recap['teams'][0]['worstScorers']), 1)

    def test_ties_share_scoring_rank(self):
        recap = season_recap(2025, self.league(), [self.player(1, 20), self.player(2, 20), self.player(3, 0)], [])
        self.assertEqual([p['scoringRank'] for t in recap['teams'] for p in t['picks']], [1, 3, 1])
        self.assertNotIn(3, [p['playerId'] for p in recap['busts']])

    def test_missing_stats_do_not_become_zero_or_projected_points(self):
        projected = self.player(2, 9000, statSourceId=1)
        wrong_year = self.player(3, 9000, year=2026)
        recap = season_recap(2025, self.league(), [self.player(1, 0), projected, wrong_year], [])
        self.assertEqual(recap['missingPlayers'], 2)
        self.assertTrue(all(t['totalPoints'] is None for t in recap['teams']))
        self.assertEqual(recap['steals'], [])
        self.assertEqual(recap['busts'], [])
        self.assertEqual(recap['teams'][0]['picks'][0]['points'], 0)

    def test_category_year_uses_explicit_benchmark(self):
        recap = season_recap(2025, self.league('H2H_MOST_CATEGORIES'),
                             [self.player(i, 9999) for i in range(1, 4)], [{'statId': 0, 'points': 3}])
        self.assertTrue(recap['benchmarkScoring'])
        self.assertEqual(recap['teams'][0]['totalPoints'], 600)

    def test_missing_applied_total_uses_that_years_scoring(self):
        recap = season_recap(2025, self.league(), [self.player(i, None) for i in range(1, 4)], [{'statId': 0, 'points': 3}])
        self.assertEqual(recap['teams'][0]['totalPoints'], 400)


if __name__ == '__main__':
    unittest.main()
