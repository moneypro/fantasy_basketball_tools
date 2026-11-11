"""Offline checks for report decisions that could change an add/drop recommendation."""
from tools.pickup_report import average, best_lineup, box_points, can_use_game, normalize, planning_windows, render


def player(pid, points, slots, injury="ACTIVE"):
    return {"id": pid, "projected": points, "eligibleSlots": slots, "injury": injury}


def test_lineup_reassigns_flexible_player_and_does_not_count_twice():
    points, picks = best_lineup([player(1, 40, [0, 1]), player(2, 35, [0]), player(3, 30, [1])], [0, 1])
    assert points == 75
    assert set(picks) == {(1, 1), (2, 0)}


def test_injured_and_unknown_projections_do_not_fill_slots():
    points, picks = best_lineup([player(1, 50, [4], "OUT"), player(2, None, [4]), player(3, 24, [4])], [4])
    assert points == 24
    assert picks == [(3, 4)]


def test_missing_season_is_unknown_and_custom_scoring_is_applied():
    p = {"stats": [{"id": "102027", "stats": {"42": 2, "0": 40, "2": 3}}]}
    assert average(p, 2027, True, {0: 1, 2: 4}) == 26
    assert average(p, 2026, False, {0: 1}) is None


def test_live_line_uses_full_points_formula_and_rejects_missing_data():
    stats = {"PTS": "22", "REB": "9", "AST": "1", "STL": "1", "BLK": "1", "TO": "1", "FG": "8-13", "FT": "6-7", "3PT": "0-0"}
    weights = {0: 1, 6: 1, 3: 2, 2: 4, 1: 4, 11: -2, 13: 2, 14: -1, 15: 1, 16: -1, 17: 1}
    assert box_points(stats, weights) == 41
    del stats["REB"]
    assert box_points(stats, weights) is None


def test_ownership_and_waivers_survive_normalization():
    entry = {"onTeamId": 14, "status": "ONTEAM", "waiverProcessDate": 1234, "player": {"id": 1, "fullName": "Example", "proTeamId": 2}}
    p = normalize(entry, 2027, {}, {2: {"abbrev": "BOS"}}, {})
    assert p["ownerTeamId"] == 14
    assert p["availability"] == "ONTEAM"
    assert p["projected"] is None
    assert p["waiverProcessDate"] == 1234


def test_waiver_clearance_does_not_allow_earlier_games():
    p = {"availability": "WAIVERS", "waiverProcessDate": 2000}
    assert not can_use_game(p, {"date": 1999}, True)
    assert can_use_game(p, {"date": 2000}, True)
    p["waiverProcessDate"] = None
    assert not can_use_game(p, {"date": 3000}, True)
    p["availability"] = "FREEAGENT"
    assert can_use_game(p, {"date": 3000}, True)


def test_calendar_windows_are_distinct_from_rolling_week():
    from datetime import date, timedelta
    days = [(date(2026, 10, 21) + timedelta(days=i)).isoformat() for i in range(14)]
    windows = planning_windows(days)
    assert windows['restOfCalendarWeek'] == days[:5]
    assert windows['nextCalendarWeek'] == days[5:12]
    assert windows['next7Days'] == days[:7]
    assert windows['fullHorizon'] == days


def test_html_escapes_research_and_marks_unreviewed_reports():
    packet = {"meta": {"date": "2026-10-20", "teamName": "<script>", "leagueName": "League", "season": 2027, "leagueSize": 14, "fetchedAt": "now"}, "warnings": [], "matchup": {}, "roster": [], "candidates": [], "liveAvailable": [], "daily": [], "scenarios": [], "news": [], "sources": []}
    html = render(packet)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Research review pending" in html
