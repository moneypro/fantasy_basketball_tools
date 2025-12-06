"""League creation and caching utilities."""
import os
import pickle
from typing import Optional

from espn_api.basketball import League
from common.io import get_file_content_from_crendential_folder


def get_cache_path(year: int) -> str:
    """Get the cache file path for a given year.
    
    Args:
        year: The league year
        
    Returns:
        The full path to the cache file
    """
    cache_dir: str = os.path.expanduser("~/.fantasy_league_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"league_{year}.pkl")


def create_league(year: int = 2026, use_local_cache: bool = True) -> League:
    """Create or load a fantasy basketball league.
    
    Attempts to load from local cache first if use_local_cache is True.
    Falls back to fetching from ESPN if cache is not available.
    
    Args:
        year: The league year (default: 2026)
        use_local_cache: Whether to use local cache (default: True)
        
    Returns:
        The League object
    """
    cache_path: str = get_cache_path(year)
    league: Optional[League] = None

    # Try to load from cache
    if use_local_cache and os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                league = pickle.load(f)
            print(f"Loaded league data for {year} from cache: {cache_path}")
            return league
        except Exception as e:
            print(f"Failed to load cache for {year}: {e}. Will fetch from ESPN.")

    # Fetch from ESPN if not cached
    # Try to get credentials from files first, fall back to environment variables
    try:
        league_id = int(get_file_content_from_crendential_folder("league_id.txt"))
        espn_s2 = get_file_content_from_crendential_folder("espn_s2.secret")
        swid = get_file_content_from_crendential_folder("swid.secret")
    except Exception:
        # Fall back to environment variables (Docker deployment)
        league_id = os.getenv('LEAGUE_ID')
        espn_s2 = os.getenv('ESPN_S2')
        swid = os.getenv('SWID')
        
        if not all([league_id, espn_s2, swid]):
            raise ValueError("Could not find credentials in credential files or environment variables (LEAGUE_ID, ESPN_S2, SWID)")
        league_id = int(league_id)
    
    league = League(
        league_id=league_id,
        year=year,
        espn_s2=espn_s2,
        swid=swid
    )

    # Cache the league object for future use
    try:
        with open(cache_path, "wb") as f:
            pickle.dump(league, f)
        print(f"Cached league data for {year} at: {cache_path}")
    except Exception as e:
        print(f"Failed to cache league data for {year}: {e}")

    return league