"""League/credential access for the public read-only fantasy basketball API.

Responsibilities
----------------
* Redirect anything that wants a writable HOME / cache dir to /tmp when we are
  running inside Lambda (the Lambda filesystem is read-only except /tmp).
* Load ESPN credentials from AWS Secrets Manager (``ESPN_SECRET_NAME``) with a
  fallback to plain ``ESPN_S2`` / ``SWID`` / ``LEAGUE_ID`` env vars so the same
  code can be exercised locally.
* Build the ``espn_api`` ``League`` object once and keep it in a module global
  so warm invocations do not re-fetch the whole league.

This module is READ-ONLY: it never mutates anything on the ESPN side.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

LOG = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Read-only filesystem guard (must run before repo modules are imported)
# --------------------------------------------------------------------------- #


def running_in_lambda() -> bool:
    return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def configure_writable_paths() -> None:
    """Point every "write a cache somewhere" convention at /tmp.

    ``utils/create_league.py`` does ``os.makedirs(os.path.expanduser("~/.fantasy_league_cache"))``
    at call time; ``os.path.expanduser`` honours ``$HOME``.  In Lambda ``$HOME``
    is ``/home/sbx_userNNNN`` on a read-only mount, so that ``makedirs`` raises
    ``OSError: [Errno 30] Read-only file system``.  Forcing HOME=/tmp makes any
    such helper land in the one writable directory we have.

    ``utils/espn_cache.py`` is purely in-memory (cachetools TTLCache) so it needs
    no redirection, but we set the usual cache env vars anyway for good measure.
    """
    if not running_in_lambda():
        return
    os.environ["HOME"] = "/tmp"
    os.environ.setdefault("XDG_CACHE_HOME", "/tmp/.cache")
    os.environ.setdefault("PYTHONPYCACHEPREFIX", "/tmp/.pycache")
    for path in ("/tmp/.cache", "/tmp/.pycache"):
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:  # pragma: no cover - defensive only
            pass


configure_writable_paths()

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

#: The 2025-26 season this repo targets (config.py / predict/* use 2026 stat keys).
SEASON_YEAR = int(os.environ.get("SEASON_YEAR", "2026"))

#: Fantasy weeks are 1..23 for this league (matches the validation in app.py and
#: the league's own ``matchup_ids`` keys).
MIN_WEEK = 1
MAX_WEEK = 23

#: How long a cached League object stays usable before we rebuild it.
LEAGUE_TTL_SECONDS = int(os.environ.get("LEAGUE_TTL_SECONDS", "900"))

# --------------------------------------------------------------------------- #
# Secrets
# --------------------------------------------------------------------------- #

_secret_cache: Optional[Dict[str, str]] = None
_secret_lock = threading.Lock()


def _load_secret_from_secrets_manager(secret_name: str) -> Dict[str, str]:
    # boto3 ships with the Lambda runtime; it is deliberately NOT in requirements.txt.
    import json

    import boto3  # type: ignore

    region = (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-west-2"
    )
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    raw = response.get("SecretString")
    if raw is None:  # binary secret
        import base64

        raw = base64.b64decode(response["SecretBinary"]).decode("utf-8")
    data = json.loads(raw)
    return {str(k): str(v) for k, v in data.items()}


def get_espn_credentials() -> Dict[str, str]:
    """Return ``{"ESPN_S2":..., "SWID":..., "LEAGUE_ID":...}``.

    Secrets Manager first (``ESPN_SECRET_NAME``), plain env vars otherwise.
    Cached in a module global so warm invocations skip the API call.
    """
    global _secret_cache
    if _secret_cache is not None:
        return _secret_cache

    with _secret_lock:
        if _secret_cache is not None:
            return _secret_cache

        secret_name = os.environ.get("ESPN_SECRET_NAME")
        creds: Dict[str, str] = {}
        if secret_name:
            LOG.info("Loading ESPN credentials from Secrets Manager: %s", secret_name)
            creds = _load_secret_from_secrets_manager(secret_name)
        else:
            LOG.info("ESPN_SECRET_NAME unset; falling back to environment variables")

        # Env vars fill any gap (and are the whole story for local testing).
        for key in ("ESPN_S2", "SWID", "LEAGUE_ID"):
            if not creds.get(key) and os.environ.get(key):
                creds[key] = os.environ[key]

        missing = [k for k in ("ESPN_S2", "SWID", "LEAGUE_ID") if not creds.get(k)]
        if missing:
            raise RuntimeError(
                "Missing ESPN credentials: %s (set ESPN_SECRET_NAME or "
                "ESPN_S2/SWID/LEAGUE_ID)" % ", ".join(missing)
            )

        _secret_cache = creds
        return _secret_cache


# --------------------------------------------------------------------------- #
# League
# --------------------------------------------------------------------------- #

_league_cache: Optional[Tuple[float, Any]] = None
_league_lock = threading.Lock()


def _build_league() -> Any:
    from espn_api.basketball import League  # imported lazily so health stays cheap

    creds = get_espn_credentials()
    started = time.time()
    league = League(
        league_id=int(creds["LEAGUE_ID"]),
        year=SEASON_YEAR,
        espn_s2=creds["ESPN_S2"],
        swid=creds["SWID"],
    )
    LOG.info(
        "Built League(%s, %s) with %d teams in %.2fs",
        creds["LEAGUE_ID"],
        SEASON_YEAR,
        len(league.teams),
        time.time() - started,
    )
    return league


def get_league(force_refresh: bool = False) -> Any:
    """Return a cached ``League``, rebuilding it after ``LEAGUE_TTL_SECONDS``."""
    global _league_cache
    now = time.time()
    cached = _league_cache
    if not force_refresh and cached is not None and (now - cached[0]) < LEAGUE_TTL_SECONDS:
        return cached[1]

    with _league_lock:
        cached = _league_cache
        if not force_refresh and cached is not None and (time.time() - cached[0]) < LEAGUE_TTL_SECONDS:
            return cached[1]
        league = _build_league()
        _league_cache = (time.time(), league)
        return league


# --------------------------------------------------------------------------- #
# Week helpers
# --------------------------------------------------------------------------- #


def season_complete(league: Any) -> bool:
    """True once the regular/playoff schedule has run out.

    ``base_league`` clamps ``current_week`` to ``finalScoringPeriod``, so the raw
    ``scoringPeriodId`` running past ``finalScoringPeriod`` is the reliable
    "the season is over" signal.  We also treat a matchup period beyond
    ``MAX_WEEK`` as complete.
    """
    scoring_period = getattr(league, "scoringPeriodId", 0) or 0
    final_period = getattr(league, "finalScoringPeriod", 0) or 0
    matchup_period = getattr(league, "currentMatchupPeriod", 0) or 0
    return bool(
        (final_period and scoring_period > final_period) or matchup_period > MAX_WEEK
    )


def clamp_week(week: int) -> int:
    return max(MIN_WEEK, min(MAX_WEEK, int(week)))


def current_week(league: Any) -> int:
    """The week the site should show by default, always inside 1..MAX_WEEK.

    Today (offseason) ESPN reports ``currentMatchupPeriod`` at/past the end of the
    season; clamping yields the last completed week, which is what we want to
    render rather than an error or an empty page.
    """
    raw = getattr(league, "currentMatchupPeriod", None) or MAX_WEEK
    return clamp_week(raw)


def current_scoring_period(league: Any) -> int:
    """Scoring period id, clamped to the season's final period."""
    scoring_period = getattr(league, "scoringPeriodId", 0) or 0
    final_period = getattr(league, "finalScoringPeriod", 0) or 0
    if final_period and scoring_period > final_period:
        return int(final_period)
    return int(scoring_period)
