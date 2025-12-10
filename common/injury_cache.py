"""Cache for team injury data (OUT and DAY_TO_DAY players).

Much faster than building all_players just to extract injuries.
Caches once per day or on manual refresh.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Cache directory for injury data
CACHE_DIR = Path(os.getenv('INJURY_CACHE_DIR', './cache/injuries'))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_injury_cache_file(league_id: int) -> Path:
    """Get the cache file path for a specific league.
    
    Args:
        league_id: ESPN league ID
        
    Returns:
        Path to the cache file
    """
    return CACHE_DIR / f"league_{league_id}_injuries.json"


def load_injuries_from_cache(league_id: int) -> Dict[str, List[Dict]]:
    """Load team injuries from cache file.
    
    Args:
        league_id: ESPN league ID
        
    Returns:
        Dictionary mapping NBA team to list of injured players, or empty dict if not cached
    """
    cache_file = get_injury_cache_file(league_id)
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading injury cache: {e}")
            return {}
    
    return {}


def save_injuries_to_cache(league_id: int, team_injuries_lookup: Dict[str, List[Dict]]) -> bool:
    """Save team injuries to cache file.
    
    Args:
        league_id: ESPN league ID
        team_injuries_lookup: Dictionary mapping NBA team to list of injured players
        
    Returns:
        True if saved successfully, False otherwise
    """
    cache_file = get_injury_cache_file(league_id)
    
    try:
        data = {
            'team_injuries': team_injuries_lookup,
            'cached_at': datetime.utcnow().isoformat(),
            'league_id': league_id
        }
        
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving injury cache: {e}")
        return False


def get_injuries_smart(league, league_id: int, force_refresh: bool = False) -> Dict[str, List[Dict]]:
    """Get team injuries, using cache if available.
    
    Strategy:
    - First call or force_refresh: fetch all player injury data and cache
    - Subsequent calls: load from cache
    - Cache can be manually refreshed via force_refresh=True
    
    Args:
        league: ESPN League object
        league_id: ESPN league ID
        force_refresh: If True, fetch from API even if cache exists
        
    Returns:
        Dictionary mapping NBA team to list of injured players
    """
    # Try to load from cache first (unless force_refresh)
    if not force_refresh:
        cached_injuries = load_injuries_from_cache(league_id)
        if cached_injuries:
            return cached_injuries
    
    # Cache miss or force_refresh, need to build from league data
    try:
        from scout.free_agent_scouting import build_team_injuries_lookup
        
        # Build all_players (ONLY for this, could be optimized further)
        all_players = {}
        for team in league.teams:
            for player in team.roster:
                all_players[player.playerId] = player
        
        # Free agents also have injury status
        free_agents = league.free_agents(size=1000)
        for player in free_agents:
            all_players[player.playerId] = player
        
        # Build injuries lookup
        team_injuries_lookup = build_team_injuries_lookup(all_players)
        
        # Save to cache for next time
        save_injuries_to_cache(league_id, team_injuries_lookup)
        
        return team_injuries_lookup
    except Exception as e:
        print(f"Error fetching injuries: {e}")
        return {}


def clear_injury_cache(league_id: int = None) -> bool:
    """Clear cached injury data.
    
    Args:
        league_id: Specific league to clear, or None to clear all
        
    Returns:
        True if cleared successfully
    """
    try:
        if league_id:
            cache_file = get_injury_cache_file(league_id)
            if cache_file.exists():
                cache_file.unlink()
        else:
            import shutil
            if CACHE_DIR.exists():
                shutil.rmtree(CACHE_DIR)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        return True
    except Exception as e:
        print(f"Error clearing injury cache: {e}")
        return False
