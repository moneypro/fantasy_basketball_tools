"""AWS Lambda entry point for the public, READ-ONLY fantasy basketball API.

Routes (API Gateway HTTP API, payload format 2.0, ``ANY /api/{proxy+}``):

    GET /api/health              -> {"ok": true, "time": "<iso>"}
    GET /api/league              -> league metadata + standings
    GET /api/forecast?week=N     -> weekly point forecast per team
    GET /api/scoreboard?week=N   -> matchups with score + projection
    GET /api/roster?teamId=N     -> one team's roster

``week`` is optional everywhere (omitted = current week, clamped into 1..23).
There are deliberately NO write/mutation routes: anything that is not a GET on a
known path is rejected.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Bundle layout / read-only filesystem bootstrap.
#
# build-lambda.sh copies the repo packages (predict/, common/, utils/, config.py)
# to the bundle root and this package's files alongside them.  Adding our own
# directory to sys.path makes ``import fb_league`` work whether handler.py ends
# up at the bundle root (handler = "handler.lambda_handler") or inside an
# ``api/`` package (handler = "api.handler.lambda_handler").  It is APPENDED, not
# prepended, so repo modules always win a name clash.
# --------------------------------------------------------------------------- #
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.append(_HERE)

import fb_league  # noqa: E402  (must follow the sys.path fix)

fb_league.configure_writable_paths()  # HOME -> /tmp before any repo import

import fb_forecast  # noqa: E402

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

JSON_CONTENT_TYPE = "application/json"
DATA_CACHE_CONTROL = "public, max-age=60"


# --------------------------------------------------------------------------- #
# HTTP plumbing
# --------------------------------------------------------------------------- #


_warned_no_origins = False


def _allowed_origins() -> List[str]:
    global _warned_no_origins
    raw = os.environ.get("ALLOWED_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins and not _warned_no_origins:
        _warned_no_origins = True
        LOG.warning(
            "ALLOWED_ORIGINS is empty; no browser origin will be permitted by CORS"
        )
    return origins


def _cors_headers(event: Dict[str, Any]) -> Dict[str, str]:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    origin = headers.get("origin")
    allowed = _allowed_origins()

    cors: Dict[str, str] = {"Vary": "Origin"}
    if not origin:
        return cors
    if "*" in allowed:
        cors["Access-Control-Allow-Origin"] = origin
    elif origin in allowed:
        cors["Access-Control-Allow-Origin"] = origin
    else:
        # Not an allowed origin: send the body but no ACAO, so the browser blocks it.
        return cors

    cors["Access-Control-Allow-Methods"] = "GET,OPTIONS"
    cors["Access-Control-Allow-Headers"] = "Content-Type"
    cors["Access-Control-Max-Age"] = "600"
    return cors


def _respond(
    event: Dict[str, Any],
    status: int,
    body: Dict[str, Any],
    cache_control: str = DATA_CACHE_CONTROL,
) -> Dict[str, Any]:
    headers = {"Content-Type": JSON_CONTENT_TYPE, "Cache-Control": cache_control}
    headers.update(_cors_headers(event))
    return {
        "statusCode": status,
        "headers": headers,
        "body": json.dumps(body, default=str),
        "isBase64Encoded": False,
    }


# The vendored espn_api library builds its access-denied message out of the live
# cookies (espn_requests.py: "League N cannot be accessed with espn_s2=... and
# swid=..."). That message must never reach a caller or CloudWatch, so scrub any
# credential material out of a string before it leaves this module.
_CRED_PATTERN = re.compile(r"(espn_s2|swid)(\s*[=:]\s*)(\S+)", re.IGNORECASE)


def _redact(text: str) -> str:
    if not text:
        return text
    scrubbed = _CRED_PATTERN.sub(r"\1\2<redacted>", text)
    try:
        for key in ("ESPN_S2", "SWID"):
            value = fb_league.get_espn_credentials().get(key)
            if value and len(value) >= 8:
                scrubbed = scrubbed.replace(value, "<redacted>")
    except Exception:  # noqa: BLE001 - redaction must never raise
        pass
    return scrubbed


def _error(event: Dict[str, Any], status: int, message: str) -> Dict[str, Any]:
    return _respond(event, status, {"error": message}, cache_control="no-store")


class BadRequest(Exception):
    """Raised for anything the caller can fix -> HTTP 400."""


class NotFound(Exception):
    """Raised for unknown teams / paths -> HTTP 404."""


def _method(event: Dict[str, Any]) -> str:
    ctx_method = (
        (event.get("requestContext") or {}).get("http", {}).get("method")
    )
    return (ctx_method or event.get("httpMethod") or "GET").upper()


def _route(event: Dict[str, Any]) -> str:
    """Normalised route key, e.g. ``health`` for ``/api/health``."""
    proxy = (event.get("pathParameters") or {}).get("proxy")
    if proxy:
        return proxy.strip("/").lower()

    path = event.get("rawPath") or event.get("path") or "/"
    stage = (event.get("requestContext") or {}).get("stage")
    if stage and stage != "$default" and path.startswith("/" + stage + "/"):
        path = path[len(stage) + 1 :]
    path = path.strip("/")
    if path.startswith("api/"):
        path = path[len("api/") :]
    elif path == "api":
        path = ""
    return path.lower()


def _query(event: Dict[str, Any]) -> Dict[str, str]:
    params = event.get("queryStringParameters") or {}
    return {str(k): ("" if v is None else str(v)) for k, v in params.items()}


def _int_param(params: Dict[str, str], name: str) -> Optional[int]:
    raw = params.get(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        raise BadRequest("%s must be an integer" % name)


def _validated_week(params: Dict[str, str]) -> Optional[int]:
    """Validate ``?week=`` (1..23) without touching ESPN.

    Returns ``None`` when the caller omitted it, so bad input 400s instantly
    instead of paying for a league fetch first.
    """
    week = _int_param(params, "week")
    if week is None:
        return None
    if week < fb_league.MIN_WEEK or week > fb_league.MAX_WEEK:
        raise BadRequest(
            "week must be an integer between %d and %d"
            % (fb_league.MIN_WEEK, fb_league.MAX_WEEK)
        )
    return week


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _round(value: Any, digits: int = 2) -> float:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------- #
# Endpoint payloads
# --------------------------------------------------------------------------- #


def handle_health() -> Dict[str, Any]:
    # Deliberately does not touch ESPN so the health check stays fast and green
    # even if ESPN is down.
    return {"ok": True, "time": _now_iso()}


def handle_league() -> Dict[str, Any]:
    league = fb_league.get_league()
    teams = [
        {
            "teamId": int(team.team_id),
            "teamName": team.team_name,
            "abbrev": getattr(team, "team_abbrev", "") or "",
            "wins": int(getattr(team, "wins", 0) or 0),
            "losses": int(getattr(team, "losses", 0) or 0),
            "pointsFor": _round(getattr(team, "points_for", 0.0)),
            "pointsAgainst": _round(getattr(team, "points_against", 0.0)),
            "standing": int(getattr(team, "standing", 0) or 0),
        }
        for team in league.teams
    ]
    teams.sort(key=lambda entry: (entry["standing"] or 999, entry["teamId"]))

    return {
        "leagueName": getattr(league.settings, "name", "") or "",
        "season": int(getattr(league, "year", fb_league.SEASON_YEAR)),
        "currentWeek": fb_league.current_week(league),
        "currentScoringPeriod": fb_league.current_scoring_period(league),
        "seasonComplete": fb_league.season_complete(league),
        "teams": teams,
    }


def handle_forecast(params: Dict[str, str]) -> Dict[str, Any]:
    week = _validated_week(params)  # validate before any network work
    league = fb_league.get_league()
    return fb_forecast.get_forecast(
        league, week if week is not None else fb_league.current_week(league)
    )


def _team_name(team: Any) -> str:
    return getattr(team, "team_name", None) or "BYE"


def _team_id(team: Any) -> int:
    team_id = getattr(team, "team_id", None)
    if team_id is None and isinstance(team, int):
        team_id = team
    return int(team_id or 0)


def _espn_projections(league: Any, week: int) -> Dict[int, float]:
    """ESPN's own live projections, when the week has them (in-season only)."""
    from utils.espn_cache import cached_box_scores

    scoring_period: Optional[int] = None
    matchup_ids = getattr(league, "matchup_ids", {}) or {}
    periods = matchup_ids.get(week)
    if periods:
        try:
            scoring_period = int(periods[-1])
        except (TypeError, ValueError):
            scoring_period = None

    projections: Dict[int, float] = {}
    try:
        box_scores = cached_box_scores(league, week, scoring_period, True)
    except Exception:  # ESPN sometimes 404s box scores for old weeks
        LOG.warning("box_scores unavailable for week %s", week, exc_info=True)
        return projections

    for box in box_scores:
        for side in ("home", "away"):
            team = getattr(box, "%s_team" % side, None)
            projected = getattr(box, "%s_projected" % side, -1)
            team_id = _team_id(team)
            if team_id and projected is not None and float(projected) >= 0:
                projections[team_id] = _round(projected)
    return projections


