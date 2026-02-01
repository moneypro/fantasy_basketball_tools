"""NBA statistics caching utilities - similar pattern to create_league.py"""

import os
import pickle
from typing import Dict, Optional
from datetime import datetime, timedelta


def get_nba_cache_path(season: str = '2024-25') -> str:
    """Get the cache file path for NBA stats.

    Args:
        season: NBA season (e.g., '2024-25')

    Returns:
        Path to cache file
    """
    cache_dir: str = os.path.expanduser("~/.nba_stats_cache")
    os.makedirs(cache_dir, exist_ok=True)
    # Sanitize season string for filename
    season_safe = season.replace('-', '_')
    return os.path.join(cache_dir, f"nba_stats_{season_safe}.pkl")


def get_nba_team_defensive_ratings(season: str = '2024-25', use_local_cache: bool = True) -> Dict[str, float]:
    """Get defensive ratings for all NBA teams with caching.

    Args:
        season: NBA season (e.g., '2024-25')
        use_local_cache: If True, try to load from cache first

    Returns:
        Dict mapping team abbreviation to defensive rating (lower is better)
    """
    cache_path: str = get_nba_cache_path(season)

    # Try to load from cache first
    if use_local_cache and os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                cached_data = pickle.load(f)
                print(f"✅ Loaded NBA stats from cache: {cache_path}")
                return cached_data
        except Exception as e:
            print(f"⚠️ Failed to load NBA stats cache for {season}: {e}. Will fetch from NBA API.")

    # Fetch from NBA API if not cached
    print(f"📊 Fetching NBA team stats from NBA API for {season}...")

    try:
        from nba_api.stats.endpoints import leaguedashteamstats
        from espn_api.basketball.constant import PRO_TEAM_MAP

        # Fetch advanced stats from NBA API
        stats = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_detailed_defense='Advanced',
            last_n_games=30,
        )
        df = stats.get_data_frames()[0]

        # Build mapping from NBA team name/abbreviation to ESPN abbreviation
        # Map NBA team names to ESPN abbreviations
        nba_to_espn_map = {
            'Atlanta Hawks': 'ATL',
            'Boston Celtics': 'BOS',
            'Brooklyn Nets': 'BKN',
            'Charlotte Hornets': 'CHA',
            'Chicago Bulls': 'CHI',
            'Cleveland Cavaliers': 'CLE',
            'Dallas Mavericks': 'DAL',
            'Denver Nuggets': 'DEN',
            'Detroit Pistons': 'DET',
            'Golden State Warriors': 'GS',
            'Houston Rockets': 'HOU',
            'Indiana Pacers': 'IND',
            'LA Clippers': 'LAC',
            'Los Angeles Lakers': 'LAL',
            'Memphis Grizzlies': 'MEM',
            'Miami Heat': 'MIA',
            'Milwaukee Bucks': 'MIL',
            'Minnesota Timberwolves': 'MIN',
            'New Orleans Pelicans': 'NOP',
            'New York Knicks': 'NY',
            'Oklahoma City Thunder': 'OKC',
            'Orlando Magic': 'ORL',
            'Philadelphia 76ers': 'PHI',
            'Phoenix Suns': 'PHX',
            'Portland Trail Blazers': 'POR',
            'Sacramento Kings': 'SAC',
            'San Antonio Spurs': 'SA',
            'Toronto Raptors': 'TOR',
            'Utah Jazz': 'UTAH',
            'Washington Wizards': 'WSH'
        }

        # Extract defensive ratings
        def_ratings = {}
        for _, row in df.iterrows():
            team_name = row['TEAM_NAME']
            def_rating = row.get('DEF_RATING', None)

            if team_name in nba_to_espn_map and def_rating is not None:
                espn_abbr = nba_to_espn_map[team_name]
                def_ratings[espn_abbr] = round(float(def_rating), 1)

        # Cache the data for future use
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(def_ratings, f)
            print(f"✅ Cached NBA stats to: {cache_path} ({len(def_ratings)} teams)")
        except Exception as e:
            print(f"⚠️ Failed to cache NBA stats for {season}: {e}")

        return def_ratings

    except Exception as e:
        print(f"❌ Could not fetch NBA team defensive ratings: {e}")
        import traceback
        traceback.print_exc()
        return {}
