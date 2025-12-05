#!/usr/bin/env python3
"""
Post a FREEAGENT transaction to ESPN Fantasy Basketball API.

This script sends a POST request to the ESPN Fantasy Basketball transaction API
to add a free agent to a team. It runs for 45 iterations, sending a request once
per minute.

The playerId, teamId, and scoringPeriodId can be provided via command-line arguments,
environment variables, or defaults will be used.

Usage:
    python3 post_free_agent_transaction.py [--player-id=<id>] [--team-id=<id>] [--scoring-period-id=<id>]
    PLAYER_ID=5211175 python3 post_free_agent_transaction.py
"""

import sys
import os
import json
import time
import logging
from datetime import datetime
from typing import Optional
import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.io import get_file_content_from_crendential_folder


def setup_logging() -> logging.Logger:
    """Set up logging to both console and file.
    
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger('post_free_agent')
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # File handler - logs to a file in the repo root
    try:
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, 'post_free_agent.log'))
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    return logger


def get_player_id() -> int:
    """Get the player ID from command-line argument or environment variable.
    
    Returns:
        The player ID as an integer
        
    Raises:
        ValueError: If player ID is not provided or invalid
    """
    # Check command-line arguments first
    for arg in sys.argv[1:]:
        if arg.startswith('--player-id='):
            try:
                return int(arg.split('=')[1])
            except ValueError:
                raise ValueError(f"Invalid player ID: {arg.split('=')[1]}")
    
    # Check environment variable
    player_id_env = os.environ.get('PLAYER_ID')
    if player_id_env:
        try:
            return int(player_id_env)
        except ValueError:
            raise ValueError(f"Invalid PLAYER_ID environment variable: {player_id_env}")
    
    raise ValueError("PLAYER_ID must be provided via --player-id=<id> or PLAYER_ID environment variable")


def get_team_id() -> int:
    """Get the team ID from command-line argument or environment variable.
    
    Returns:
        The team ID as an integer (default: 2)
    """
    # Check command-line arguments
    for arg in sys.argv[1:]:
        if arg.startswith('--team-id='):
            try:
                return int(arg.split('=')[1])
            except ValueError:
                return 2
    
    # Check environment variable
    team_id_env = os.environ.get('TEAM_ID')
    if team_id_env:
        try:
            return int(team_id_env)
        except ValueError:
            return 2
    
    return 2


def get_scoring_period_id() -> int:
    """Get the scoring period ID from command-line argument or environment variable.
    
    Returns:
        The scoring period ID as an integer (default: 45)
    """
    # Check command-line arguments
    for arg in sys.argv[1:]:
        if arg.startswith('--scoring-period-id='):
            try:
                return int(arg.split('=')[1])
            except ValueError:
                return 45
    
    # Check environment variable
    scoring_period_env = os.environ.get('SCORING_PERIOD_ID')
    if scoring_period_env:
        try:
            return int(scoring_period_env)
        except ValueError:
            return 45
    
    return 45


def get_espn_credentials() -> tuple[str, str]:
    """Load ESPN credentials from the credentials folder.
    
    Returns:
        A tuple of (espn_s2, swid)
        
    Raises:
        FileNotFoundError: If credential files are not found
    """
    try:
        espn_s2 = get_file_content_from_crendential_folder('espn_s2.secret')
        swid = get_file_content_from_crendential_folder('swid.secret')
        return espn_s2, swid
    except Exception as e:
        raise FileNotFoundError(f"Failed to load ESPN credentials: {e}")


def build_cookie_header(espn_s2: str, swid: str) -> str:
    """Build the Cookie header value from ESPN credentials.
    
    Args:
        espn_s2: The ESPN S2 token
        swid: The SWID token
        
    Returns:
        The formatted Cookie header value
    """
    return f'SWID={swid}; ESPN-ONESITE.WEB-PROD-ac=XUS; espnAuth={{"swid":"{swid}"}}; espn_s2={espn_s2};'


def build_transaction_payload(player_id: int, team_id: int, scoring_period_id: int) -> dict:
    """Build the transaction payload for the API request.
    
    Args:
        player_id: The player ID to add
        team_id: The team ID
        scoring_period_id: The scoring period ID
        
    Returns:
        The transaction payload as a dictionary
    """
    return {
        "isLeagueManager": False,
        "teamId": team_id,
        "type": "FREEAGENT",
        "scoringPeriodId": scoring_period_id,
        "executionType": "EXECUTE",
        "items": [
            {
                "playerId": player_id,
                "type": "ADD",
                "toTeamId": team_id
            }
        ]
    }


def post_transaction(url: str, player_id: int, team_id: int, scoring_period_id: int,
                    cookie_header: str, logger: logging.Logger) -> None:
    """Post free agent transaction requests 45 times, once per minute.
    
    Args:
        url: The transaction API endpoint URL
        player_id: The player ID to add
        team_id: The team ID
        scoring_period_id: The scoring period ID
        cookie_header: The Cookie header value for authentication
        logger: A logger instance
    """
    headers = {
        'Cookie': cookie_header,
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.49.1',
        'Accept': '*/*'
    }
    
    payload = build_transaction_payload(player_id, team_id, scoring_period_id)
    
    logger.info(f"Starting transaction loop for playerId={player_id}, teamId={team_id}, "
                f"scoringPeriodId={scoring_period_id}")
    
    for i in range(1, 46):
        timestamp = datetime.now().isoformat()
        logger.info(f"{timestamp} - Request {i}/45")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"Request {i}/45 succeeded (HTTP {response.status_code})")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request {i}/45 failed: {e}")
        
        # Sleep between requests (except after the last one)
        if i < 45:
            time.sleep(60)
    
    logger.info("Transaction loop completed")


def main() -> None:
    """Main entry point for the script."""
    logger = setup_logging()
    
    try:
        # Get parameters
        player_id = get_player_id()
        team_id = get_team_id()
        scoring_period_id = get_scoring_period_id()
        
        # Load credentials
        espn_s2, swid = get_espn_credentials()
        
        # Build the transaction URL
        url = "https://lm-api-writes.fantasy.espn.com/apis/v3/games/fba/seasons/2026/segments/0/leagues/30695/transactions/"
        
        # Build headers
        cookie_header = build_cookie_header(espn_s2, swid)
        
        # Post the transaction
        post_transaction(url, player_id, team_id, scoring_period_id, cookie_header, logger)
        
    except ValueError as e:
        logger.error(f"Argument error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
