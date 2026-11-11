"""Read-only ESPN pickup research packet and printable HTML report.

Run from the repository root: python3 tools/pickup_report.py --season 2027 --team 2
Only GET requests are made. Credentials are never included in saved artifacts.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PACIFIC = ZoneInfo("America/Los_Angeles")
SLOTS = {0: "PG", 1: "SG", 2: "SF", 3: "PF", 4: "C", 5: "G", 6: "F", 11: "UT", 12: "BE", 13: "IR"}
STAT_IDS = {"PTS": 0, "BLK": 1, "STL": 2, "AST": 3, "REB": 6, "TO": 11, "FGM": 13, "FGA": 14, "FTM": 15, "FTA": 16, "3PM": 17}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def config(path):
    """Read simple KEY=value dotenv entries without evaluating shell code."""
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("\"'")
    return {**values, **os.environ}


class Collector:
    def __init__(self, output):
        self.output = output
        self.sources = []

    def get(self, name, url, headers=None, optional=False):
        stamp = utc_now()
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=25) as response:
                data = json.load(response)
            self.sources.append({"name": name, "url": url, "fetchedAt": stamp, "status": "ok"})
            # Raw league responses can include member identities; save normalized data instead.
            return data
        except (OSError, ValueError) as exc:
            kind = f"HTTP {exc.code}" if isinstance(exc, urllib.error.HTTPError) else type(exc).__name__
            self.sources.append({"name": name, "url": url, "fetchedAt": stamp, "status": kind})
            if not optional:
                raise RuntimeError(f"{name}: {kind}; no stale data substituted") from None
            return None


def average(player, season, projected, weights):
    stat = next((s for s in player.get("stats", []) if s.get("id") == f"{1 if projected else 0}0{season}"), None)
    if not stat or not stat.get("stats") or not stat["stats"].get("42"):
        return None
    return sum(stat["stats"].get(str(k), 0) * v for k, v in weights.items()) / stat["stats"]["42"]


def box_points(stats, weights):
    """Return unknown for incomplete lines; never infer missing stats as zero."""
    try:
        values = {key: float(stats[key]) for key in ("PTS", "REB", "AST", "STL", "BLK", "TO")}
        for key, made, attempted in (("FG", "FGM", "FGA"), ("FT", "FTM", "FTA"), ("3PT", "3PM", "3PA")):
            values[made], values[attempted] = map(float, stats[key].split("-"))
        return sum(values[key] * weights.get(stat_id, 0) for key, stat_id in STAT_IDS.items())
    except (KeyError, ValueError, TypeError):
        return None


def best_lineup(players, slots):
    """Maximum projected points with unique players and legal overlapping eligibility."""
    states = {0: (0.0, [])}
    for p in players:
        if p["projected"] is None or p["injury"] in {"OUT", "INJURY_RESERVE", "SUSPENSION"}:
            continue
        updated = dict(states)
        for mask, (score, picks) in states.items():
            for index, slot in enumerate(slots):
                bit = 1 << index
                if not mask & bit and slot in p["eligibleSlots"]:
                    new_mask, new_score = mask | bit, score + p["projected"]
                    if new_mask not in updated or new_score > updated[new_mask][0]:
                        updated[new_mask] = (new_score, picks + [(p["id"], slot)])
        states = updated
    return max(states.values(), key=lambda item: item[0])


def can_use_game(player, game, is_new=False):
    """Conservatively omit waived players until a known claim processing time."""
    if not is_new or player["availability"] != "WAIVERS":
        return True
    clears = player.get("waiverProcessDate")
    return clears is not None and game["date"] >= clears


def planning_windows(days):
    """Calendar weeks and rolling horizons are explicit, never guessed matchup weeks."""
    start = date.fromisoformat(days[0])
    sunday = start + timedelta(days=6 - start.weekday())
    monday = sunday + timedelta(days=1)
    return {
        "restOfCalendarWeek": [d for d in days if date.fromisoformat(d) <= sunday],
        "nextCalendarWeek": [d for d in days if monday <= date.fromisoformat(d) <= monday + timedelta(days=6)],
        "next7Days": days[:7],
        "fullHorizon": days,
    }


def normalize(entry, season, weights, teams, roster_slots):
    p = entry["player"]
    return {
        "id": p["id"], "name": p["fullName"], "nbaTeamId": p.get("proTeamId"),
        "team": teams.get(p.get("proTeamId"), {}).get("abbrev", "FA"),
        "ownerTeamId": entry.get("onTeamId"), "availability": entry.get("status", "UNKNOWN"),
        "injury": p.get("injuryStatus", "UNKNOWN"), "eligibleSlots": p.get("eligibleSlots", []),
        "slot": roster_slots.get(p["id"]), "projected": average(p, season, True, weights),
        "previous": average(p, season - 1, False, weights),
        "waiverProcessDate": entry.get("waiverProcessDate"),
        "lineupLocked": entry.get("lineupLocked"), "rosterLocked": entry.get("rosterLocked"),
        "undroppable": p.get("droppable") is False,
    }


def table(headers, rows):
    return "<div class='scroll'><table><thead><tr>" + "".join(f"<th>{escape(str(x))}</th>" for x in headers) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>" for row in rows) + "</tbody></table></div>"


def fmt(value):
    return "unknown" if value is None else f"{value:.1f}"


def render(packet, notes=None):
    meta = packet["meta"]
    horizon_label = f"Next {len(meta.get('horizon', range(7)))} days"
    body = [f"<h1>Pickup research · {escape(meta['date'])}</h1>", f"<p>{escape(meta['teamName'])} · {escape(meta['leagueName'])} · season {meta['season']} · {meta['leagueSize']} teams</p>", f"<p class='muted'>Collected {escape(meta['fetchedAt'])}. All times below are Pacific. Read-only; no roster moves submitted.</p>"]
    if notes:
        body += ["<h2>Research conclusions</h2>"]
        for section in notes.get("sections", []):
            body.append(f"<h3>{escape(section['title'])}</h3>")
            body.extend(f"<p>{escape(x)}</p>" for x in section.get("paragraphs", []))
            for source in section.get("sources", []):
                if source["url"].startswith("https://"):
                    body.append(f"<p class='source'><a href='{escape(source['url'], quote=True)}'>{escape(source['title'])}</a></p>")
    else:
        body.append("<p class='notice'>Research review pending: tables are screening data, not final add/drop recommendations. ESPN news is collected below; Reddit requires a fresh human/assistant review.</p>")
    body += ["<h2>League and freshness</h2>", "<ul>" + "".join(f"<li>{escape(x)}</li>" for x in packet["warnings"]) + "</ul>", "<pre>" + escape(json.dumps(packet["matchup"], indent=2)) + "</pre>"]
    if packet.get('slate'):
        body += ["<h2>NBA slate</h2>", table(['Game', 'Status', 'Score'], [[g['name'], g['status'], g['score']] for g in packet['slate']])]
    body += ["<h2>Current roster</h2>", table(["Player", "NBA", "Slot", "Health", "Projected FP/G", "Previous FP/G", horizon_label], [[p["name"], p["team"], SLOTS.get(p["slot"], p["slot"]), p["injury"], fmt(p["projected"]), fmt(p["previous"]), ", ".join(p["gameDates"])] for p in packet["roster"]])]
    body += ["<h2>Available players · projection screening</h2>", table(["Player", "NBA", "Availability", "Health", "Projected FP/G", "Clears (PT)", horizon_label], [[p["name"], p["team"], p["availability"], p["injury"], fmt(p["projected"]), datetime.fromtimestamp(p["waiverProcessDate"] / 1000, PACIFIC).strftime("%m/%d %H:%M") if p["waiverProcessDate"] else "—", ", ".join(p["gameDates"])] for p in packet["candidates"]])]
    body += [f"<h2>Available players from the {escape(meta.get('slateDate', meta['date']))} slate</h2>", "<p>Fantasy points recalculated with your scoring rules. In-progress lines are provisional; completed production cannot be acquired retroactively.</p>", table(["Player", "Game status", "MIN", "PTS", "REB", "AST", "STL", "BLK", "Fantasy points", "Availability"], [[p["name"], p["gameStatus"], *[p["stats"].get(k, "—") for k in ("MIN", "PTS", "REB", "AST", "STL", "BLK")], fmt(p["fantasyPoints"]), p["availability"]] for p in packet["liveAvailable"]])]
    body += ["<h2>Daily lineup capacity</h2>", table(["Date", "Healthy scheduled players", "Filled slots", "Projected total", "Open positions"], [[d["date"], d["scheduled"], len(d["lineup"]), fmt(d["points"]), ", ".join(d["openSlots"])] for d in packet["daily"]])]
    body += ["<h2>Replacement scenarios</h2>", "<p>Static season-projection model, not injury-adjusted forecasts. Assumes OUT players remain out and others play every scheduled game, reoptimizes legal starters daily, and excludes games before waiver clearance. Includes DTD risk. Assumes a waiver claim wins; acquisition/lineup locks still require ESPN validation. Gain conservatively excludes the dropped player throughout. Calendar weeks are not verified fantasy matchup boundaries.</p>", table(["Add", "Drop", "Full horizon gain"], [[s["add"], s["drop"], fmt(s["gain"])] for s in packet["scenarios"][:30]])]
    if packet.get('windows'):
        body.append('<h2>Week-by-week comparison</h2>')
        body.extend(f"<p>{escape(key)}: {escape(ds[0])} through {escape(ds[-1])}</p>" for key, ds in packet['windows'].items() if ds)
        body.append(table(['Add', 'Drop', 'Rest of week', 'Next calendar week', 'Next 7 days', 'Full horizon'], [[s['add'], s['drop'], *[fmt(s['windowGains'][k]) for k in packet['windows']]] for s in packet['scenarios'] if s['dropId'] == packet.get('preferredDropId')]))
    body.append("<h2>ESPN news review</h2><p>Timestamped ESPN/RotoWire headlines; read the linked feed for context. Old headlines are not current confirmations.</p>")
    for n in packet["news"]:
        r = n.get("rotowire") or {}
        headline = r.get('headline', 'No headline returned').split()
        excerpt = ' '.join(headline[:20]) + (' …' if len(headline) > 20 else '')
        body.append(f"<p><b>{escape(n['name'])}</b> · {escape(r.get('published', 'No dated update'))}<br>{escape(excerpt)}<br><a href='{escape(n['url'], quote=True)}'>ESPN source feed</a></p>")
    body.append("<h2>Source audit</h2>" + table(["Source", "Retrieved (UTC)", "Status"], [[s["name"], s["fetchedAt"], s["status"]] for s in packet["sources"]]))
    return "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Fantasy pickup report</title><style>body{font:16px/1.55 system-ui;max-width:1160px;margin:40px auto;padding:0 22px;color:#172334;background:#f8fafc}h1{font-size:32px}h2{margin-top:38px;border-bottom:2px solid #ccd7e1}h3{color:#185c4a}table{border-collapse:collapse;width:100%;font-size:14px;background:white}th,td{text-align:left;padding:10px;border-bottom:1px solid #dce3e9}th{background:#e8eff5}.scroll{overflow:auto}.muted,.source{font-size:13px;color:#516276}.notice{padding:16px;background:#fff1ce}a{color:#146854}pre{white-space:pre-wrap}@media print{body{background:white;margin:0;font-size:12px}table{font-size:10px}h2{break-after:avoid}.scroll{overflow:visible}}</style><body>" + "\n".join(body) + "</body></html>"


def collect(args):
    cfg = config(Path(args.env_file))
    league_id = int(args.league or cfg["LEAGUE_ID"])
    headers = {"Cookie": f"espn_s2={cfg['ESPN_S2']}; SWID={cfg['SWID']}"}
    output = Path(args.output or ROOT / "output" / f"pickup_report_{args.date}_{datetime.now(PACIFIC):%H%M%S}")
    output.mkdir(parents=True, exist_ok=True)
    c = Collector(output)
    base = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{args.season}/segments/0/leagues/{league_id}"
    health = c.get("dashboard_health", args.dashboard.rstrip('/') + '/api/health', optional=True)
    league = c.get("league", base + "?view=mSettings&view=mTeam&view=mRoster&view=mMatchupScore", headers)
    if league.get("seasonId") != args.season or league.get("id") != league_id:
        raise RuntimeError("League or season mismatch")
    settings = league["settings"]
    if settings["scoringSettings"]["scoringType"] != "H2H_POINTS":
        raise RuntimeError("This report supports head-to-head points leagues only")
    weights = {x["statId"]: x["points"] for x in settings["scoringSettings"]["scoringItems"]}
    if set(weights) - set(STAT_IDS.values()):
        raise RuntimeError("Unsupported scoring stats; refusing incomplete box-score scoring")
    current_period = league["scoringPeriodId"]
    transaction_period = league["status"].get("transactionScoringPeriod", current_period)
    next_roster = c.get("transaction_roster", base + f"?view=mRoster&scoringPeriodId={transaction_period}", headers)
    team = next(t for t in league["teams"] if t["id"] == args.team)
    transaction_team = next(t for t in next_roster["teams"] if t["id"] == args.team)
    entries = transaction_team["roster"]["entries"]
    roster_slots = {e["playerId"]: e["lineupSlotId"] for e in entries}
    pro = c.get("schedule", f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{args.season}?view=proTeamSchedules")
    teams = {t["id"]: t for t in pro["settings"]["proTeams"]}
    # Make explicit dates agree with this live season and current scoring period.
    period_dates = {datetime.fromtimestamp(g['date'] / 1000, PACIFIC).date().isoformat() for t in teams.values() for g in t.get('proGamesByScoringPeriod', {}).get(str(current_period), [])}
    if args.date not in period_dates:
        raise RuntimeError(f"Requested date {args.date} does not match the live scoring-period dates {sorted(period_dates)}; historical rosters require a separate workflow")
    pool, seen = [], set()
    for offset in range(0, 10000, 500):
        filt = {"players": {"limit": 500, "offset": offset, "sortDraftRanks": {"sortPriority": 1, "sortAsc": True, "value": "STANDARD"}, "filterStatsForTopScoringPeriodIds": {"value": 1, "additionalValue": [f"00{args.season - 1}", f"10{args.season}", f"00{args.season}"]}}}
        chunk = c.get(f"players_{offset}", base + f"?view=kona_player_info&scoringPeriodId={current_period}", {**headers, "x-fantasy-filter": json.dumps(filt)})["players"]
        new = [p for p in chunk if p["id"] not in seen]
        if chunk and not new:
            raise RuntimeError("Player pagination did not advance")
        pool.extend(new)
        seen.update(p["id"] for p in new)
        if len(chunk) < 500:
            break
    else:
        raise RuntimeError("Player pool exceeded pagination limit")
    players = {e["id"]: normalize(e, args.season, weights, teams, roster_slots) for e in pool}
    owned = {p["id"] for p in players.values() if p["ownerTeamId"] == args.team}
    if owned != set(roster_slots):
        raise RuntimeError("Ownership and transaction roster disagree; rerun after ESPN finishes updating")
    roster = [players[e["playerId"]] for e in entries]
    available = [p for p in players.values() if p["ownerTeamId"] == 0 and p["availability"] in {"FREEAGENT", "WAIVERS"}]
    available.sort(key=lambda p: p["projected"] if p["projected"] is not None else -1, reverse=True)
    candidates = available[:args.limit]
    candidates += [p for p in available[args.limit:] if p['id'] in args.watch]
    transaction_dates = sorted({datetime.fromtimestamp(g['date'] / 1000, PACIFIC).date().isoformat() for t in teams.values() for g in t.get('proGamesByScoringPeriod', {}).get(str(transaction_period), [])})
    start = date.fromisoformat(args.start_date or max(args.date, transaction_dates[0] if transaction_dates else args.date))
    if start < date.fromisoformat(args.date):
        raise RuntimeError('Planning start cannot precede the live report date')
    days = [(start + timedelta(days=n)).isoformat() for n in range(args.days)]
    windows = planning_windows(days)
    games = {}
    for tid, t in teams.items():
        for period, gs in t.get("proGamesByScoringPeriod", {}).items():
            for g in gs:
                day = datetime.fromtimestamp(g["date"] / 1000, PACIFIC).date().isoformat()
                if day in days and not g.get("canceled") and not g.get("postponed") and int(period) >= transaction_period and g['date'] / 1000 > datetime.now(timezone.utc).timestamp():
                    games.setdefault((tid, day), []).append(g)
    for p in players.values():
        p["gameDates"] = [day for day in days if (p["nbaTeamId"], day) in games]
    slots = [int(s) for s, count in settings["rosterSettings"]["lineupSlotCounts"].items() if int(s) not in (12, 13, 14) for _ in range(count)]
    def lineup(roster, day, new_id=None):
        playing = [p for p in roster if p["slot"] != 13 and any(can_use_game(p, g, p["id"] == new_id) for g in games.get((p["nbaTeamId"], day), []))]
        return best_lineup(playing, slots)
    daily = []
    for day in days:
        points, selected = lineup(roster, day)
        open_slots = list(slots)
        for _, slot in selected:
            open_slots.remove(slot)
        daily.append({"date": day, "points": points, "lineup": selected, "openSlots": [SLOTS.get(s, str(s)) for s in open_slots], "scheduled": sum(day in p["gameDates"] and p["slot"] != 13 and p["injury"] not in {"OUT", "INJURY_RESERVE", "SUSPENSION"} for p in roster)})
    slate_date = args.slate_date or args.date
    board = c.get("nba_scoreboard", "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=" + slate_date.replace("-", ""))
    slate = [{"id": e['id'], "name": e['name'], "status": e['status']['type']['detail'], "complete": e['status']['type']['completed'], "score": ' / '.join(f"{t['team']['abbreviation']} {t.get('score', '?')}" for t in e['competitions'][0]['competitors'])} for e in board.get('events', [])]
    def box(event):
        return event, c.get("game_" + event["id"], "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=" + event["id"], optional=True)
    live = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        for event, b in executor.map(box, board.get("events", [])):
            if not b:
                continue
            status = b.get("header", {}).get("competitions", [{}])[0].get("status", event["status"])["type"]["detail"]
            for t in b.get("boxscore", {}).get("players", []):
                for tab in t.get("statistics", []):
                    for row in tab.get("athletes", []):
                        p = players.get(int(row["athlete"]["id"]))
                        if not p or p not in available or row.get("didNotPlay") or not row.get("stats"):
                            continue
                        stats = dict(zip(tab["labels"], row["stats"]))
                        live.append({"id": p["id"], "name": p["name"], "availability": p["availability"], "gameId": event["id"], "gameStatus": status, "stats": stats, "fantasyPoints": box_points(stats, weights)})
    live.sort(key=lambda p: p["fantasyPoints"] if p["fantasyPoints"] is not None else -1, reverse=True)
    baseline = sum(d["points"] for d in daily)
    drops = sorted([p for p in roster if p["slot"] != 13 and p["projected"] is not None and not p["undroppable"]], key=lambda p: p["projected"])[:4]
    scenario_candidates = {p["id"]: p for p in candidates if p["injury"] not in {"OUT", "INJURY_RESERVE", "SUSPENSION"}}
    scenario_candidates.update({p["id"]: players[p["id"]] for p in live[:5]})
    scenarios = []
    for add in scenario_candidates.values():
        if add["projected"] is None:
            continue
        for drop in drops:
            totals = {day: lineup([p for p in roster if p["id"] != drop["id"]] + [add], day, add["id"])[0] for day in days}
            gains = {key: round(sum(totals[d['date']] - d['points'] for d in daily if d['date'] in ds), 2) for key, ds in windows.items()}
            scenarios.append({"addId": add["id"], "dropId": drop["id"], "add": add["name"], "drop": drop["name"], "gain": gains['fullHorizon'], "windowGains": gains})
    scenarios.sort(key=lambda s: s["gain"], reverse=True)
    news_ids = set(p["id"] for p in roster) | set(p["id"] for p in candidates[:12]) | set(p["id"] for p in live[:5]) | set(args.watch)
    def news(pid):
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{pid}/overview"
        result = c.get(f"news_{pid}", url, optional=True)
        return {"id": pid, "name": players.get(pid, {}).get("name", str(pid)), "url": url, "rotowire": (result or {}).get("rotowire")}
    with ThreadPoolExecutor(max_workers=4) as executor:
        news_rows = list(executor.map(news, sorted(news_ids)))
    matchup_id = league["status"]["currentMatchupPeriod"]
    matchup = next((m for m in league.get("schedule", []) if m.get("matchupPeriodId") == matchup_id and args.team in (m.get("home", {}).get("teamId"), m.get("away", {}).get("teamId"))), {})
    matchup_summary = {side: {"team": next((t.get("name") for t in league["teams"] if t["id"] == matchup.get(side, {}).get("teamId")), "unknown"), "livePoints": matchup.get(side, {}).get("totalPointsLive"), "settledPoints": matchup.get(side, {}).get("totalPoints")} for side in ("home", "away")}
    used = team.get("transactionCounter", {}).get("matchupAcquisitionTotals", {}).get(str(matchup_id), 0)
    limit = settings["acquisitionSettings"].get("matchupAcquisitionLimit")
    warnings = [f"Current scoring period {current_period}; transactions effective period {transaction_period}. Today's and transaction-period rosters may differ.", f"Acquisitions this matchup: {used}; configured limit: {limit}. Waiver priority {team.get('waiverRank', 'unknown')}. Seven-day schedule is a planning horizon, not a verified matchup end date.", "Projection baselines are full-season FP/G, not recent form. Missing projections remain unknown. Availability uses onTeamId AND FREEAGENT/WAIVERS status.", "OUT/IR players excluded for the entire planning horizon; reassess when their injury status changes. DTD players are not probability-discounted.", "No transactions, lineup moves, or recurring jobs created. Recheck ESPN ownership, claim time, player locks and news before acting."]
    if not health or health.get("season") != args.season:
        warnings.append("Dashboard unavailable or season mismatch; direct authenticated ESPN reads used.")
    else:
        warnings.append("Local dashboard health verified; direct ESPN roster/ownership endpoints used because the dashboard focuses on draft picks.")
    packet = {"meta": {"date": args.date, "fetchedAt": utc_now(), "season": args.season, "leagueId": league_id, "teamId": args.team, "teamName": team.get("name", str(args.team)), "leagueName": settings["name"], "leagueSize": settings["size"], "weights": weights, "horizon": days, "baseline": baseline}, "warnings": warnings, "matchup": matchup_summary, "roster": roster, "candidates": candidates, "liveAvailable": live, "daily": daily, "scenarios": scenarios, "news": news_rows, "sources": c.sources}
    packet.update({'slate': slate, 'windows': windows, 'preferredDropId': args.compare_drop})
    packet['meta']['slateDate'] = slate_date
    packet['warnings'] = [w.replace('Seven-day schedule', 'Forward schedule') for w in packet['warnings']]
    notes = json.loads(Path(args.notes).read_text()) if args.notes else None
    if notes and (notes.get("date") != args.date or notes.get("teamId") != args.team or notes.get("season") != args.season or notes.get("leagueId") != league_id):
        raise RuntimeError("Research notes do not match this report's date, league, season and team")
    (output / "packet.json").write_text(json.dumps(packet, indent=2))
    (output / "report.html").write_text(render(packet, notes))
    (output / "research_queries.txt").write_text("Fresh ESPN and Reddit review required; do not reuse old consensus.\n\n" + "\n".join(f'site:reddit.com/r/fantasybball "{p["name"]}" {args.date[:7]}\nsite:espn.com "{p["name"]}" injury rotation {args.date}' for p in [*drops, *candidates[:10]]))
    print(json.dumps({"output": str(output), "roster": len(roster), "available": len(available), "sources": len(c.sources), "topScenarios": scenarios[:6]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True, help="ESPN season ending year (2027 = 2026–27)")
    parser.add_argument("--team", type=int, default=2)
    parser.add_argument("--league", type=int)
    parser.add_argument("--date", default=datetime.now(PACIFIC).date().isoformat())
    parser.add_argument("--slate-date", help="NBA games to review; independent of the live roster date, useful after midnight")
    parser.add_argument("--start-date", help="Planning start; defaults to the first effective transaction date or today")
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--dashboard", default="http://127.0.0.1:3030")
    parser.add_argument("--limit", type=int, default=35)
    parser.add_argument("--days", type=int, choices=range(7, 29), default=14, help="Planning horizon, 7–28 days; default 14")
    parser.add_argument("--compare-drop", type=int, default=5105550, help="Player ID highlighted in the week-by-week table; no transaction is made")
    parser.add_argument("--watch", type=int, nargs="*", default=[])
    parser.add_argument("--output")
    parser.add_argument("--notes", help="Date/league/team/season-scoped JSON research conclusions")
    args = parser.parse_args()
    try:
        collect(args)
    except (RuntimeError, KeyError, StopIteration, ValueError) as exc:
        raise SystemExit(f"Report failed: {exc}") from None


if __name__ == "__main__":
    main()
