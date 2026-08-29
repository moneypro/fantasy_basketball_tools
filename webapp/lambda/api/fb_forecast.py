"""Weekly forecast, expressed as JSON instead of the repo's HTML tables.

All of the *math* comes straight from the existing pipeline:

* ``common.week.Week``                             -> which pro teams play each day
* ``predict.internal.roster_week_predictor``       -> per-player mean/variance,
  the "top 9 scorers per day" selection, the week total and the game count.

What is re-implemented here is only the *aggregation* layer that
``predict/predict_week.py`` performs, because that module renders through
``tabulate`` (an extra dependency we do not want in the Lambda bundle) and emits
display strings such as ``"1234 ± 56"`` keyed by team NAME.  The contract needs
raw numbers keyed by team ID, so the loops below mirror
``PredictWeekHelper.predict_week`` and ``get_remaining_days_cumulative_scores``
one for one while keeping every actual calculation inside ``RosterWeekPredictor``.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from common.week import Week
from predict.internal.roster_week_predictor import RosterWeekPredictor

try:  # config.py is copied to the bundle root by build-lambda.sh
    from config import FANTASY_POINTS_WEIGHTS
except Exception:  # pragma: no cover - keep the Lambda alive if config is absent
    FANTASY_POINTS_WEIGHTS = {
        "PTS": 1.0,
        "3PTM": 1.0,
        "FGA": -1.0,
        "FGM": 2.0,
        "FTA": -1.0,
        "FTM": 1.0,
        "REB": 1.0,
        "AST": 2.0,
        "STL": 4.0,
        "BLK": 4.0,
        "TO": -2.0,
    }


def _safe_fantasy_pts(stats: Dict[str, Any]) -> float:
    """Drop-in replacement for ``RosterWeekPredictor.get_fantasy_pts``.

    The repo version indexes ``stats['AST']``/``['STL']``/``['TO']``/etc. directly
    while only ``PTS``/``3PTM``/``BLK`` go through the ``.get(cat, 0)`` helper.
    ESPN omits categories a player is projected at zero for, so e.g. Leonard
    Miller's ``2026_projected`` split has no ``AST`` key and the real predictor
    raises ``KeyError: 'AST'`` -- which would 500 every forecast request.

    Treating a missing category as 0 is exactly what ``get_stat_in_category``
    already does for the three categories it covers, so this changes no number
    that the repo can currently compute; it only stops the crash.  The weights
    come from ``config.FANTASY_POINTS_WEIGHTS``, which already matches the
    hard-coded formula in ``get_fantasy_pts``.
    """
    total = 0.0
    for category, weight in FANTASY_POINTS_WEIGHTS.items():
        total += float(stats.get(category, 0) or 0) * float(weight)
    return total


# Applied at import time: everything downstream (RosterWeekPredictor.predict,
# get_total_number_of_games, get_avg_variance_stats) keeps using the repo's own
# logic, with only this one leaf function made defensive.  The repo source is
# left untouched.
RosterWeekPredictor.get_fantasy_pts = staticmethod(_safe_fantasy_pts)

_LOG = logging.getLogger(__name__)
#: Accessing a staticmethod off the class yields the plain function on py3.10+,
#: but unwrap defensively so this works on older runtimes too.
_original_avg_variance = getattr(
    RosterWeekPredictor.get_avg_variance_stats,
    "__func__",
    RosterWeekPredictor.get_avg_variance_stats,
)


def _safe_avg_variance(player: Any) -> Tuple[float, float]:
    """Defence in depth: one malformed ESPN stat split must not 500 the site."""
    try:
        return _original_avg_variance(player)
    except Exception:  # pragma: no cover - defensive
        _LOG.warning(
            "Could not score player %s; treating as 0",
            getattr(player, "name", "?"),
            exc_info=True,
        )
        return 0.0, 0.0


RosterWeekPredictor.get_avg_variance_stats = staticmethod(_safe_avg_variance)


#: Mirrors ``PredictWeekHelper.DAYS_OF_WEEK``.
DAYS_OF_WEEK = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

#: ``predict/predict_week.py`` calls ``predict(daily_active_size=9, ...)`` and
#: ``get_remaining_days_cumulative_scores`` hard-codes the same 9.
DAILY_ACTIVE_SIZE = 9

ACTIVE_ONLY = ["ACTIVE"]
ACTIVE_PLUS_DTD = ["ACTIVE", "DAY_TO_DAY"]

FORECAST_TTL_SECONDS = 300

_forecast_cache: Dict[int, Tuple[float, Dict[str, Any]]] = {}
_forecast_lock = threading.Lock()


def _round(value: float, digits: int = 2) -> float:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


def _injury_status(player: Any) -> str:
    return getattr(player, "injuryStatus", "ACTIVE") or "ACTIVE"


def _daily_mean_variance(
    predictor: RosterWeekPredictor, num_days: int, injury_statuses: List[str]
) -> List[Tuple[float, float]]:
    """Per-day (mean, variance) for the top ``DAILY_ACTIVE_SIZE`` eligible players.

    Same selection rule as ``RosterWeekPredictor.predict`` /
    ``get_remaining_days_cumulative_scores``: filter by injury status, score every
    player through ``get_avg_variance_stats``, sort by mean descending, keep 9.
    """
    daily: List[Tuple[float, float]] = []
    for day in range(num_days):
        eligible = [
            player
            for player in predictor.players_with_game(day)
            if _injury_status(player) in injury_statuses
        ]
        stats = [predictor.get_avg_variance_stats(player) for player in eligible]
        stats.sort(reverse=True, key=lambda pair: pair[0])
        top = stats[:DAILY_ACTIVE_SIZE]
        daily.append((sum(avg for avg, _ in top), sum(var for _, var in top)))
    return daily


def _remaining_days(daily: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
    """Cumulative "this day through the end of the week" mean/stdDev.

    Variance of independent days adds, so the cumulative std dev is the square
    root of the summed variances -- identical to
    ``predict.predict_week.get_remaining_days_cumulative_scores``.
    """
    out: List[Dict[str, Any]] = []
    for start in range(len(daily)):
        mean = sum(day[0] for day in daily[start:])
        variance = sum(day[1] for day in daily[start:])
        out.append(
            {
                # ``% 7`` guards week 1, which spans 8 scoring periods (0..7) in
                # ``Week._match_up_week_to_scoring_period_convert``.
                "day": DAYS_OF_WEEK[start % len(DAYS_OF_WEEK)],
                "mean": _round(mean),
                "stdDev": _round(math.sqrt(variance)),
            }
        )
    return out


def build_forecast(league: Any, week_index: int) -> Dict[str, Any]:
    """Build the ``/api/forecast`` payload for one week (read-only)."""
    week = Week(league, week_index)
    num_days = week.scoring_period[1] - week.scoring_period[0] + 1

    teams: List[Dict[str, Any]] = []
    for team in league.teams:
        predictor = RosterWeekPredictor(team.roster, week)

        mean, std_dev = predictor.predict(
            daily_active_size=DAILY_ACTIVE_SIZE,
            starting_day=0,
            injuryStatusList=ACTIVE_ONLY,
        )
        mean_dtd, std_dev_dtd = predictor.predict(
            daily_active_size=DAILY_ACTIVE_SIZE,
            starting_day=0,
            injuryStatusList=ACTIVE_PLUS_DTD,
        )
        games = predictor.get_total_number_of_games(
            daily_active_size=DAILY_ACTIVE_SIZE,
            starting_day=0,
            injuryStatusList=ACTIVE_ONLY,
        )

        day_to_day = [
            player.name
            for player in team.roster
            if _injury_status(player) == "DAY_TO_DAY"
        ]
        out = [
            player.name for player in team.roster if _injury_status(player) == "OUT"
        ]

        teams.append(
            {
                "teamId": int(team.team_id),
                "teamName": team.team_name,
                "games": int(games),
                "mean": _round(mean),
                "stdDev": _round(std_dev),
                "meanWithDtd": _round(mean_dtd),
                "stdDevWithDtd": _round(std_dev_dtd),
                "injuries": {"dayToDay": day_to_day, "out": out},
                "remainingDays": _remaining_days(
                    _daily_mean_variance(predictor, num_days, ACTIVE_ONLY)
                ),
            }
        )

    teams.sort(key=lambda entry: entry["mean"], reverse=True)

    return {
        "week": int(week_index),
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "teams": teams,
    }


def get_forecast(league: Any, week_index: int) -> Dict[str, Any]:
    """``build_forecast`` with a short-lived module-global cache.

    ``/api/scoreboard`` reuses the forecast means when ESPN has no live
    projection (i.e. any completed week), so caching keeps the two endpoints from
    recomputing the same numbers on every request.
    """
    now = time.time()
    cached = _forecast_cache.get(week_index)
    if cached and (now - cached[0]) < FORECAST_TTL_SECONDS:
        return cached[1]

    with _forecast_lock:
        cached = _forecast_cache.get(week_index)
        if cached and (time.time() - cached[0]) < FORECAST_TTL_SECONDS:
            return cached[1]
        payload = build_forecast(league, week_index)
        _forecast_cache[week_index] = (time.time(), payload)
        return payload


def forecast_means_by_team_id(league: Any, week_index: int) -> Dict[int, float]:
    """``{team_id: active-only projected mean}`` for the given week."""
    forecast = get_forecast(league, week_index)
    return {entry["teamId"]: entry["mean"] for entry in forecast["teams"]}


def safe_forecast_means_by_team_id(
    league: Any, week_index: int
) -> Optional[Dict[int, float]]:
    """Like ``forecast_means_by_team_id`` but never raises (scoreboard fallback)."""
    try:
        return forecast_means_by_team_id(league, week_index)
    except Exception:  # pragma: no cover - defensive
        return None
