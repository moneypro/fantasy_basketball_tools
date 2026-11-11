"""Report a player's rotation and upcoming matchups in a live ESPN points league.

python3 tools/streaming_profile.py --season 2027 4278585 4592829 4431893
Player arguments are ESPN IDs. By default, the schedule ends on Sunday (Pacific).
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
from pathlib import Path
from statistics import mean
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pickup_report import Collector, PACIFIC, ROOT, STAT_IDS, box_points, config

SITE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
FANTASY = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons"
POSITIONS = {1: "pg", 2: "sg", 3: "sf", 4: "pf", 5: "c"}


def tip(game):
    return datetime.fromtimestamp(game["date"] / 1000, PACIFIC)


def opponent(game, team):
    if team == game["homeProTeamId"]:
        return game["awayProTeamId"]
    if team == game["awayProTeamId"]:
        return game["homeProTeamId"]
    raise ValueError(f"Team {team} missing from game {game['id']}")


def minutes(value):
    whole, separator, seconds = str(value).partition(":")
    return float(whole) + (int(seconds) / 60 if separator else 0)


def parse_box(data, weights):
    comp = data["header"]["competitions"][0]
    if not comp["status"]["type"]["completed"] or data["header"]["season"]["type"] != 2:
        raise ValueError("Expected a completed regular-season game")
    scores = {int(side["team"]["id"]): int(side["score"]) for side in comp["competitors"]}
    sides = {}
    for team in data["boxscore"]["teams"]:
        tid = int(team["team"]["id"])
        stats = {s["name"]: s["displayValue"] for s in team["statistics"]}
        fga = int(stats["fieldGoalsMade-fieldGoalsAttempted"].split("-")[1])
        fta = int(stats["freeThrowsMade-freeThrowsAttempted"].split("-")[1])
        possessions = fga + .44 * fta - int(stats["offensiveRebounds"]) + int(stats["totalTurnovers"])
        sides[tid] = dict(points=scores[tid], possessions=possessions, players={}, dnps=set())
    for team in data["boxscore"]["players"]:
        tid = int(team["team"]["id"])
        players = sides[tid]["players"]
        for tab in team["statistics"]:
            for row in tab["athletes"]:
                if row.get("didNotPlay"):
                    sides[tid]["dnps"].add(int(row["athlete"]["id"]))
                    continue
                athlete = row["athlete"]
                pid = int(athlete["id"])
                stats = dict(zip(tab["labels"], row["stats"]))
                fp = box_points(stats, weights)
                if fp is None or pid in players:
                    raise ValueError(f"Incomplete or duplicate box line for {athlete['displayName']}")
                players[pid] = dict(name=athlete["displayName"], label=athlete["shortName"],
                                    min=minutes(stats["MIN"]), fp=fp, pts=int(stats["PTS"]),
                                    position=(athlete.get("position") or {}).get("abbreviation"),
                                    start=int(row["starter"]))
    for tid, side in sides.items():
        rows = side["players"].values()
        if not rows or sum(r["pts"] for r in rows) != scores[tid]:
            raise ValueError(f"Player points do not reconcile for team {tid}")
        side["fp"] = sum(r["fp"] for r in rows)
    if len(sides) != 2:
        raise ValueError("Expected two team boxes")
    return sides


def league_history(teams, now, get, weights):
    recent, upcoming = {}, {}
    for tid, team in teams.items():
        games = {g["id"]: g for group in team.get("proGamesByScoringPeriod", {}).values()
                 for g in group if not (g.get("canceled") or g.get("postponed"))}
        ordered = sorted(games.values(), key=tip)
        recent[tid] = [g for g in ordered if tip(g) <= now and
                       str(g.get("detail", "")).lower().startswith("final")][-5:]
        upcoming[tid] = [g for g in ordered if tip(g) > now and not g.get("inProgress")]
    ids = {g["id"] for games in recent.values() for g in games}

    def fetch(eid):
        try:
            return eid, parse_box(get(f"box {eid}", f"{SITE}/summary?event={eid}"), weights)
        except (ValueError, KeyError) as exc:
            raise ValueError(f"Box {eid}: {exc}") from exc

    with ThreadPoolExecutor(max_workers=6) as pool:
        boxes = dict(pool.map(fetch, sorted(ids)))
    return recent, upcoming, boxes


def defensive_metrics(recent, boxes):
    metrics = {}
    for tid, games in recent.items():
        if not games:
            continue
        allowed, points, possessions = [], 0, 0
        for game in games:
            sides = boxes[game["id"]]
            other = sides[opponent(game, tid)]
            points += other["points"]
            possessions += (other["possessions"] + sides[tid]["possessions"]) / 2
            allowed.append(other["fp"])
        metrics[tid] = dict(rating=100 * points / possessions, allowed=mean(allowed),
                            game_totals=allowed, games=len(games))
    for stat in ("rating", "allowed"):
        for row in metrics.values():
            row[stat + "_rank"] = 1 + sum(other[stat] < row[stat] for other in metrics.values())
    return metrics


def nba_ratings(teams, recent, season, now):
    """Use official NBA figures only if the entire ranked field matches the sample sizes."""
    params = dict(LeagueID="00", Season=f"{season-1}-{str(season)[-2:]}", SeasonType="Regular Season",
                  LastNGames=5, MeasureType="Advanced", PerMode="Totals", DateTo=now.strftime("%m/%d/%Y"),
                  DateFrom="", Month=0, OpponentTeamID=0, Period=0, TeamID=0, PORound=0,
                  PaceAdjust="N", PlusMinus="N", Rank="N", Location="", Outcome="", SeasonSegment="",
                  GameSegment="", GameScope="", PlayerExperience="", PlayerPosition="", StarterBench="",
                  VsConference="", VsDivision="", Conference="", Division="", ShotClockRange="")
    url = "https://stats.nba.com/stats/leaguedashteamstats?" + urlencode(params)
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.nba.com/",
                                    "Origin": "https://www.nba.com", "x-nba-stats-token": "true"})
    by_name = {f"{t['location']} {t['name']}": tid for tid, t in teams.items()}
    try:
        with urlopen(request, timeout=5) as response:
            tables = json.load(response)["resultSets"]
        result = next(tab for tab in tables if tab["name"] == "LeagueDashTeamStats")
        ratings = {}
        for values in result["rowSet"]:
            row = dict(zip(result["headers"], values))
            tid = by_name[row["TEAM_NAME"]]
            if row["GP"] != len(recent[tid]):
                return {}
            ratings[tid] = (float(row["DEF_RATING"]), int(row["DEF_RATING_RANK"]))
        if ratings.keys() == {tid for tid, games in recent.items() if games}:
            return ratings
    except (OSError, ValueError, TypeError, KeyError, StopIteration):
        pass
    return {}


def table(headers, rows):
    return ["| " + " | ".join(map(str, row)) + " |"
            for row in [headers, ["---"] * len(headers), *rows]]


def game_link(game, team, teams):
    where = "vs." if team == game["homeProTeamId"] else "@"
    label = f"{tip(game):%b %d} {where} {teams[opponent(game, team)]['abbrev']}"
    return f"[{label}](https://www.espn.com/nba/boxscore/_/gameId/{game['id']})"


def split_summary(group):
    if not group:
        return "—"
    mins, points = zip(*group)
    return f"{len(group)}g · {mean(mins):.1f} MIN · {mean(points):.1f} FP"


def teammate_context(team_boxes, pid, roster, peers, news, dates):
    """Condition the candidate's actual game lines on each current teammate's appearances."""
    lines = ["", "### Teammate availability and return risk", ""]
    if roster is None:
        return lines + ["Current team roster and injury status unavailable. Return risk could not be checked."]
    rows, reports = [], []
    for a in roster:
        teammate = int(a["id"])
        if teammate == pid:
            continue
        played = [teammate in side["players"] for side in team_boxes]
        injuries = a.get("injuries") or []
        if not injuries and (all(played) or (not any(played) and teammate not in peers)):
            continue
        samples = {True: [], False: []}
        for side, appeared in zip(team_boxes, played):
            if pid in side["players"]:
                target = side["players"][pid]
                samples[appeared].append((target["min"], target["fp"]))
            elif pid in side["dnps"]:
                samples[appeared].append((0, 0))
        # Current membership does not establish why a teammate missed a prior game.
        timeline = [f"{side['players'][teammate]['min']:g}" if present else
                    ("DNP" if teammate in side["dnps"] else "—")
                    for side, present in zip(team_boxes, played)]
        flags = ", ".join(dict.fromkeys(i.get("status") or "unknown" for i in injuries))
        label = a["shortName"]
        rows.append([label, ", ".join(peers.get(teammate, [])) or "other rotation",
                     flags or "No flag", " / ".join(timeline), split_summary(samples[True]), split_summary(samples[False])])
        update = news.get(teammate) or {}
        item = max(injuries, key=lambda i: i.get("date") or "", default={})
        if item.get("date"):
            reports.append(f"- {label} · roster lists {item.get('status', 'unknown')} as of {item['date']}.")
        if update.get("headline"):
            reports.append(f"- {label} · {update.get('published') or 'date unavailable'} · "
                           f"{update['headline']} [ESPN player update](https://www.espn.com/nba/player/_/id/{teammate})")
        elif injuries or teammate in peers:
            reports.append(f"- {label} · Dated player update unavailable.")
    if not rows:
        return lines + ["No current injury flags or changes in teammate participation found in this sample."]
    lines += ["Teammate minutes, oldest first: " + ", ".join(dates) + ". DNP is explicit; — means no box line. "
              "Splits count the candidate’s recorded games (including explicit DNPs as zero). "
              "They show association only. A missed game alone does not establish an injury.", ""]
    lines += table(["Teammate", "Shared depth slots", "ESPN roster status", "Teammate MIN",
                    "Candidate when teammate played", "Candidate when teammate did not appear"], rows)
    if reports:
        lines += ["", "Dated reports (check the game named in each update):", "", *reports]
    return lines


def team_availability(get, targets, season, recent, boxes):
    rosters, news_ids = {}, set()
    for tid in targets:
        data = get("team roster", f"{SITE}/teams/{tid}/roster", optional=True) or {}
        roster = data.get("athletes") if data.get("season", {}).get("year") == season else None
        rosters[tid] = roster or None
        for athlete in roster or []:
            pid = int(athlete["id"])
            played = [pid in boxes[g["id"]][tid]["players"] for g in recent[tid]]
            if athlete.get("injuries") or not all(played):
                news_ids.add(pid)

    def fetch(pid):
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{pid}/overview"
        return pid, (get("teammate update", url, optional=True) or {}).get("rotowire")

    with ThreadPoolExecutor(max_workers=6) as pool:
        return rosters, dict(pool.map(fetch, sorted(news_ids)))


def profile(entry, teams, recent, upcoming, boxes, defenses, depth, end, rating_label, roster, news):
    player = entry["player"]
    tid, pid = player["proTeamId"], player["id"]
    games = recent[tid]
    n = len(games)
    abbr = teams[tid]["abbrev"]
    name = player["fullName"]
    lines = [f"## {name} · {abbr}", "",
             f"ESPN ID {pid} · {entry['status']} · {player.get('injuryStatus', 'unknown')}.",
             "", "### Play schedule and opponent defense", ""]
    rows = []
    opponents = []
    for game in upcoming[tid]:
        if tip(game).date() > end:
            break
        opp = opponent(game, tid)
        d = defenses.get(opp)
        venue = "vs." if tid == game["homeProTeamId"] else "@"
        time = tip(game).strftime("%a %b %d, %I:%M %p %Z")
        if game.get("startTimeTBD"):
            time = f"{tip(game):%a %b %d}, time TBD"
        rows.append([time, venue + " " + teams[opp]["abbrev"], d["games"] if d else 0,
                     f"{d['rating']:.1f} (#{d['rating_rank']})" if d else "—",
                     f"{d['allowed']:.1f} (#{d['allowed_rank']})" if d else "—"])
        if opp not in opponents:
            opponents.append(opp)
    lines += table(["Tip (Pacific)", "Opponent", "Sample", rating_label, "FP allowed/game"], rows)
    if not rows:
        lines += ["", "No remaining games in this window."]
    lines += ["", "### Team fantasy production and player game log", ""]
    by_player = defaultdict(list)
    game_rows = []
    for game in games:
        side = boxes[game["id"]][tid]
        for i, row in side["players"].items():
            by_player[i].append(row)
        own = side["players"].get(pid)
        game_rows.append([game_link(game, tid, teams), f"{side['fp']:.1f}",
                          f"{own['min']:g}" if own else "—", f"{own['fp']:.1f}" if own else "—"])
    lines += table(["Final game", f"{abbr} total FP", "Player MIN", "Player FP"], game_rows)
    if n:
        team_fp = sum(boxes[g["id"]][tid]["fp"] for g in games) / n
        lines += ["", f"Team average **{team_fp:.1f} FP/game** across {n} completed games."]
        if by_player.get(pid):
            player_fp = sum(r["fp"] for r in by_player[pid])
            if team_fp > 0:
                lines[-1] += f" {name} contributed {100 * player_fp / (team_fp * n):.1f}% of the team total."

    positions = (depth or {}).get("depthchart") or []
    chart = positions[0]["positions"] if positions else {}
    primary = POSITIONS.get(player.get("defaultPositionId"))
    shared = [pos for pos, group in chart.items()
              if any(int(a["id"]) == pid for a in group["athletes"])]
    if primary and primary not in shared:
        shared.insert(0, primary)
    peers = defaultdict(list)
    short_names = {}
    for pos in shared:
        for index, athlete in enumerate(chart.get(pos, {}).get("athletes", []), start=1):
            i = int(athlete["id"])
            peers[i].append(f"{pos.upper()}{index}")
            short_names[i] = athlete["shortName"]

    def averages(i):
        played = by_player.get(i, [])
        if not played:
            return ["0", "0", "—", "—"]
        return [len(played), sum(r["start"] for r in played),
                f"{mean(r['min'] for r in played):.1f}", f"{mean(r['fp'] for r in played):.1f}"]

    names = {i: rows[0]["label"] for i, rows in by_player.items()}
    names.update(short_names)
    surnames = Counter(short.split(". ", 1)[-1] for short in names.values())

    def label(i):
        short = names[i]
        last = short.split(". ", 1)[-1]
        return last if surnames[last] == 1 else short

    lines += ["", "### Rotation and contributors", "",
              "Minutes and FP are per appearance. GP and starts cover the same team games.", ""]
    rotation = sorted(by_player, key=lambda i: sum(r["min"] for r in by_player[i]), reverse=True)
    lines += table(["Player", "GP", "Starts", "MIN", "FP"], [[label(i), *averages(i)] for i in rotation])
    lines += ["", "### Same-position competition", ""]
    if peers:
        lines += ["ESPN depth-chart slots shared with the player. A player can appear at multiple positions.", ""]
        lines += table(["Player", "Depth", "GP", "Starts", "MIN", "FP"],
                       [[label(i), ", ".join(tags), *averages(i)] for i, tags in peers.items()])
    else:
        lines += ["ESPN depth-chart competitors unavailable."]
    lines += teammate_context([boxes[g["id"]][tid] for g in games], pid, roster, peers, news,
                              [tip(g).strftime("%b %d") for g in games])
    lines += ["", "### Opponent recap over the last five games", ""]
    group = {"pg": "G", "sg": "G", "sf": "F", "pf": "F", "c": "C"}.get(primary)
    if group:
        lines += [f"Position totals include every opposing player ESPN labeled {group} in the box score. "
                  "Bench totals cover reserves at that position. A dash indicates incomplete position data.", ""]
    for opp in opponents:
        rows = []
        for game in recent[opp]:
            sides = boxes[game["id"]]
            own, other = sides[opp], sides[opponent(game, opp)]
            result = "W" if own["points"] > other["points"] else "L"
            row = [game_link(game, opp, teams), f"{result} {own['points']}–{other['points']}", f"{other['fp']:g}"]
            if group:
                played = other["players"].values()
                if all(p["position"] for p in played):
                    matching = [p for p in played if p["position"] in
                                {"G": ("G", "PG", "SG"), "F": ("F", "SF", "PF"), "C": ("C",)}[group]]
                    row += [f"{sum(p['fp'] for p in matching):g}",
                            f"{sum(p['fp'] for p in matching if not p['start']):g}"]
                else:
                    row += ["—", "—"]
            rows.append(row)
        headers = ["Game", f"{teams[opp]['abbrev']} result", "Team FP allowed"]
        if group:
            headers += [f"{group} FP allowed", f"Bench {group} FP allowed"]
        lines += [f"**{teams[opp]['location']} {teams[opp]['name']}**", "", *table(headers, rows), ""]
    lines += ["", f"[ESPN depth chart]({SITE}/teams/{tid}/depthcharts)"]
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("player_ids", type=int, nargs="+", metavar="PLAYER_ID")
    parser.add_argument("--season", type=int, required=True, help="ESPN ending year")
    parser.add_argument("--league", type=int, help="Defaults to the league in .env")
    parser.add_argument("--days", type=int, help="Schedule horizon including today (default: through Sunday)")
    parser.add_argument("--output", type=Path, help="Markdown file (default: stdout)")
    args = parser.parse_args()
    if args.days is not None and args.days < 1:
        parser.error("--days must be positive")
    cfg = config(ROOT / ".env")
    league = args.league or int(cfg["LEAGUE_ID"])
    base = f"{FANTASY}/{args.season}/segments/0/leagues/{league}"
    auth = {"Cookie": f"espn_s2={cfg['ESPN_S2']}; SWID={cfg['SWID']}"}
    now = datetime.now(PACIFIC)
    days = args.days if args.days is not None else 7 - now.weekday()
    end = now.date() + timedelta(days=days - 1)
    get = Collector(None).get
    data = get("league", base + "?view=mSettings", auth)
    if data["seasonId"] != args.season or data["id"] != league:
        raise ValueError("League identity mismatch")
    scoring = data["settings"]["scoringSettings"]
    weights = {s["statId"]: s["points"] for s in scoring["scoringItems"]}
    if scoring["scoringType"] != "H2H_POINTS" or not weights or weights.keys() - set(STAT_IDS.values()):
        raise ValueError("League scoring cannot be reconstructed with the supported box stats")
    ids = list(dict.fromkeys(args.player_ids))
    filt = json.dumps({"players": {"filterIds": {"value": ids}}})
    entries = get("player pool", base + "?view=kona_player_info&scoringPeriodId=" + str(data["scoringPeriodId"]),
                  {**auth, "x-fantasy-filter": filt})["players"]
    entries = {p["id"]: p for p in entries}
    if set(ids) - entries.keys():
        raise ValueError(f"Unknown player IDs: {sorted(set(ids) - entries.keys())}")
    schedule = get("schedule", f"{FANTASY}/{args.season}?view=proTeamSchedules")
    teams = {t["id"]: t for t in schedule["settings"]["proTeams"] if t["id"] and t.get("proGamesByScoringPeriod")}
    targets = {entry["player"]["proTeamId"] for entry in entries.values()}
    if targets - teams.keys():
        raise ValueError("A selected player has no scheduled NBA team")
    recent, upcoming, boxes = league_history(teams, now, get, weights)
    defenses = defensive_metrics(recent, boxes)
    official = nba_ratings(teams, recent, args.season, now)
    if official:
        for tid, (rating, rank) in official.items():
            defenses[tid].update(rating=rating, rating_rank=rank)
        rating_label = "NBA DRtg"
        method = "[NBA Advanced Team Stats](https://www.nba.com/stats/teams/advanced?LastNGames=5) supplies points allowed per 100 possessions and the league rank."
    else:
        rating_label = "Est. DRtg"
        method = ("A matching NBA Stats table was unavailable. Estimated DRtg is points allowed per 100 possessions, weighted across games. "
                  "Possessions per game use the average of both teams’ FGA + 0.44 × FTA − OREB + total turnovers.")
    depths = {tid: get("depth chart", f"{SITE}/teams/{tid}/depthcharts", optional=True) for tid in targets}
    rosters, news = team_availability(get, targets, args.season, recent, boxes)
    lines = ["# Streaming comparison", "",
             f"{data['settings']['name']} · Season ending {args.season} · Retrieved {now:%b %d, %Y %I:%M %p %Z}.",
             f"Upcoming games through {end:%b %d}. Each sample uses the team's last five completed regular-season games, or all games available if fewer.",
             "", f"Defense ranks among {len(defenses)} teams with a completed game. #1 allows the fewest. {method} "
             "Fantasy totals sum individual player scores under the league settings, including overtime.", ""]
    for pid in ids:
        entry = entries[pid]
        depth = depths[entry["player"]["proTeamId"]]
        if depth and depth.get("season", {}).get("year") != args.season:
            depth = None
        lines += profile(entry, teams, recent, upcoming, boxes, defenses, depth, end, rating_label,
                         rosters[entry["player"]["proTeamId"]], news) + [""]
    report = "\n".join(lines)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        sys.exit(f"Report unavailable: {error}")
