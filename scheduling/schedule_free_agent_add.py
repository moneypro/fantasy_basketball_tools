#!/usr/bin/env python3
"""
Schedule a free agent transaction to be posted at 12:15 AM on a specified date.

This script uses the 'at' command to schedule the posting script to run at a fixed
time (12:15 AM) on the specified date. The posting script will then send POST requests
to the ESPN Fantasy Basketball API once per minute for 45 minutes.

Usage:
    python3 schedule_free_agent_add.py <player_id> "<date>"
    python3 schedule_free_agent_add.py --player-id=<id> --date="<date>"
    
Examples:
    python3 schedule_free_agent_add.py 5211175 "Dec 5 2025"
    python3 schedule_free_agent_add.py --player-id=5211175 --date="Dec 5 2025"
    python3 schedule_free_agent_add.py 5211175 "Dec 5 2025" --team-id=2 --scoring-period-id=45
"""

import sys
import os
import logging
import subprocess
from datetime import datetime
from typing import Optional, Tuple


def setup_logging() -> logging.Logger:
    """Set up logging to both console and file.
    
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger('schedule_free_agent')
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # File handler - logs to a file in the repo root
    try:
        log_dir = os.path.join(get_repo_root(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, 'schedule_free_agent.log'))
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    return logger


def get_repo_root() -> str:
    """Get the repository root directory.
    
    This function finds the root of the fantasy_basketball_tools repository
    by looking for the directory name in the current path.
    
    Returns:
        The absolute path to the repository root
        
    Raises:
        RuntimeError: If the repository root cannot be found
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    curr_path = os.path.abspath(script_dir)
    directory = "fantasy_basketball_tools"
    
    while curr_path != os.path.dirname(curr_path):  # Stop at root
        if os.path.basename(curr_path) == directory:
            return curr_path
        curr_path = os.path.dirname(curr_path)
    
    # Alternative: look for the directory name in the path
    index = curr_path.rfind(directory)
    if index != -1:
        return curr_path[:index + len(directory)]
    
    raise RuntimeError(f"Cannot find {directory} in the current path hierarchy")


def parse_arguments() -> Tuple[int, str, int, int]:
    """Parse command-line arguments.
    
    Supports both positional and flag-based arguments:
    - Positional: python3 script.py <player_id> "<date>" [--team-id=<id>] [--scoring-period-id=<id>]
    - Flags: python3 script.py --player-id=<id> --date="<date>" [--team-id=<id>] [--scoring-period-id=<id>]
    
    Returns:
        A tuple of (player_id, date_string, team_id, scoring_period_id)
        
    Raises:
        SystemExit: If required arguments are missing or invalid
    """
    player_id: Optional[int] = None
    date_string: Optional[str] = None
    team_id: int = 2
    scoring_period_id: int = 45
    
    positional_args = []
    
    # Parse arguments
    for arg in sys.argv[1:]:
        if arg.startswith('--player-id='):
            try:
                player_id = int(arg.split('=', 1)[1])
            except ValueError:
                print(f"Error: Invalid player ID: {arg.split('=', 1)[1]}", file=sys.stderr)
                sys.exit(1)
        elif arg.startswith('--date='):
            date_string = arg.split('=', 1)[1]
        elif arg.startswith('--team-id='):
            try:
                team_id = int(arg.split('=', 1)[1])
            except ValueError:
                team_id = 2
        elif arg.startswith('--scoring-period-id='):
            try:
                scoring_period_id = int(arg.split('=', 1)[1])
            except ValueError:
                scoring_period_id = 45
        elif not arg.startswith('--'):
            positional_args.append(arg)
    
    # Handle positional arguments
    if len(positional_args) > 0:
        try:
            player_id = int(positional_args[0])
        except ValueError:
            print(f"Error: Invalid player ID: {positional_args[0]}", file=sys.stderr)
            sys.exit(1)
    
    if len(positional_args) > 1:
        date_string = positional_args[1]
    
    # Validate required arguments
    if player_id is None:
        print("Error: player_id is required", file=sys.stderr)
        print_usage()
        sys.exit(1)
    
    if date_string is None:
        print("Error: date is required", file=sys.stderr)
        print_usage()
        sys.exit(1)
    
    return player_id, date_string, team_id, scoring_period_id


