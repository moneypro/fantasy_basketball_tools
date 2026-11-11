import importlib.util
import json
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('waiver_watch', ROOT / '.agents/skills/espn-waiver-watch/scripts/waiver_watch.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.cfg = dict(authorized=True, season=2027, league=30695, team=2,
                        addId=1, dropId=2, protectedPeriod=7, targetPeriod=8,
                        start='2026-10-27T00:00:00-07:00', end='2026-10-27T02:00:00-07:00')
        self.now = datetime.fromisoformat(self.cfg['start'])
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.api = Mock()
        self.league = dict(id=30695, seasonId=2027, scoringPeriodId=8,
                           status={'transactionScoringPeriod': 8})
        self.api.get.return_value = self.league
        self.pool = {1: dict(onTeamId=0, status='WAIVERS', player={'injuryStatus':'ACTIVE'}),
                     2: dict(onTeamId=2, status='ONTEAM')}
        self.api.players.return_value = self.pool

    def tick(self, **kw):
        return w.tick(self.api, self.cfg, self.path, kw.pop('now', self.now), **kw)

    def test_waivers_never_post(self):
        self.assertEqual(self.tick()['state'], 'waiting_for_free_agent')
        self.api.post.assert_not_called()

    def test_owned_anywhere_stops(self):
        for owner in [2, 9]:
            self.pool[1]['onTeamId'] = owner
            self.assertEqual(self.tick()['state'], 'target_already_owned')
        self.api.post.assert_not_called()

    def test_missing_drop_stops(self):
        self.pool[2]['onTeamId'] = 0
        self.assertTrue(self.tick()['terminal'])

    def test_window_boundaries(self):
        self.assertEqual(self.tick(now=self.now-timedelta(seconds=1))['state'], 'waiting_for_window')
        self.assertEqual(self.tick(now=self.now+timedelta(hours=2))['state'], 'expired_no_attempt')
        self.api.get.assert_not_called()

    def test_preview_free_agent_never_executes(self):
        self.pool[1]['status'] = 'FREEAGENT'
        with patch.object(w, 'execute') as execute:
            self.assertEqual(self.tick(preview=True)['state'], 'preview_free_agent')
            execute.assert_not_called()

    def test_wrong_period_and_injury_stop(self):
        self.league['status']['transactionScoringPeriod'] = 9
        self.assertTrue(self.tick()['terminal'])
        self.league['status']['transactionScoringPeriod'] = 8
        self.pool[1].update(status='FREEAGENT', player={'injuryStatus':'OUT'})
        self.assertEqual(self.tick()['state'], 'target_ruled_out_needs_review')

    def test_old_period_waits_without_purchase(self):
        self.pool[1]['status'] = 'FREEAGENT'
        self.league['status']['transactionScoringPeriod'] = 7
        self.assertEqual(self.tick()['state'], 'waiting_for_target_period')

    def test_existing_attempt_only_verifies(self):
        j = self.path/'transaction'; j.mkdir()
        (j/'plan.json').write_text('{}')
        with patch.object(w, 'verify', return_value={'state':'unverified'}) as verify, patch.object(w,'execute') as execute:
            self.assertTrue(self.tick()['postAlreadyAttempted'])
            verify.assert_called_once(); execute.assert_not_called()

    def test_terminal_does_not_read(self):
        (self.path/'status.json').write_text(json.dumps({'terminal':True,'state':'verified_completed'}))
        self.assertEqual(self.tick()['state'], 'verified_completed')
        self.api.get.assert_not_called()

    def test_success_snapshots_then_finishes_and_never_repeats(self):
        self.pool[1]['status'] = 'FREEAGENT'
        self.api.roster.return_value = []
        with patch.object(w,'preflight',return_value={'effectivePeriod':8}) as preflight, \
             patch.object(w,'execute',return_value={'state':'verified_completed'}) as execute, \
             patch.object(w,'finish',return_value={'state':'verified_completed','terminal':True}) as finish, \
             patch.object(w,'datetime') as clock:
            clock.fromisoformat = datetime.fromisoformat
            clock.now.return_value = self.now
            result = self.tick()
            preflight.assert_called_once_with(self.api,2,1,2)
            execute.assert_called_once(); finish.assert_called_once()
            self.assertTrue((self.path/'protected-roster.json').exists())
            (self.path/'status.json').write_text(json.dumps(result))
            self.tick(); execute.assert_called_once()

    def test_preflight_race_refuses_without_execution(self):
        self.pool[1]['status'] = 'FREEAGENT'
        with patch.object(w,'preflight',side_effect=w.Refused('No longer free')), patch.object(w,'execute') as execute:
            with self.assertRaises(w.Refused): self.tick()
            execute.assert_not_called()

    def test_authorization_and_window_validation(self):
        self.cfg['authorized'] = False
        with self.assertRaises(w.Refused):self.tick()
        self.cfg['authorized'] = True
        self.cfg['end'] = '2026-10-27T03:00:00-07:00'
        with self.assertRaises(w.Refused):self.tick()

    def priority(self, status='PENDING', pending=True):
        self.cfg['priorityClaim'] = dict(transactionId='claim', addId=3, activationPeriod=9,
                                         directory=str(self.path))
        self.api.transactions.return_value = [dict(id='claim', teamId=2, type='WAIVER',
            status=status, isPending=pending, items=[dict(type='ADD',playerId=3),dict(type='DROP',playerId=2)])]

    def test_teammate_rule_ignores_stale_out_and_waits_until_deadline(self):
        self.priority()
        rule = dict(teammateId=4, alternateId=5, teamId=30, teammateName='Player', eventId=100,
                    freshAfter=self.now.isoformat(), resume=(self.now+timedelta(hours=14)).isoformat(),
                    decide=(self.now+timedelta(hours=15, minutes=50)).isoformat(),
                    stop=(self.now+timedelta(hours=15, minutes=58)).isoformat())
        self.cfg['teammateDecision'] = rule
        raw = dict(injuryStatus='OUT', fullName='Player', proTeamId=30)
        self.pool[4] = {'player':raw}
        report = dict(status='Out', date=(self.now-timedelta(days=1)).isoformat())
        with patch.object(w, 'teammate_report', return_value=report):
            self.assertEqual(w.choose_fallback(self.api,self.cfg,8,self.now)[0], None)
            self.assertEqual(w.choose_fallback(self.api,self.cfg,8,datetime.fromisoformat(rule['decide']))[0],5)
            report['date'] = self.now.isoformat()
            self.assertEqual(w.choose_fallback(self.api,self.cfg,8,self.now)[0],1)
            raw['injuryStatus'] = 'ACTIVE'
            self.assertEqual(w.choose_fallback(self.api,self.cfg,8,self.now)[0],None)
            report.clear()
            self.assertEqual(w.choose_fallback(self.api,self.cfg,8,self.now)[0],5)
        self.assertEqual(self.tick(now=self.now+timedelta(hours=2))['state'], 'waiting_for_prelock_window')
        self.assertEqual(self.tick(now=datetime.fromisoformat(rule['stop']))['state'], 'expired_no_attempt')
        self.api.post.assert_not_called()
        j=self.path/'transaction'; j.mkdir()
        (j/'plan.json').write_text(json.dumps({'add':{'id':5},'drop':{'id':2}}))
        with patch.object(w,'verify',return_value={'state':'verified_completed'}), patch.object(w,'finish') as finish:
            self.tick(now=datetime.fromisoformat(rule['resume']))
            self.assertEqual(finish.call_args.args[1]['addId'],5)

    def test_clearance_observed_before_claim_survives_pending_and_morning_gap(self):
        self.priority()
        rule = dict(teammateId=4, alternateId=5, teamId=30, teammateName='Player', eventId=100,
                    freshAfter=(self.now-timedelta(days=1)).isoformat(), resume=(self.now+timedelta(hours=14)).isoformat(),
                    observeFrom=(self.now-timedelta(hours=4)).isoformat(),
                    decide=(self.now+timedelta(hours=15,minutes=50)).isoformat(), stop=(self.now+timedelta(hours=16)).isoformat())
        self.cfg['teammateDecision'] = rule
        self.pool[4]={'player':dict(injuryStatus='ACTIVE',fullName='Player',proTeamId=30)}
        self.pool[5]={'player':{'injuryStatus':'ACTIVE'},'onTeamId':0,'status':'FREEAGENT'}
        with patch.object(w,'teammate_report',return_value={}) as feed:
            self.tick(now=self.now-timedelta(hours=1))
            self.api.post.assert_not_called()
            self.assertTrue((self.path/'teammate-clearance.json').exists())
            self.pool[4]['player']['injuryStatus']='DAY_TO_DAY'
            feed.return_value={'status':'Day-To-Day'}
            self.assertEqual(self.tick()['state'],'waiting_for_priority_claim')
            self.api.transactions.return_value[0].update(status='FAILED',isPending=False)
            morning=self.now+timedelta(hours=5)
            self.assertEqual(self.tick(now=morning,preview=True)['selectedPickup'],5)
            # A real, later scratch is different from an inconclusive designation.
            self.pool[4]['player']['injuryStatus']='OUT'
            feed.return_value={'status':'Out','date':morning.isoformat()}
            self.assertEqual(w.choose_fallback(self.api,self.cfg,8,morning,self.path)[0],1)
            self.assertFalse((self.path/'teammate-clearance.json').exists())

    def test_decision_change_at_submission_defers_without_posting(self):
        self.priority('FAILED',False)
        self.cfg['teammateDecision']=dict(teammateId=4, alternateId=5,teamId=30, eventId=100,
            observeFrom=(self.now-timedelta(hours=1)).isoformat(),resume=(self.now+timedelta(hours=14)).isoformat(),
            decide=(self.now+timedelta(hours=15)).isoformat(), stop=(self.now+timedelta(hours=16)).isoformat())
        self.pool[1]['status']='FREEAGENT'
        self.api.roster.return_value=[]
        with patch.object(w,'choose_fallback',side_effect=[(1,'teammate_out'),(5,'teammate_active')]), \
             patch.object(w,'preflight',return_value={'effectivePeriod':8}), patch.object(w,'execute') as execute:
            self.assertEqual(self.tick()['state'],'teammate_status_changed_before_pickup')
            execute.assert_not_called()

    def test_priority_pending_blocks_free_agent_fallback(self):
        self.priority(); self.pool[1]['status'] = 'FREEAGENT'
        with patch.object(w, 'execute') as execute:
            self.assertEqual(self.tick()['state'], 'waiting_for_priority_claim')
            execute.assert_not_called()

    def test_missing_priority_evidence_waits(self):
        self.priority(); self.api.transactions.return_value = []
        self.assertEqual(self.tick()['state'], 'waiting_for_priority_claim_evidence')

    def test_failed_priority_allows_fallback_preview(self):
        self.priority('FAILED', False); self.pool[1]['status'] = 'FREEAGENT'
        self.assertEqual(self.tick(preview=True)['state'], 'preview_free_agent')

    def test_reissued_result_requires_matching_parent_and_competing_award(self):
        self.priority('FAILED_INVALIDPLAYERSOURCE', False)
        self.cfg['priorityClaim']['requireOtherWinner'] = True
        loss = self.api.transactions.return_value[0]
        loss.update(id='new', relatedTransactionId='unrelated', executionType='PROCESS')
        self.pool[1]['status'] = 'FREEAGENT'
        self.pool[3] = dict(onTeamId=17)
        self.assertEqual(self.tick(preview=True)['state'], 'waiting_for_priority_claim_evidence')
        loss['relatedTransactionId'] = 'claim'
        self.assertEqual(self.tick(preview=True)['state'], 'waiting_for_competing_award')
        self.api.transactions.return_value.append(dict(teamId=17, type='WAIVER', status='EXECUTED',
            isPending=False, scoringPeriodId=8, items=[dict(type='ADD', playerId=3)]))
        self.assertEqual(self.tick(preview=True)['state'], 'preview_free_agent')

    def test_no_verified_claim_id_never_releases_free_agent(self):
        self.priority()
        self.cfg['priorityClaim']['transactionId'] = None
        self.assertEqual(self.tick(preview=True)['state'], 'waiting_for_priority_claim_evidence')
        self.api.transactions.assert_not_called()

    def test_awarded_priority_activates_primary_not_fallback(self):
        self.priority('EXECUTED', False)
        self.pool[3] = dict(onTeamId=2); self.pool[2]['onTeamId'] = 0
        with patch.object(w, 'finish', return_value={'state':'verified_completed','terminal':True}) as finish, patch.object(w,'execute') as execute:
            self.assertEqual(self.tick()['selectedPickup'], 3)
            self.assertEqual(finish.call_args.args[1]['targetPeriod'], 9)
            execute.assert_not_called()

    def test_awarded_priority_preview_never_activates(self):
        self.priority('EXECUTED', False)
        self.pool[3] = dict(onTeamId=2); self.pool[2]['onTeamId'] = 0
        with patch.object(w,'finish') as finish:
            self.assertEqual(self.tick(preview=True)['state'], 'priority_claim_awarded')
            finish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