def handle_scoreboard(params: Dict[str, str]) -> Dict[str, Any]:
    from utils.espn_cache import cached_scoreboard

    requested_week = _validated_week(params)  # validate before any network work
    league = fb_league.get_league()
    week = (
        requested_week
        if requested_week is not None
        else fb_league.current_week(league)
    )

    espn_projections = _espn_projections(league, week)
    forecast_means: Optional[Dict[int, float]] = None
    if not espn_projections:
        # No live ESPN projection (any completed week, and every week right now
        # in the offseason) -> fall back to our own forecast mean.
        forecast_means = fb_forecast.safe_forecast_means_by_team_id(league, week)

    def side(team: Any, score: Any) -> Dict[str, Any]:
        team_id = _team_id(team)
        projected = espn_projections.get(team_id)
        if projected is None and forecast_means is not None:
            projected = forecast_means.get(team_id)
        return {
            "teamId": team_id,
            "teamName": _team_name(team),
            "score": _round(score),
            "projected": _round(projected) if projected is not None else 0.0,
        }

    matchups = [
        {
            "home": side(matchup.home_team, matchup.home_final_score),
            "away": side(matchup.away_team, matchup.away_final_score),
        }
        for matchup in cached_scoreboard(league, week)
    ]

    return {"week": int(week), "matchups": matchups}


