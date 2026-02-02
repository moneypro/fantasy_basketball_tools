"""
ESPN API Caching Layer

Provides TTL-based caching for ESPN API calls to reduce API load and improve response times.
"""

import threading
from typing import Any, Dict, List, Optional, Tuple
from cachetools import TTLCache
from functools import wraps

# Cache configurations (maxsize, ttl_seconds)
CACHE_CONFIG = {
    'scoreboard': (50, 300),      # 50 entries, 5 min TTL
    'box_scores': (100, 120),     # 100 entries, 2 min TTL (more dynamic)
    'free_agents': (10, 600),     # 10 entries, 10 min TTL
    'pro_schedule': (200, 3600),  # 200 entries, 1 hour TTL (rarely changes)
    'lineup': (100, 180),         # 100 entries, 3 min TTL
}

# Thread-safe caches
_caches: Dict[str, TTLCache] = {}
_locks: Dict[str, threading.Lock] = {}

def _get_cache(name: str) -> Tuple[TTLCache, threading.Lock]:
    """Get or create a cache and its lock."""
    if name not in _caches:
        maxsize, ttl = CACHE_CONFIG.get(name, (100, 300))
        _caches[name] = TTLCache(maxsize=maxsize, ttl=ttl)
        _locks[name] = threading.Lock()
    return _caches[name], _locks[name]


def cached_scoreboard(league, week_index: int) -> List[Any]:
    """Cached wrapper for league.scoreboard()."""
    cache, lock = _get_cache('scoreboard')
    key = f"scoreboard_{week_index}"

    with lock:
        if key in cache:
            return cache[key]

    # Fetch outside lock to avoid blocking
    result = league.scoreboard(week_index)

    with lock:
        cache[key] = result

    return result


def cached_box_scores(league, week_index: int, scoring_period: int, matchup_total: bool = True) -> List[Any]:
    """Cached wrapper for league.box_scores()."""
    cache, lock = _get_cache('box_scores')
    key = f"box_scores_{week_index}_{scoring_period}_{matchup_total}"

    with lock:
        if key in cache:
            return cache[key]

    result = league.box_scores(week_index, scoring_period, matchup_total=matchup_total)

    with lock:
        cache[key] = result

    return result


def cached_free_agents(league, size: int = 1000) -> List[Any]:
    """Cached wrapper for league.free_agents()."""
    cache, lock = _get_cache('free_agents')
    key = f"free_agents_{size}"

    with lock:
        if key in cache:
            return cache[key]

    result = league.free_agents(size=size)

    with lock:
        cache[key] = result

    return result


def cached_pro_schedule(league, scoring_period: int) -> Dict[int, Any]:
    """Cached wrapper for league._get_pro_schedule()."""
    cache, lock = _get_cache('pro_schedule')
    key = f"pro_schedule_{scoring_period}"

    with lock:
        if key in cache:
            return cache[key]

    result = league._get_pro_schedule(scoring_period)

    with lock:
        cache[key] = result

    return result


def invalidate_cache(cache_name: Optional[str] = None) -> None:
    """Invalidate a specific cache or all caches.

    Args:
        cache_name: Name of cache to invalidate, or None for all caches
    """
    if cache_name:
        if cache_name in _caches:
            with _locks[cache_name]:
                _caches[cache_name].clear()
    else:
        for name in list(_caches.keys()):
            with _locks[name]:
                _caches[name].clear()


def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics about all caches."""
    stats = {}
    for name, cache in _caches.items():
        with _locks[name]:
            maxsize, ttl = CACHE_CONFIG.get(name, (100, 300))
            stats[name] = {
                'current_size': len(cache),
                'max_size': maxsize,
                'ttl_seconds': ttl,
            }
    return stats
