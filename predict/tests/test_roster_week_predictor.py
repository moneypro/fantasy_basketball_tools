from unittest import TestCase

from common.week import Week
from predict.internal.roster_week_predictor import RosterWeekPredictor
from test_utils.create_league import create_league


class TestRosterWeekPredictor(TestCase):
    def test_predict_sanity(self):
        league = create_league(year=2023)
        currWeek = Week(league, 1)
        predictor = RosterWeekPredictor(league.teams[1].roster, currWeek)
        scores = predictor.predict()
        total_number_of_games = predictor.get_total_number_of_games()

        assert scores[0] > 0 and scores[1] > 0
        assert total_number_of_games > 0
