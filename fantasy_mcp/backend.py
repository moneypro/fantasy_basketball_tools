"""Reuse the verified CLI/domain code without exposing arbitrary commands or paths."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents/skills"
sys.path.insert(0, str(SKILLS / "espn-add-drop/scripts"))
import add_drop
from line_up.line_up_editer import plan_explicit_moves, verify_explicit_moves
from tools.pickup_report import config

WORKFLOWS = {
    "fantasy-free-agent-research": "Pickups, usable games, rotation context and longer holds",
    "fantasy-prelock-injury-opportunities": "Significant absences and available replacement players",
    "espn-add-drop": "Authorized paired acquisitions and minimal target-date activation",
    "espn-roster-rollover": "Authorized next-day pickups using persistent local timers",
    "espn-waiver-watch": "Authorized overnight free-agent clearance watches",
}
REPORT_FILES = {"packet.json", "report.html", "research_queries.txt", "matchup.json",
                "matchup.md", "live_boxscores.json", "streaming.md", "injuries.json"}


def require(condition, message):
    add_drop.require(condition, message)


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    """Atomic state updates, including when the process is interrupted."""
    temp = path.with_name(path.name + ".tmp-" + uuid4().hex)
    try:
        temp.write_text(json.dumps(value, indent=2) + "\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def workflow(name):
    require(name in WORKFLOWS, "Unknown workflow; call list_workflows")
    directory = SKILLS / name
    return {
        "name": name,
        "instructions": (directory / "SKILL.md").read_text(),
        "references": {p.name: p.read_text() for p in sorted((directory / "references").glob("*.md"))},
        "mcpGuide": (ROOT / "docs/MCP.md").read_text(),
    }


class Backend:
    def __init__(self, state_dir=None, api_factory=None):
        self.state = Path(state_dir or ROOT / "output/mcp")
        self.env_file = ROOT / ".env"
        self.api_factory = api_factory or add_drop.ESPN

    def identity(self, season=None, league=None, team=None):
        cfg = config(self.env_file)
        today = datetime.now(ZoneInfo("America/Los_Angeles"))
        return (season or today.year + (today.month >= 7),
                league or int(cfg.get("LEAGUE_ID", "30695")),
                team or int(cfg.get("FANTASY_TEAM_ID", "2")))

    def api(self, season, league):
        return self.api_factory(season, league, str(self.env_file))

    def health(self):
        cfg = config(self.env_file)
        season, league, team = self.identity()
        return {"state": "ready", "transport": "stdio", "season": season,
                "leagueId": league, "teamId": team,
                "credentialsPresent": all(bool(cfg.get(k)) for k in ("ESPN_S2", "SWID")),
                "credentialValidity": "not_checked", "workflows": list(WORKFLOWS),
                "writes": "Only execute_plan sends ESPN mutations; requires an authorized preview",
                "scheduler": "Existing systemd runners remain independent; no job is created at startup"}

    def league_context(self, season=None, league=None, team=None):
        season, league, team = self.identity(season, league, team)
        api = self.api(season, league)
        data = api.get("?view=mSettings&view=mTeam")
        require(data["id"] == league and data["seasonId"] == season, "League/season mismatch")
        selected = next((t for t in data["teams"] if t["id"] == team), None)
        require(selected is not None, "Team not found")
        settings = data["settings"]
        return {"season": season, "leagueId": league, "teamId": team,
                "leagueName": settings.get("name"), "teamName": selected.get("name"),
                "scoringPeriod": data["scoringPeriodId"],
                "transactionScoringPeriod": data["status"].get("transactionScoringPeriod", data["scoringPeriodId"]),
                "matchupPeriod": data["status"].get("currentMatchupPeriod"),
                "isActive": data["status"].get("isActive"),
                "transactionCounter": selected.get("transactionCounter", {}),
                "waiverRank": selected.get("waiverRank"),
                "settings": {k: settings.get(k) for k in ("rosterSettings", "scoringSettings",
                                                           "acquisitionSettings", "scheduleSettings")},
                "fetchedAt": add_drop.now()}

    @staticmethod
    def player(entry):
        p = entry["player"]
        return {"id": p["id"], "name": p["fullName"], "nbaTeamId": p.get("proTeamId"),
                "ownerTeamId": entry.get("onTeamId"), "availability": entry.get("status"),
                "injury": p.get("injuryStatus"), "eligibleSlots": p.get("eligibleSlots", []),
                "waiverProcessDate": entry.get("waiverProcessDate"),
                "lineupLocked": entry.get("lineupLocked"), "rosterLocked": entry.get("rosterLocked"),
                "droppable": p.get("droppable")}

    def roster(self, period=None, season=None, league=None, team=None):
        ctx = self.league_context(season, league, team)
        period = period or ctx["scoringPeriod"]
        api = self.api(ctx["season"], ctx["leagueId"])
        rows = api.roster(period, ctx["teamId"])
        return {"context": ctx, "period": period, "players": [
            {**self.player(e["playerPoolEntry"]), "slot": e["lineupSlotId"]} for e in rows]}

    def players(self, player_ids, season=None, league=None):
        season, league, _ = self.identity(season, league)
        api = self.api(season, league)
        data = api.get("?view=mSettings")
        require(data["id"] == league and data["seasonId"] == season, "League/season mismatch")
        period = data["status"].get("transactionScoringPeriod", data["scoringPeriodId"])
        pool = api.players(period, player_ids)
        require(set(player_ids) <= pool.keys(), "One or more player IDs missing from live pool")
        return {"season": season, "leagueId": league, "effectivePeriod": period,
                "fetchedAt": add_drop.now(), "players": [self.player(pool[p]) for p in player_ids]}

    def new_directory(self, category):
        directory = self.state / category / uuid4().hex
        directory.mkdir(parents=True, mode=0o700)
        return directory

    def directory(self, category, token):
        require(re.fullmatch(r"[a-f0-9]{32}", token) is not None, "Invalid artifact ID")
        base = (self.state / category).resolve()
        directory = (base / token).resolve()
        require(directory.parent == base and directory.is_dir(), "Unknown artifact ID")
        return directory

    def report(self, kind, *, season=None, league=None, team=None, days=14,
               limit=35, player_ids=None, compare_drop=None):
        season, league, team = self.identity(season, league, team)
        scripts = {"pickup": "tools/pickup_report.py", "matchup": "tools/matchup_report.py",
                   "streaming": "tools/streaming_profile.py",
                   "injuries": ".agents/skills/fantasy-free-agent-research/scripts/injury_context.py"}
        require(kind in scripts, "Unknown report type")
        directory = self.new_directory("reports")
        args = [sys.executable, str(ROOT / scripts[kind]), "--season", str(season), "--league", str(league)]
        if kind == "pickup":
            args += ["--team", str(team), "--days", str(days), "--limit", str(limit), "--output", str(directory)]
            if compare_drop:
                args += ["--compare-drop", str(compare_drop)]
            if player_ids:
                args += ["--watch", *map(str, player_ids)]
        elif kind == "matchup":
            args += ["--team", str(team), "--output", str(directory)]
        elif kind == "streaming":
            require(player_ids, "Streaming profiles require player IDs")
            args += ["--days", str(days), "--output", str(directory / "streaming.md"), *map(str, player_ids)]
        else:
            args += ["--output", str(directory / "injuries.json")]
        # Fixed entrypoints, no shell, no user-supplied environment or output paths.
        try:
            result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            raise add_drop.Refused("Report timed out; no ESPN mutations were made") from None
        require(result.returncode == 0, "Report failed; no stale data substituted. Check credentials, season and ESPN availability")
        files = sorted(p.name for p in directory.iterdir() if p.name in REPORT_FILES)
        response = {"state": "read_only_completed", "reportId": directory.name, "kind": kind,
                    "files": files, "directory": str(directory),
                    "resources": [f"fantasy://reports/{directory.name}/{f}" for f in files]}
        if kind == "pickup":
            packet = read_json(directory / "packet.json")
            response.update({k: packet[k] for k in ("meta", "warnings", "roster", "candidates", "scenarios")})
        elif kind == "injuries":
            packet = read_json(directory / "injuries.json")
            response.update({k: packet[k] for k in ("fetchedAt", "teams", "limitations")})
        else:
            response["markdown"] = (directory / ("matchup.md" if kind == "matchup" else "streaming.md")).read_text()
        return response

    def read_report(self, report_id, filename):
        require(filename in REPORT_FILES, "Unknown report filename")
        directory = self.directory("reports", report_id)
        path = (directory / filename).resolve()
        require(path.parent == directory and path.is_file(), "Report file missing or outside report directory")
        return path.read_text()

    def save_plan(self, kind, plan):
        directory = self.new_directory("plans")
        saved = {"kind": kind, "plan": plan,
                 "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}
        write_json(directory / "preview.json", saved)
        return {"state": "preview_only", "planId": directory.name, **saved}

    def preview_add_drop(self, add_id, drop_id, season=None, league=None, team=None):
        season, league, team = self.identity(season, league, team)
        plan = add_drop.preflight(self.api(season, league), team, add_id, drop_id)
        return self.save_plan("add_drop", plan)

    def preview_lineup(self, moves, period, season=None, league=None, team=None):
        season, league, team = self.identity(season, league, team)
        require(len({m["player_id"] for m in moves}) == len(moves), "Duplicate player move")
        plan = plan_explicit_moves(self.api(season, league), team, period,
                                   {m["player_id"]: m["slot_id"] for m in moves})
        plan["requestedMoves"] = {m["player_id"]: m["slot_id"] for m in moves}
        return self.save_plan("lineup", plan)

    @contextmanager
    def team_lock(self, plan):
        locks = self.state / "locks"
        locks.mkdir(parents=True, exist_ok=True)
        with (locks / f"{plan['season']}-{plan['league']}-{plan['team']}.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise add_drop.Refused("Another MCP transaction is running for this team") from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    @staticmethod
    def same_plan(kind, old, fresh):
        keys = ("payload", "beforeRoster", "currentPeriod", "effectivePeriod", "add", "drop") if kind == "add_drop" else (
            "payload", "before", "expectedSlots", "period")
        # JSON round trip normalizes the integer dict keys saved on disk.
        return json.dumps({k: old[k] for k in keys}, sort_keys=True) == json.dumps(
            {k: fresh[k] for k in keys}, sort_keys=True)

    def execute_plan(self, plan_id, authorized):
        require(authorized is True, "Execution requires the user's authorization for this exact move")
        directory = self.directory("plans", plan_id)
        saved = read_json(directory / "preview.json")
        plan, kind = saved["plan"], saved["kind"]
        with self.team_lock(plan):
            # Repeated calls/restarts only reconcile the original journal, even after expiry.
            if (directory / "journal").exists():
                return self.verify_plan(plan_id)
            require(datetime.now(timezone.utc) <= datetime.fromisoformat(saved["expiresAt"]),
                    "Preview expired; create a fresh preview")
            for other in (self.state / "plans").glob("*/journal"):
                other_saved = read_json(other.parent / "preview.json")["plan"]
                if any(other_saved[k] != plan[k] for k in ("season", "league", "team")):
                    continue
                status_file = other / "verification.json"
                if not status_file.exists():
                    status_file = other / "result.json"
                state = read_json(status_file).get("state") if status_file.exists() else "unverified"
                require(state in ("verified_completed", "already_set", "rejected_unchanged"),
                        "An earlier MCP attempt is unresolved; verify it before another transaction")
            api = self.api(plan["season"], plan["league"])
            if kind == "add_drop":
                fresh = add_drop.preflight(api, plan["team"], plan["add"]["id"], plan["drop"]["id"])
            else:
                fresh = plan_explicit_moves(api, plan["team"], plan["period"],
                                            {int(k): v for k, v in plan["requestedMoves"].items()})
            require(self.same_plan(kind, plan, fresh), "Roster, period or transaction changed; create a fresh preview")
            journal = directory / "journal"
            if kind == "add_drop":
                result = add_drop.execute(api, fresh, journal)
            else:
                journal.mkdir()  # Durable barrier before a possible POST.
                write_json(journal / "plan.json", fresh)
                if not fresh["payload"]["items"]:
                    result = {"state": "already_set", "period": fresh["period"]}
                else:
                    write_json(journal / "attempt.json", {"startedAt": add_drop.now()})
                    submission = api.post(fresh["payload"])
                    write_json(journal / "submission.json", submission)
                    try:
                        result = verify_explicit_moves(api, fresh, submission)
                    except (add_drop.Refused, KeyError, StopIteration, OSError):
                        result = {"state": "unverified", "reason": "Readback failed; call verify_plan"}
                write_json(journal / "result.json", result)
            return {"planId": plan_id, "kind": kind, **result}

    def verify_plan(self, plan_id):
        directory = self.directory("plans", plan_id)
        saved = read_json(directory / "preview.json")
        journal = directory / "journal"
        if not journal.exists():
            return {"state": "preview_only", "planId": plan_id, "expiresAt": saved["expiresAt"]}
        if not (journal / "plan.json").exists():
            return {"state": "unverified", "planId": plan_id, "reason": "Incomplete journal; do not resubmit"}
        plan = read_json(journal / "plan.json")
        api = self.api(plan["season"], plan["league"])
        submission = read_json(journal / "submission.json") if (journal / "submission.json").exists() else {}
        if saved["kind"] == "add_drop":
            result = add_drop.verify(api, plan, submission)
        elif not plan["payload"]["items"]:
            roster = add_drop.roster_summary(api.roster(plan["period"], plan["team"]))
            expected = {int(k): v for k, v in plan["expectedSlots"].items()}
            result = {"state": "already_set" if {p['id']: p['slot'] for p in roster} == expected else "unverified"}
        else:
            result = verify_explicit_moves(api, plan, submission)
        write_json(journal / "verification.json", result)
        return {"planId": plan_id, "kind": saved["kind"], **result}
