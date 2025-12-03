"""Configuration constants for fantasy basketball analysis."""

# Player scouting configuration
RECENT_STATS_RATIO: float = 0.5  # Weight of recent stats vs projected stats
ADJUSTER: float = 1.0  # Games played adjustment factor
TEAM_CONTEXT_ALPHA: float = 0.2  # Team context boost factor
OFFENSIVE_RATING_BETA: float = 0.5  # Offensive rating scaling factor

# Player scouting top N teammates
TOP_TEAMMATES_COUNT: int = 5

# Default season for team stats
DEFAULT_STATS_SEASON: str = '2024-25'

# Free agents query size
FREE_AGENTS_SIZE: int = 1000

# Roster prediction configuration
DAILY_ACTIVE_SIZE_DEFAULT: int = 10
DAILY_ACTIVE_SIZE_GAMES: int = 9
ROSTER_SIZE_CAP: int = 10
UTIL_POSITION_CAP: int = 4

# Stat periods for player analysis
STAT_PERIODS: list = ['2026_last_30', '2026_last_15', '2026_last_7', '2026_projected']

# Injury status configuration
DEFAULT_INJURY_STATUS: list = ['ACTIVE']

# Fantasy scoring weights
FANTASY_POINTS_WEIGHTS: dict = {
    'PTS': 1.0,
    '3PTM': 1.0,
    'FGA': -1.0,
    'FGM': 2.0,
    'FTA': -1.0,
    'FTM': 1.0,
    'REB': 1.0,
    'AST': 2.0,
    'STL': 4.0,
    'BLK': 4.0,
    'TO': -2.0,
}

# Lineup positions
PRIMARY_POSITIONS: list = ['PG', 'SG', 'SF', 'PF', 'C']
BENCH_POSITION: str = 'BE'
UTIL_POSITION: str = 'UT'

# AWS Configuration
AWS_REGION: str = "us-west-2"
SENDER_EMAIL: str = "Fantasy Basketball <fantasybasketball@chenghong.info>"
