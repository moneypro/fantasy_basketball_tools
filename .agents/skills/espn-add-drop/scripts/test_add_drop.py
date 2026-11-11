"""Offline transaction safety checks: no network or real credentials."""
import copy
from pathlib import Path
import tempfile
import unittest
from add_drop import Refused, execute, preflight, verify


def entry(pid, slot):
    return {'playerId': pid, 'lineupSlotId': slot,
            'playerPoolEntry': {'player': {'fullName': f'Player {pid}'}}}


class FakeESPN:
    season, league, owner = 2027, 30695, 'owner'

    def __init__(self, mode='success'):
        self.mode, self.posts = mode, []
        self.period_reads = []
        self.data = {'id': self.league, 'seasonId': self.season, 'scoringPeriodId': 2,
                     'status': {'isActive': True, 'isExpired': False, 'transactionScoringPeriod': 3,
                                'currentMatchupPeriod': 1},
                     'teams': [{'id': 2, 'name': 'Test', 'primaryOwner': '{OWNER}', 'owners': [],
                                'transactionCounter': {'matchupAcquisitionTotals': {'1': 2}, 'acquisitions': 2}}],
                     'settings': {'acquisitionSettings': {'matchupAcquisitionLimit': 7, 'acquisitionLimit': -1},
                                  'rosterSettings': {'lineupSlotCounts': {'12': 3}, 'isBenchUnlimited': True}}}
        self.pool = {1: {'onTeamId': 0, 'status': 'FREEAGENT', 'rosterLocked': False, 'tradeLocked': False,
                         'player': {'fullName': 'Add Player', 'eligibleSlots': [4, 12]}},
                     2: {'onTeamId': 2, 'status': 'ONTEAM', 'rosterLocked': False, 'tradeLocked': False,
                         'player': {'fullName': 'Drop Player', 'droppable': True}}}
        self.entries, self.txs = [entry(2, 12), entry(3, 4)], []

    def get(self, query):
        return copy.deepcopy(self.data)

    def players(self, period, ids):
        self.period_reads.append(period)
        return copy.deepcopy(self.pool)

    def roster(self, period, team):
        self.period_reads.append(period)
        if self.posts and self.mode == 'read_failure':
            raise Refused('Simulated read failure')
        return copy.deepcopy(self.entries)

    def transactions(self):
        return copy.deepcopy(self.txs)

    def post(self, payload):
        self.posts.append(copy.deepcopy(payload))
        if self.mode in ('reject', 'business_error'):
            return {'httpStatus': 409 if self.mode == 'reject' else 200,
                    'messages': 'Simulated rejection'}
        if self.mode == 'timeout':
            return {'transportError': 'TimeoutError'}
        tx = {**copy.deepcopy(payload), 'id': 'new-transaction', 'status': 'EXECUTED', 'isPending': False}
        if self.mode == 'pending':
            tx.update(status='PENDING', isPending=True)
        else:
            self.pool[1].update(onTeamId=2, status='ONTEAM')
            self.pool[2].update(onTeamId=0, status='WAIVERS')
            self.entries = [entry(1, 12), entry(3, 4)]
        self.txs = [tx]
        if self.mode == 'timeout_completed':
            return {'transportError': 'TimeoutError'}
        return {'httpStatus': 200, 'response': tx}


class WorkflowTests(unittest.TestCase):
    def test_preview_has_no_posts_and_distinguishes_periods(self):
        api = FakeESPN()
        plan = preflight(api, 2, 1, 2)
        self.assertEqual(api.posts, [])
        self.assertEqual(plan['payload']['scoringPeriodId'], 2)
        self.assertEqual(plan['effectivePeriod'], 3)
        self.assertEqual(set(api.period_reads), {3})

    def test_atomic_replacement_readback_and_duplicate_guard(self):
        api = FakeESPN()
        plan = preflight(api, 2, 1, 2)
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / 'operation'
            result = execute(api, plan, journal)
            self.assertEqual(result['state'], 'verified_completed')
            self.assertEqual(len(api.posts), 1)
            self.assertEqual({i['type'] for i in api.posts[0]['items']}, {'ADD', 'DROP'})
            with self.assertRaises(FileExistsError):
                execute(api, plan, journal)
            self.assertEqual(len(api.posts), 1)

    def test_rejection_timeout_pending_and_false_success(self):
        for mode, expected in [('reject', 'rejected_unchanged'), ('timeout', 'unverified'),
                               ('pending', 'pending'), ('business_error', 'unverified'),
                               ('read_failure', 'unverified'), ('timeout_completed', 'verified_completed')]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                api = FakeESPN(mode)
                result = execute(api, preflight(api, 2, 1, 2), Path(tmp) / 'op')
                self.assertEqual(result['state'], expected)
                self.assertEqual(len(api.posts), 1)

    def test_safety_preconditions_block_without_post(self):
        mutations = [lambda a: a.pool[1].update(status='WAIVERS'),
                     lambda a: a.pool[1].update(onTeamId=9),
                     lambda a: a.pool[2].update(rosterLocked=True),
                     lambda a: a.pool[2]['player'].update(droppable=False),
                     lambda a: a.data['teams'][0].update(primaryOwner='someone-else'),
                     lambda a: a.data['teams'][0]['transactionCounter'].update(matchupAcquisitionTotals={'1': 7}),
                     lambda a: a.entries.clear()]
        for mutate in mutations:
            api = FakeESPN(); mutate(api)
            with self.assertRaises(Refused):
                preflight(api, 2, 1, 2)
            self.assertEqual(api.posts, [])

    def test_old_transaction_cannot_prove_new_execution(self):
        api = FakeESPN()
        old = {'id': 'old', 'teamId': 2, 'type': 'FREEAGENT', 'status': 'EXECUTED', 'isPending': False,
               'items': [{'type': 'ADD', 'playerId': 1}, {'type': 'DROP', 'playerId': 2}]}
        api.txs = [old]
        plan = preflight(api, 2, 1, 2)
        api.pool[1].update(onTeamId=2, status='ONTEAM')
        api.pool[2].update(onTeamId=0, status='WAIVERS')
        api.entries = [entry(1, 12), entry(3, 4)]
        self.assertEqual(verify(api, plan, {})['state'], 'unverified')

    def test_unrelated_roster_change_prevents_verified_claim(self):
        api = FakeESPN()
        plan = preflight(api, 2, 1, 2)
        submission = api.post(plan['payload'])
        api.entries.append(entry(4, 12))
        self.assertEqual(verify(api, plan, submission)['state'], 'unverified')


if __name__ == '__main__':
    unittest.main()
