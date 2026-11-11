"""MCP boundary regressions; fake ESPN state, no real writes or credentials."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

pytest.importorskip("mcp", reason="Install requirements-mcp.txt to test the optional MCP adapter")

from fantasy_mcp.backend import Backend, add_drop, workflow, write_json
from fantasy_mcp.server import call
from mcp.server.fastmcp.exceptions import ToolError
from test_add_drop import FakeESPN


@pytest.fixture
def harness(tmp_path):
    api = FakeESPN()
    backend = Backend(tmp_path / "state", api_factory=lambda *args: api)
    backend.env_file = tmp_path / ".env"
    backend.env_file.write_text("LEAGUE_ID=30695\n")
    return backend, api


def preview(backend):
    return backend.preview_add_drop(1, 2, 2027, 30695, 2)["planId"]


def test_preview_and_authorization_do_not_write(harness):
    backend, api = harness
    token = preview(backend)
    assert backend.verify_plan(token)["state"] == "preview_only"
    with pytest.raises(add_drop.Refused, match="authorization"):
        backend.execute_plan(token, False)
    assert api.posts == []


def test_execute_is_atomic_and_repeat_after_restart_only_verifies(harness):
    backend, api = harness
    token = preview(backend)
    assert backend.execute_plan(token, True)["state"] == "verified_completed"
    restarted = Backend(backend.state, api_factory=lambda *args: api)
    assert restarted.execute_plan(token, True)["state"] == "verified_completed"
    assert len(api.posts) == 1
    assert {i["type"] for i in api.posts[0]["items"]} == {"ADD", "DROP"}
    assert api.posts[0]["scoringPeriodId"] == 2


@pytest.mark.parametrize("mode,state", [("timeout", "unverified"), ("pending", "pending"),
                                        ("reject", "rejected_unchanged"), ("timeout_completed", "verified_completed")])
def test_uncertain_or_rejected_attempt_is_never_resubmitted(harness, mode, state):
    backend, api = harness
    api.mode = mode
    token = preview(backend)
    assert backend.execute_plan(token, True)["state"] == state
    assert backend.execute_plan(token, True)["state"] == state
    assert len(api.posts) == 1


def test_unresolved_attempt_blocks_a_different_plan(harness):
    backend, api = harness
    first, second = preview(backend), preview(backend)
    api.mode = "timeout"
    backend.execute_plan(first, True)
    with pytest.raises(add_drop.Refused, match="unresolved"):
        backend.execute_plan(second, True)
    assert len(api.posts) == 1


def test_expired_preview_and_changed_period_refuse(harness):
    backend, api = harness
    token = preview(backend)
    path = backend.directory("plans", token) / "preview.json"
    saved = json.loads(path.read_text())
    saved["expiresAt"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    write_json(path, saved)
    with pytest.raises(add_drop.Refused, match="expired"):
        backend.execute_plan(token, True)
    token = preview(backend)
    api.data["scoringPeriodId"] += 1
    with pytest.raises(add_drop.Refused, match="changed"):
        backend.execute_plan(token, True)
    assert api.posts == []


def test_changed_roster_and_waivers_refuse(harness):
    backend, api = harness
    token = preview(backend)
    api.entries[1]["lineupSlotId"] = 11
    with pytest.raises(add_drop.Refused, match="changed"):
        backend.execute_plan(token, True)
    api.pool[1]["status"] = "WAIVERS"
    with pytest.raises(add_drop.Refused, match="not a free agent"):
        preview(backend)
    assert api.posts == []


def test_crash_after_journal_creation_never_posts(harness):
    backend, api = harness
    token = preview(backend)
    (backend.directory("plans", token) / "journal").mkdir()
    assert backend.execute_plan(token, True)["state"] == "unverified"
    assert api.posts == []


def test_team_lock_serializes_different_plans(harness):
    backend, api = harness
    token = preview(backend)
    saved = json.loads((backend.directory("plans", token) / "preview.json").read_text())
    with backend.team_lock(saved["plan"]):
        with pytest.raises(add_drop.Refused, match="Another MCP transaction"):
            backend.execute_plan(token, True)
    assert api.posts == []


def test_report_paths_and_symlinks_cannot_escape_state(harness, tmp_path):
    backend, _ = harness
    directory = backend.new_directory("reports")
    secret = tmp_path / "secret"
    secret.write_text("must not be exposed")
    (directory / "packet.json").symlink_to(secret)
    for token, filename in [(directory.name, "packet.json"), ("../secret", "packet.json"),
                            (directory.name, "../../secret")]:
        with pytest.raises(add_drop.Refused):
            backend.read_report(token, filename)
    with pytest.raises(add_drop.Refused):
        workflow("../../secret")


def test_report_invocation_is_bounded_without_shell(harness, monkeypatch):
    backend, api = harness
    def run(args, **kwargs):
        assert kwargs["timeout"] == 600
        assert "shell" not in kwargs
        directory = Path(args[args.index("--output") + 1])
        (directory / "matchup.md").write_text("# Simulated report")
        return Mock(returncode=0)
    monkeypatch.setattr("fantasy_mcp.backend.subprocess.run", run)
    result = backend.report("matchup", season=2027)
    assert result["markdown"] == "# Simulated report"
    assert api.posts == []


def test_untrusted_exception_text_is_not_returned():
    def fail():
        raise ValueError("Cookie: secret-that-must-not-leak")
    with pytest.raises(ToolError) as exc:
        asyncio.run(call(fail))
    assert "secret-that-must-not-leak" not in str(exc.value)
    assert "ValueError" in str(exc.value)


def lineup_api():
    api = Mock(season=2027, league=30695, owner="owner")
    api.get.return_value = {"id":30695, "seasonId":2027, "scoringPeriodId":6,
        "status":{"finalScoringPeriod":174}, "teams":[{"id":2,"primaryOwner":"owner"}],
        "settings":{"rosterSettings":{"lineupSlotCounts":{"11":1,"12":3,"4":1},"isBenchUnlimited":False}}}
    entries = [{"playerId":i,"lineupSlotId":slot,"playerPoolEntry":{"player":{"fullName":str(i)}}}
               for i,slot in [(1,12),(2,11),(3,4)]]
    api.roster.return_value = entries
    api.players.return_value = {i:{"onTeamId":2,"status":"ONTEAM","lineupLocked":False,
        "player":{"eligibleSlots":[11,12],"injuryStatus":"ACTIVE"}} for i in [1,2]}
    def post(payload):
        for item in payload["items"]:
            next(e for e in entries if e["playerId"] == item["playerId"])["lineupSlotId"] = item["toLineupSlotId"]
        return {"response":{"status":"EXECUTED","isPending":False}}
    api.post.side_effect = post
    return api


def test_lineup_preserves_unrelated_slots_and_repeated_call_never_posts(tmp_path):
    api = lineup_api()
    backend = Backend(tmp_path, api_factory=lambda *args: api)
    plan = backend.preview_lineup([{"player_id":1,"slot_id":11},{"player_id":2,"slot_id":12}], 6, 2027, 30695, 2)
    assert backend.execute_plan(plan["planId"], True)["state"] == "verified_completed"
    assert backend.execute_plan(plan["planId"], True)["state"] == "verified_completed"
    assert api.post.call_count == 1
    assert api.roster.return_value[2]["lineupSlotId"] == 4


def test_noop_lineup_is_verified_without_post(tmp_path):
    api = lineup_api()
    backend = Backend(tmp_path, api_factory=lambda *args: api)
    plan = backend.preview_lineup([{"player_id":1,"slot_id":12}], 6, 2027, 30695, 2)
    assert backend.execute_plan(plan["planId"], True)["state"] == "already_set"
    assert backend.execute_plan(plan["planId"], True)["state"] == "already_set"
    api.post.assert_not_called()
