import sys
from pathlib import Path
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.agents/skills/espn-add-drop/scripts'))
from add_drop import Refused
from line_up.line_up_editer import plan_explicit_moves, verify_explicit_moves


class ExplicitLineupTests(unittest.TestCase):
    def setUp(self):
        self.api = Mock(season=2027, league=30695, owner='owner')
        self.api.get.return_value = {'id':30695,'seasonId':2027,'scoringPeriodId':6,
            'status':{'finalScoringPeriod':174},
            'teams':[{'id':2,'primaryOwner':'owner'}],
            'settings':{'rosterSettings':{'lineupSlotCounts':{'11':1,'12':3,'4':1},'isBenchUnlimited':False}}}
        self.entries = [{'playerId':i,'lineupSlotId':slot,'playerPoolEntry':{'player':{'fullName':str(i)}}}
                        for i,slot in [(1,12),(2,11),(3,4)]]
        self.api.roster.return_value = self.entries
        self.pool = {i:{'onTeamId':2,'status':'ONTEAM','lineupLocked':False,
                       'player':{'eligibleSlots':[11,12], 'injuryStatus':'ACTIVE' if i==1 else 'OUT'}}
                     for i in [1,2]}
        self.api.players.return_value = self.pool

    def test_atomic_swap_preserves_unrelated_player(self):
        p=plan_explicit_moves(self.api,2,6,{1:11,2:12})
        self.assertEqual(p['expectedSlots'],{1:11,2:12,3:4})
        self.assertEqual(len(p['payload']['items']),2)
        self.assertEqual(p['payload']['type'],'ROSTER')
        self.api.post.assert_not_called()

    def test_future_period_uses_future_roster(self):
        p=plan_explicit_moves(self.api,2,7,{1:11,2:12})
        self.assertEqual(p['payload']['type'],'FUTURE_ROSTER')

    def test_rejects_full_slot(self):
        with self.assertRaises(Refused):plan_explicit_moves(self.api,2,6,{1:11})

    def test_rejects_locked_player(self):
        self.pool[1]['lineupLocked']=True
        with self.assertRaises(Refused):plan_explicit_moves(self.api,2,6,{1:11,2:12})

    def test_rejects_ineligible_slot(self):
        with self.assertRaises(Refused):plan_explicit_moves(self.api,2,6,{1:4,2:12})

    def test_rejects_past_period(self):
        with self.assertRaises(Refused):plan_explicit_moves(self.api,2,5,{1:11,2:12})

    def test_readback_requires_all_slots_and_transaction_success(self):
        p=plan_explicit_moves(self.api,2,6,{1:11,2:12})
        submission={'response':{'status':'EXECUTED','isPending':False}}
        self.assertEqual(verify_explicit_moves(self.api,p,submission)['state'],'unverified')
        self.entries[0]['lineupSlotId']=11;self.entries[1]['lineupSlotId']=12
        self.assertEqual(verify_explicit_moves(self.api,p,submission)['state'],'verified_completed')
        self.api.transactions.return_value=[]
        self.assertEqual(verify_explicit_moves(self.api,p,{})['state'],'unverified')


if __name__=='__main__':unittest.main()
