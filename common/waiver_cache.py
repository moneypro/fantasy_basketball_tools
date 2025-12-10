"""Cache for waiver player IDs with daily refresh at 3AM PT."""

import json
import os
from pathlib import Path
from typing import Set
from datetime import datetime, time
import pytz

# Cache directory for waiver data
CACHE_DIR = Path(os.getenv('WAIVER_CACHE_DIR', './cache/waivers'))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_waiver_cache_file(league_id: int) -> Path:
    """Get the cache file path for a specific league.
    
    Args:
        league_id: ESPN league ID
        
    Returns:
        Path to the cache file
    """
    return CACHE_DIR / f"league_{league_id}_waivers.json"


def is_cache_expired(league_id: int) -> bool:
    """Check if waiver cache has expired (past 3AM PT).
    
    Cache is considered expired if:
    - File doesn't exist, OR
    - Current time is past 3AM PT today
    
    Args:
        league_id: ESPN league ID
        
    Returns:
        True if cache is expired and should be refreshed
    """
    cache_file = get_waiver_cache_file(league_id)
    
    if not cache_file.exists():
        return True
    
    # Check if we're past 3AM PT
    pt = pytz.timezone('US/Pacific')
    now = datetime.now(pt)
    refresh_time = now.replace(hour=3, minute=0, second=0, microsecond=0)
    
    # Get file modification time
    file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime, tz=pt)
    
    # If current time is after 3AM and file was modified before 3AM today, it's expired
    if now.time() >= time(3, 0):
        # We're past 3AM, check if file was modified before today's 3AM
        if file_mtime < refresh_time:
            return True
    else:
        # We're before 3AM, check if file was modified before yesterday's 3AM
        yesterday_refresh = refresh_time.replace(day=refresh_time.day - 1)
        if file_mtime < yesterday_refresh:
            return True
    
    return False


def load_waiver_ids_from_cache(league_id: int) -> Set[int]:
    """Load waiver player IDs from cache file if it exists and is fresh.
    
    Args:
        league_id: ESPN league ID
        
    Returns:
        Set of player IDs on waivers, or empty set if not cached or expired
    """
    if is_cache_expired(league_id):
        return set()
    
    cache_file = get_waiver_cache_file(league_id)
    
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
            return set(data.get('waiver_player_ids', []))
    except Exception as e:
        print(f"Error loading waiver cache: {e}")
        return set()


def save_waiver_ids_to_cache(league_id: int, waiver_ids: Set[int]) -> bool:
    """Save waiver player IDs to cache file.
    
    Args:
        league_id: ESPN league ID
        waiver_ids: Set of player IDs on waivers
        
    Returns:
        True if saved successfully, False otherwise
    """
    cache_file = get_waiver_cache_file(league_id)
    
    try:
        data = {
            'waiver_player_ids': list(waiver_ids),
            'cached_at': datetime.utcnow().isoformat(),
            'league_id': league_id
        }
        
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving waiver cache: {e}")
        return False


def get_waiver_ids_smart(league, league_id: int) -> Set[int]:
    """Get waiver player IDs, using cache until 3AM PT daily.
    
    Strategy:
    - Check cache first (if not expired)
    - If expired or missing, fetch from API and update cache
    - Cache expires at 3AM PT every day (when NBA waiver period resets)
    
    Args:
        league: ESPN League object
        league_id: ESPN league ID
        
    Returns:
        Set of player IDs currently on waivers
    """
    # Try to load from cache first
    cached_ids = load_waiver_ids_from_cache(league_id)
    if cached_ids:
        return cached_ids
    
    # Cache is expired or missing, fetch from API
    try:
        from scout.free_agent_scouting import get_waiver_player_ids
        waiver_ids = get_waiver_player_ids(league)
        
        # Save to cache for next time
        save_waiver_ids_to_cache(league_id, waiver_ids)
        
        return waiver_ids
    except Exception as e:
        print(f"Error fetching waiver IDs: {e}")
        return set()


def clear_waiver_cache(league_id: int = None) -> bool:
    """Clear cached waiver data.
    
    Args:
        league_id: Specific league to clear, or None to clear all
        
    Returns:
        True if cleared successfully
    """
    try:
        if league_id:
            cache_file = get_waiver_cache_file(league_id)
            if cache_file.exists():
                cache_file.unlink()
        else:
            import shutil
            if CACHE_DIR.exists():
                shutil.rmtree(CACHE_DIR)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        return True
    except Exception as e:
        print(f"Error clearing waiver cache: {e}")
        return False
