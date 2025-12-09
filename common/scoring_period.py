"""Utilities for converting between scoring periods and dates."""

from datetime import datetime, timedelta

# Scoring period 1 = Oct 21, 2025 (Tuesday)
# Each scoring period = 1 day
SCORING_PERIOD_START_DATE = datetime(2025, 10, 21)


def scoring_period_to_date(scoring_period: int) -> datetime:
    """Convert scoring period number to date.
    
    Args:
        scoring_period: Scoring period number (1-based)
        
    Returns:
        datetime object for that scoring period
        
    Example:
        scoring_period_to_date(1) -> 2025-10-21
        scoring_period_to_date(49) -> 2025-12-08
    """
    # Subtract 1 because period 1 is the first day
    days_offset = scoring_period - 1
    return SCORING_PERIOD_START_DATE + timedelta(days=days_offset)


def scoring_period_to_date_string(scoring_period: int) -> str:
    """Convert scoring period to YYYY-MM-DD format.
    
    Args:
        scoring_period: Scoring period number
        
    Returns:
        Date string in YYYY-MM-DD format
    """
    date = scoring_period_to_date(scoring_period)
    return date.strftime("%Y-%m-%d")


def scoring_period_to_day_of_week(scoring_period: int) -> str:
    """Convert scoring period to day of week name.
    
    Args:
        scoring_period: Scoring period number
        
    Returns:
        Day name (e.g., "Monday", "Tuesday", etc.)
    """
    date = scoring_period_to_date(scoring_period)
    return date.strftime("%A")


def scoring_period_to_date_and_day(scoring_period: int) -> tuple:
    """Convert scoring period to both date and day of week.
    
    Args:
        scoring_period: Scoring period number
        
    Returns:
        Tuple of (date_string, day_of_week)
        
    Example:
        scoring_period_to_date_and_day(49) -> ("2025-12-08", "Monday")
    """
    date = scoring_period_to_date(scoring_period)
    date_str = date.strftime("%Y-%m-%d")
    day_name = date.strftime("%A")
    return date_str, day_name