def handle_roster(params: Dict[str, str]) -> Dict[str, Any]:
    team_id = _int_param(params, "teamId")  # validate before any network work
    if team_id is None:
        raise BadRequest("teamId is required")

    league = fb_league.get_league()
    team = league.get_team_data(team_id)
    if team is None:
        raise NotFound("team %d not found" % team_id)

    players = [
        {
            "playerId": int(getattr(player, "playerId", 0) or 0),
            "name": getattr(player, "name", "") or "",
            "position": getattr(player, "position", "") or "",
            "lineupSlot": getattr(player, "lineupSlot", "") or "",
            "proTeam": getattr(player, "proTeam", "") or "",
            "injuryStatus": getattr(player, "injuryStatus", "ACTIVE") or "ACTIVE",
            "avgPoints": _round(getattr(player, "avg_points", 0.0)),
            "totalPoints": _round(getattr(player, "total_points", 0.0)),
        }
        for player in team.roster
    ]

    return {
        "teamId": int(team.team_id),
        "teamName": team.team_name,
        "players": players,
    }


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #

_ROUTES = {"health", "league", "forecast", "scoreboard", "roster"}


def _dispatch(route: str, params: Dict[str, str]) -> Tuple[int, Dict[str, Any]]:
    if route == "health":
        return 200, handle_health()
    if route == "league":
        return 200, handle_league()
    if route == "forecast":
        return 200, handle_forecast(params)
    if route == "scoreboard":
        return 200, handle_scoreboard(params)
    if route == "roster":
        return 200, handle_roster(params)
    raise NotFound("no such endpoint: /api/%s" % route)


def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    event = event or {}
    try:
        method = _method(event)
        route = _route(event)

        if method == "OPTIONS":
            headers = {"Content-Type": JSON_CONTENT_TYPE, "Cache-Control": "no-store"}
            headers.update(_cors_headers(event))
            return {
                "statusCode": 204,
                "headers": headers,
                "body": "",
                "isBase64Encoded": False,
            }

        if method not in ("GET", "HEAD"):
            # Read-only service: no POST/PUT/PATCH/DELETE routes exist at all.
            return _error(
                event, 405, "method %s not allowed; this API is read-only" % method
            )

        if route not in _ROUTES:
            return _error(event, 404, "no such endpoint: /api/%s" % route)

        status, body = _dispatch(route, _query(event))
        cache_control = "no-store" if route == "health" else DATA_CACHE_CONTROL
        return _respond(event, status, body, cache_control=cache_control)

    except BadRequest as exc:
        return _error(event, 400, str(exc))
    except NotFound as exc:
        return _error(event, 404, str(exc))
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        # Never put the exception text in the response: it can carry the
        # league's ESPN session cookie (see _redact) or internal AWS detail.
        # Callers get a fixed message plus a request id to quote; the detail
        # goes to CloudWatch, redacted.
        request_id = getattr(context, "aws_request_id", "-")
        LOG.error(
            "Unhandled %s (request %s): %s",
            type(exc).__name__,
            request_id,
            _redact(traceback.format_exc()),
        )
        return _error(event, 500, "internal error (request %s)" % request_id)


# Common alternate entry-point names, so the infra side can point at any of them.
handler = lambda_handler
main = lambda_handler
