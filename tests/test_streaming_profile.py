import sys
from pathlib import Path
from unittest.mock import patch
import json
from io import BytesIO
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from streaming_profile import PACIFIC, defensive_metrics, nba_ratings, teammate_context


def test_allowed_uses_opposing_players_and_possession_weighted_rating():
    games = [{"id": i, "homeProTeamId": 1, "awayProTeamId": 2} for i in (1, 2)]
    games[1].update(homeProTeamId=2, awayProTeamId=1)
    boxes = {
        1: {1: dict(points=100, possessions=80, fp=212), 2: dict(points=85, possessions=90, fp=180)},
        2: {1: dict(points=95, possessions=120, fp=189), 2: dict(points=109, possessions=110, fp=200)},
    }
    rows = defensive_metrics({1: games, 2: games, 3: []}, boxes)
    assert rows[1]["game_totals"] == [180, 200]
    assert rows[1]["allowed"] == 190
    assert rows[1]["rating"] == 97
    assert rows[1]["rating_rank"] == rows[1]["allowed_rank"] == 1
    assert rows[2]["rating_rank"] == 2
    assert 3 not in rows


def test_official_ranks_require_matching_team_coverage_and_game_counts():
    teams = {1: {"location": "Phoenix", "name": "Suns"}, 2: {"location": "Indiana", "name": "Pacers"}}
    recent = {1: list(range(5)), 2: list(range(4))}
    data = {"name": "LeagueDashTeamStats", "headers": ["TEAM_NAME", "GP", "DEF_RATING", "DEF_RATING_RANK"],
            "rowSet": [["Phoenix Suns", 5, 102.3, 1], ["Indiana Pacers", 4, 110.1, 2]]}

    def read():
        response = BytesIO(json.dumps({"resultSets": [data]}).encode())
        with patch("streaming_profile.urlopen", return_value=response):
            return nba_ratings(teams, recent, 2027, datetime(2026, 11, 10, tzinfo=PACIFIC))

    assert read() == {1: (102.3, 1), 2: (110.1, 2)}
    data["rowSet"][1][1] = 5
    assert read() == {}
    data["rowSet"].pop()
    assert read() == {}


def test_returning_peer_is_included_after_injury_flag_clears():
    # The peer returns mid-sample. Count the candidate's explicit DNP as zero,
    # but exclude a game where the candidate is absent from the box entirely.
    games = [
        {"players": {1: {"min": 30, "fp": 36}}, "dnps": {2}},
        {"players": {1: {"min": 20, "fp": 22}, 2: {"min": 32}}, "dnps": set()},
        {"players": {2: {"min": 34}}, "dnps": {1}},
        {"players": {2: {"min": 31}}, "dnps": set()},
    ]
    roster = [{"id": "2", "shortName": "A. Guard", "injuries": []},
              {"id": "3", "shortName": "B. Wing", "injuries": [{"status": "Out"}]}]
    report = "\n".join(teammate_context(games, 1, roster, {2: ["PG1"]}, {}, list("abcd")))
    assert "No flag | DNP / 32 / 34 / 31 | 2g · 10.0 MIN · 11.0 FP | 1g · 30.0 MIN · 36.0 FP" in report
    assert "B. Wing | other rotation | Out | — / — / — / — | — | 3g" in report
