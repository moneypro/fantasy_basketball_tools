import os
import pickle
from espn_api.basketball import League
from common.io import get_file_content_from_crendential_folder

def get_cache_path(year):
    # You can customize this path as needed
    cache_dir = os.path.expanduser("~/.fantasy_league_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"league_{year}.pkl")

def create_league(year: int = 2026, use_local_cache: bool = True) -> League:
    cache_path = get_cache_path(year)
    league = None

    if use_local_cache and os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                league = pickle.load(f)
            print(f"Loaded league data for {year} from cache: {cache_path}")
            return league
        except Exception as e:
            print(f"Failed to load cache for {year}: {e}. Will fetch from ESPN.")

    # If not using cache or cache failed, fetch from ESPN
    league = League(
        league_id=int(get_file_content_from_crendential_folder("league_id.txt")),
        year=year,
        espn_s2=get_file_content_from_crendential_folder("espn_s2.secret"),
        swid=get_file_content_from_crendential_folder("swid.secret")
    )

    # Cache the league object for future use
    try:
        with open(cache_path, "wb") as f:
            pickle.dump(league, f)
        print(f"Cached league data for {year} at: {cache_path}")
    except Exception as e:
        print(f"Failed to cache league data for {year}: {e}")

    return league