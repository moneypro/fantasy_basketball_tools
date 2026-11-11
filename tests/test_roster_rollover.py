import copy
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/espn-add-drop/scripts'))
from add_drop import Refused, preflight
from test_add_drop import FakeESPN

spec = importlib.util.spec_from_file_location('rollover', ROOT / '.agents/skills/espn-roster-rollover/scripts/rollover_pickup.py')
rollover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rollover)


class RolloverTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {'authorized':True,'season':2027,'league':30695,'team':2,'addId':1,'dropId':2,
                    'protectedPeriod':2,'targetPeriod':3,'start':'2026-10-25T14:00:00-07:00',
                    'end':'2026-10-25T14:15:00-07:00'}
        self.now = datetime.fromisoformat(self.cfg['start'])
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.api = FakeESPN()
        self.api.data['teams'][0]['transactionCounter']['matchupAcquisitionTotals']={'1':7,'2':0}
        self.api.data['settings']['scheduleSettings']={'periodTypeId':2,'matchupPeriods':{'1':[1],'2':[2]}}
        self.api.season_view = lambda view: {'segments':[{'id':0,'periodTypes':[{'id':2,'periods':[
            {'id':1,'scoringPeriodStart':1,'scoringPeriodEnd':2},
            {'id':2,'scoringPeriodStart':3,'scoringPeriodEnd':9}]}]}]}

    def test_existing_preflight_still_enforces_current_limit(self):
        with self.assertRaises(Refused):preflight(self.api,2,1,2)

    def test_rollover_checks_next_budget_but_posts_current_period(self):
        p=preflight(self.api,2,1,2,rollover_target_period=3)
        self.assertEqual(p['budgetMatchupChecked'],2)
        self.assertEqual(p['payload']['scoringPeriodId'],2)
        self.assertEqual(p['effectivePeriod'],3)
        self.assertEqual(len(p['payload']['items']),2)

    def test_target_budget_exhausted_is_rejected(self):
        self.api.data['teams'][0]['transactionCounter']['matchupAcquisitionTotals']['2']=7
        with self.assertRaises(Refused):preflight(self.api,2,1,2,rollover_target_period=3)

    def test_rollover_must_be_observed(self):
        self.api.data['status']['transactionScoringPeriod']=2
        r=rollover.tick(self.api,self.cfg,self.path,self.now)
        self.assertEqual(r['state'],'waiting_for_roster_rollover');self.assertEqual(self.api.posts,[])

    def test_wrong_effective_period_stops(self):
        self.api.data['status']['transactionScoringPeriod']=4
        self.assertTrue(rollover.tick(self.api,self.cfg,self.path,self.now)['terminal'])
        self.assertEqual(self.api.posts,[])

    def test_owned_target_stops(self):
        self.api.pool[1]['onTeamId']=9
        self.assertEqual(rollover.tick(self.api,self.cfg,self.path,self.now)['state'],'target_unavailable')

    def test_preview_never_submits(self):
        r=rollover.tick(self.api,self.cfg,self.path,self.now,True)
        self.assertEqual(r['state'],'preview_ready');self.assertEqual(self.api.posts,[])

    def test_outside_window_never_submits(self):
        self.assertEqual(rollover.tick(self.api,self.cfg,self.path,datetime.fromisoformat(self.cfg['end']))['state'],'expired_no_attempt')
        self.assertEqual(self.api.posts,[])

    def test_existing_attempt_only_reconciles(self):
        journal=self.path/'transaction';journal.mkdir()
        (journal/'plan.json').write_text('{}')
        with patch.object(rollover,'verify',return_value={'state':'unverified'}) as verify, patch.object(rollover,'execute') as execute:
            r=rollover.tick(self.api,self.cfg,self.path,self.now)
            self.assertTrue(r['postAlreadyAttempted']);verify.assert_called_once();execute.assert_not_called()

    def test_terminal_state_never_submits(self):
        (self.path/'status.json').write_text(json.dumps({'state':'verified_completed','terminal':True}))
        self.assertEqual(rollover.tick(self.api,self.cfg,self.path,self.now)['state'],'verified_completed')
        self.assertEqual(self.api.posts,[])

    def test_minimal_activation_only_benches_idle_player(self):
        api=Mock()
        def entry(i,slot,tid):
            return {'playerId':i,'lineupSlotId':slot,'playerPoolEntry':{'player':{'proTeamId':tid,'eligibleSlots':[0,12],'injuryStatus':'ACTIVE'}}}
        api.roster.return_value=[entry(1,12,9),entry(2,0,23)]
        api.get.return_value={'settings':{'rosterSettings':{'lineupSlotCounts':{'0':1,'12':3}}}}
        api.season_view.return_value={'settings':{'proTeams':[{'id':9,'proGamesByScoringPeriod':{'3':[{}]}},{'id':23,'proGamesByScoringPeriod':{}}]}}
        with patch.object(rollover,'plan_explicit_moves',return_value={'ok':True}) as plan:
            rollover.minimal_activation(api,self.cfg)
            plan.assert_called_once_with(api,2,3,{1:0,2:12})


if __name__=='__main__':unittest.main()