def print_usage() -> None:
    """Print usage information."""
    print("Usage:", file=sys.stderr)
    print("  python3 schedule_free_agent_add.py <player_id> \"<date>\"", file=sys.stderr)
    print("  python3 schedule_free_agent_add.py --player-id=<id> --date=\"<date>\"", file=sys.stderr)
    print("", file=sys.stderr)
    print("Examples:", file=sys.stderr)
    print("  python3 schedule_free_agent_add.py 5211175 \"Dec 5 2025\"", file=sys.stderr)
    print("  python3 schedule_free_agent_add.py --player-id=5211175 --date=\"Dec 5 2025\"", file=sys.stderr)


def validate_date_format(date_string: str) -> None:
    """Validate that the date string is in a format acceptable to 'at'.
    
    Args:
        date_string: The date string to validate
        
    Raises:
        ValueError: If the date format is not recognized
    """
    # The 'at' command accepts various formats. We'll just do a basic sanity check.
    # The at command will validate more thoroughly when we execute it.
    if not date_string or len(date_string.strip()) == 0:
        raise ValueError("Date string cannot be empty")


def get_posting_script_path() -> str:
    """Get the absolute path to the posting script.
    
    Returns:
        The absolute path to post_free_agent_transaction.py
        
    Raises:
        FileNotFoundError: If the posting script does not exist
    """
    repo_root = get_repo_root()
    posting_script = os.path.join(repo_root, 'scheduling', 'post_free_agent_transaction.py')
    
    if not os.path.exists(posting_script):
        raise FileNotFoundError(f"Posting script not found at: {posting_script}")
    
    return posting_script


def schedule_with_at(player_id: int, date_string: str, team_id: int,
                     scoring_period_id: int, posting_script: str,
                     logger: logging.Logger) -> None:
    """Schedule the posting script using the 'at' command.
    
    Args:
        player_id: The player ID to add
        date_string: The date to schedule (e.g., "Dec 5 2025")
        team_id: The team ID
        scoring_period_id: The scoring period ID
        posting_script: The absolute path to the posting script
        logger: A logger instance
        
    Raises:
        RuntimeError: If the 'at' command fails
    """
    # Build the command to execute via 'at'
    # Using environment variables to pass parameters to the posting script
    cmd_to_schedule = (
        f"cd {get_repo_root()} && "
        f"PLAYER_ID={player_id} TEAM_ID={team_id} SCORING_PERIOD_ID={scoring_period_id} "
        f"python3 {posting_script}"
    )
    
    logger.info(f"Scheduling FREEAGENT add: playerId={player_id} at 12:15 AM {date_string}")
    logger.info(f"Posting script: {posting_script}")
    logger.info(f"Command to execute: {cmd_to_schedule}")
    
    try:
        # Use 'at' to schedule the job
        # The 'at' command reads from stdin, so we pipe the command to it
        process = subprocess.Popen(
            ['at', '12:15 AM', date_string],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=cmd_to_schedule)
        
        if process.returncode != 0:
            error_msg = stderr.strip() if stderr else stdout.strip()
            raise RuntimeError(f"'at' command failed: {error_msg}")
        
        logger.info(f"Successfully scheduled job. Output: {stdout.strip()}")
        
        # Also print to console for user feedback
        print(f"\n✓ Successfully scheduled transaction")
        print(f"  Player ID: {player_id}")
        print(f"  Date: {date_string}")
        print(f"  Time: 12:15 AM (fixed)")
        print(f"  Team ID: {team_id}")
        print(f"  Scoring Period ID: {scoring_period_id}")
        print(f"\nSchedule output: {stdout.strip()}")
        
    except FileNotFoundError:
        raise RuntimeError(
            "The 'at' command is not available on this system. "
            "Please install the 'at' service (e.g., 'sudo apt-get install at' on Ubuntu)"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to schedule job: {e}")


def main() -> None:
    """Main entry point for the scheduling script."""
    logger = setup_logging()
    
    try:
        # Parse arguments
        player_id, date_string, team_id, scoring_period_id = parse_arguments()
        
        # Validate date format
        validate_date_format(date_string)
        
        # Get the posting script path
        posting_script = get_posting_script_path()
        
        # Schedule the job using 'at'
        schedule_with_at(player_id, date_string, team_id, scoring_period_id,
                        posting_script, logger)
        
    except ValueError as e:
        logger.error(f"Argument error: {e}")
        print_usage()
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"Scheduling error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
