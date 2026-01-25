"""Date and scoring period utilities for fantasy basketball."""
from datetime import datetime, date, timedelta
from typing import Union, Tuple


class DateScoringPeriodConverter:
    """Convert between dates and ESPN scoring periods for 2024-25 NBA season."""

    # NBA 2024-25 season starts on October 22, 2024 (scoring period 1)
    SEASON_START_DATE = date(2024, 10, 22)
    SEASON_YEAR = "2024-25"

    @classmethod
    def date_to_scoring_period(cls, input_date: Union[str, date, datetime]) -> int:
        """Convert a date to ESPN scoring period number.

        Args:
            input_date: Date as string (YYYY-MM-DD), date object, or datetime object

        Returns:
            Scoring period number (1-based)

        Raises:
            ValueError: If date is before season start
        """
        if isinstance(input_date, str):
            parsed_date = datetime.strptime(input_date, "%Y-%m-%d").date()
        elif isinstance(input_date, datetime):
            parsed_date = input_date.date()
        else:
            parsed_date = input_date

        if parsed_date < cls.SEASON_START_DATE:
            raise ValueError(f"Date {parsed_date} is before season start {cls.SEASON_START_DATE}")

        # Calculate days since season start (0-based) and add 1 for 1-based scoring period
        days_since_start = (parsed_date - cls.SEASON_START_DATE).days
        return days_since_start + 1

    @classmethod
    def scoring_period_to_date(cls, scoring_period: int) -> date:
        """Convert scoring period number to date.

        Args:
            scoring_period: Scoring period number (1-based)

        Returns:
            Date object for that scoring period

        Raises:
            ValueError: If scoring period is less than 1
        """
        if scoring_period < 1:
            raise ValueError(f"Scoring period must be >= 1, got {scoring_period}")

        # Subtract 1 to make it 0-based, then add days to season start
        days_offset = scoring_period - 1
        return cls.SEASON_START_DATE + timedelta(days=days_offset)

    @classmethod
    def matchup_week_to_date_range(cls, week_index: int) -> Tuple[date, date]:
        """Convert matchup week to date range.

        Args:
            week_index: Matchup week number (1-based)

        Returns:
            Tuple of (start_date, end_date) for the matchup week
        """
        # Use the same logic as Week class without importing it
        # This avoids circular imports and keeps date utils independent
        if week_index == 1:
            start_period, end_period = 0, 7
        else:
            start_period = 7 * (week_index - 1)
            end_period = 7 * week_index - 1

        # Convert to dates
        start_date = cls.scoring_period_to_date(start_period + 1)  # +1 because periods are 0-based
        end_date = cls.scoring_period_to_date(end_period + 1)

        return start_date, end_date

    @classmethod
    def get_current_scoring_period(cls) -> int:
        """Get the current scoring period based on today's date.

        Returns:
            Current scoring period number
        """
        today = date.today()
        if today < cls.SEASON_START_DATE:
            return 1  # Season hasn't started yet
        return cls.date_to_scoring_period(today)

    @classmethod
    def get_current_matchup_week(cls) -> int:
        """Get the current matchup week based on today's date.

        Uses the same logic as Week._match_up_week_to_scoring_period_convert
        but reversed to calculate week from current scoring period.

        Returns:
            Current matchup week number (1-23)
        """
        current_period = cls.get_current_scoring_period()

        # Week 1 is special: scoring periods 0-7 (days 1-8)
        if current_period <= 8:
            return 1

        # Week 2+: scoring period = 7 * (week - 1) to 7 * week - 1
        # Reverse: week = ceiling((period + 1) / 7)
        import math
        return math.ceil((current_period + 1) / 7)

    @classmethod
    def get_remaining_days_in_week(cls, week_index: int, current_date: Union[str, date, datetime] = None) -> int:
        """Calculate remaining days in a matchup week.

        Args:
            week_index: Matchup week number (1-based)
            current_date: Optional date to calculate from (defaults to today)

        Returns:
            Number of days remaining in the week (0 if week is over)
        """
        if current_date is None:
            current_date = date.today()
        elif isinstance(current_date, str):
            current_date = datetime.strptime(current_date, "%Y-%m-%d").date()
        elif isinstance(current_date, datetime):
            current_date = current_date.date()

        start_date, end_date = cls.matchup_week_to_date_range(week_index)

        if current_date > end_date:
            return 0  # Week is over
        elif current_date < start_date:
            # Week hasn't started yet, return total days in week
            return (end_date - start_date).days + 1
        else:
            # Week is in progress
            return (end_date - current_date).days + 1


def parse_date_or_period_input(date_or_period: Union[str, int]) -> Tuple[str, Union[int, str]]:
    """Parse input that could be either a date string or a period number.

    Args:
        date_or_period: Either a date string (YYYY-MM-DD) or scoring period/week number

    Returns:
        Tuple of (input_type, value) where input_type is 'date', 'scoring_period', or 'week'

    Examples:
        "2024-12-25" -> ('date', '2024-12-25')
        5 -> ('week', 5)
        "5" -> ('week', 5)
    """
    if isinstance(date_or_period, int):
        # Assume it's a week number
        return ('week', date_or_period)

    # Try to parse as date
    try:
        datetime.strptime(date_or_period, "%Y-%m-%d")
        return ('date', date_or_period)
    except (ValueError, TypeError):
        pass

    # Try to parse as number (week or scoring period)
    try:
        num = int(date_or_period)
        # If number is > 50, likely a scoring period, else a week
        if num > 50:
            return ('scoring_period', num)
        else:
            return ('week', num)
    except (ValueError, TypeError):
        pass

    raise ValueError(f"Could not parse '{date_or_period}' as date (YYYY-MM-DD) or period number")
