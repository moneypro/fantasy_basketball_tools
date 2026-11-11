import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from matchup_report import matchup_bounds, player_baselines, daily_projection


def player(pid, slot, points, nba, injury='ACTIVE'):
    return {'id':pid,'name':str(pid),'slot':slot,'nbaTeamId':nba,'injury':injury,
            'eligibleSlots':[4,11,12], 'seasonBaseline':points,'baselineSource':'test'}


class MatchupReportTests(unittest.TestCase):
    def test_calendar_uses_league_period_type(self):
        league={'segmentId':0,'status':{'currentMatchupPeriod':1},
                'settings':{'scheduleSettings':{'periodTypeId':2,'matchupPeriods':{'1':[1]}}}}
        season={'segments':[{'id':0,'periodTypes':[{'id':2,'periods':[
            {'id':1,'scoringPeriodStart':1,'scoringPeriodEnd':6},
            {'id':2,'scoringPeriodStart':7,'scoringPeriodEnd':13}]}]}]}
        self.assertEqual(matchup_bounds(league,season),(1,6))

    def test_live_year_not_previous_year_in_blend(self):
        raw={'stats':[{'id':'102026','stats':{'42':1,'0':999}},
                      {'id':'102027','stats':{'42':2,'0':40}},
                      {'id':'032027','stats':{'42':2,'0':20}}]}
        result=player_baselines(raw,2027,{0:1})
        self.assertEqual(result['seasonBaseline'],20)
        self.assertEqual(result['recentBlend'],15)

    def test_missing_baseline_stays_missing(self):
        self.assertIsNone(player_baselines({},2027,{0:1})['seasonBaseline'])

    def test_live_points_not_counted_again_and_slot_remains_occupied(self):
        roster=[player(1,4,50,1),player(2,12,30,2),player(3,11,40,3)]
        games={1:{'state':'in'},2:{'state':'pre'},3:{'state':'post'}}
        result=daily_projection(roster,[4,11],games,'seasonBaseline',True,True)
        self.assertEqual(result['unstartedPoints'],0)
        self.assertEqual(result['inProgressActivePlayers'],['1'])

    def test_locked_bench_game_cannot_be_activated(self):
        result=daily_projection([player(1,12,50,1)],[4],{1:{'state':'in'}},'seasonBaseline',True,True)
        self.assertEqual(result['unstartedPoints'],0)
        self.assertEqual(result['inProgressActivePlayers'],[])

    def test_health_scenarios_and_ir(self):
        roster=[player(1,4,20,1,'DAY_TO_DAY'),player(2,13,50,2),player(3,12,30,3,'OUT')]
        games={i:{'state':'pre'} for i in [1,2,3]}
        self.assertEqual(daily_projection(roster,[4,11],games,'seasonBaseline',True)['unstartedPoints'],20)
        self.assertEqual(daily_projection(roster,[4,11],games,'seasonBaseline',False)['unstartedPoints'],0)


if __name__=='__main__':unittest.main()
