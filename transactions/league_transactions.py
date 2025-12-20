"""Track and analyze recent league transactions.

This module provides functionality to view recent league transactions including:
- Trades between teams
- Waiver pickups and drops
- Free agent signings
- Transaction history and trends
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from espn_api.basketball.league import League
import os
from dateutil import parser as dateutil_parser


def format_timestamp(timestamp: Any) -> str:
    """Convert various timestamp formats to readable datetime string.
    
    Args:
        timestamp: Unix timestamp (seconds or milliseconds), datetime object, or string
        
    Returns:
        Human-readable datetime string (YYYY-MM-DD HH:MM:SS)
    """
    if timestamp is None:
        return "N/A"
    
    try:
        if isinstance(timestamp, int):
            # Check if it's milliseconds (13 digits) or seconds (10 digits)
            if timestamp > 10**11:  # Milliseconds
                dt = datetime.fromtimestamp(timestamp / 1000)
            else:  # Seconds
                dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(timestamp, datetime):
            return timestamp.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(timestamp, str):
            # Try to parse string timestamp
            dt = dateutil_parser.parse(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OverflowError):
        pass
    
    return str(timestamp)


def get_recent_transactions(league: League, limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent league transactions.
    
    Args:
        league: ESPN League object
        limit: Maximum number of recent transactions to retrieve
        
    Returns:
        List of transaction dictionaries with details
    """
    try:
        transactions = league.transactions()
        
        # Convert transaction objects to dictionaries
        transaction_list = []
        for trans in transactions[:limit]:
            trans_dict = {
                'type': getattr(trans, 'type', None),
                'scoring_period': getattr(trans, 'scoring_period', None),
                'date': getattr(trans, 'date', None),
                'timestamp': getattr(trans, 'timestamp', None),
                'items': str(getattr(trans, 'items', [])),
                'creator_id': getattr(trans, 'creator_id', None),
                'team_ids': getattr(trans, 'team_ids', []),
            }
            transaction_list.append(trans_dict)
        
        return transaction_list
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return []


def get_transactions_by_type(league: League, transaction_type: str = 'TRADE') -> List[Dict[str, Any]]:
    """Get transactions filtered by type.
    
    Args:
        league: ESPN League object
        transaction_type: Type of transaction ('TRADE', 'WAIVER', 'FA', etc.)
        
    Returns:
        List of transactions of the specified type
    """
    all_transactions = get_recent_transactions(league, limit=100)
    
    return [t for t in all_transactions if t.get('type') == transaction_type]


def get_team_transactions(league: League, team_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Get transactions for a specific team.
    
    Args:
        league: ESPN League object
        team_id: Team ID to filter by
        limit: Maximum number of transactions
        
    Returns:
        List of transactions involving the specified team
    """
    all_transactions = get_recent_transactions(league, limit=limit)
    
    return [t for t in all_transactions if team_id in t.get('team_ids', [])]


def get_transactions_by_scoring_period(league: League, scoring_period: int) -> List[Dict[str, Any]]:
    """Get transactions from a specific scoring period.
    
    Args:
        league: ESPN League object
        scoring_period: Scoring period number to filter by
        
    Returns:
        List of transactions from the specified period
    """
    all_transactions = get_recent_transactions(league, limit=200)
    
    return [t for t in all_transactions if t.get('scoring_period') == scoring_period]


def get_recent_pickups(league: League, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent waiver pickups and free agent signings.
    
    Args:
        league: ESPN League object
        limit: Maximum number of pickups to retrieve
        
    Returns:
        List of pickup transactions
    """
    all_transactions = get_recent_transactions(league, limit=limit*2)
    
    # Filter for waiver and FA transactions
    pickups = [
        t for t in all_transactions 
        if t.get('type') in ['WAIVER', 'FA']
    ]
    
    return pickups[:limit]


def get_recent_trades(league: League, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent trades between teams.
    
    Args:
        league: ESPN League object
        limit: Maximum number of trades to retrieve
        
    Returns:
        List of trade transactions
    """
    all_transactions = get_recent_transactions(league, limit=limit*2)
    
    # Filter for trades
    trades = [t for t in all_transactions if t.get('type') == 'TRADE']
    
    return trades[:limit]


def get_transaction_summary(league: League, hours: int = 24) -> Dict[str, Any]:
    """Get a summary of recent transaction activity.
    
    Args:
        league: ESPN League object
        hours: Look back this many hours for recent activity
        
    Returns:
        Dictionary with transaction summary statistics
    """
    all_transactions = get_recent_transactions(league, limit=100)
    
    now = datetime.utcnow()
    cutoff_time = now - timedelta(hours=hours)
    
    recent = []
    for trans in all_transactions:
        trans_time = trans.get('date')
        # Handle both datetime objects and timestamps
        if trans_time:
            try:
                if isinstance(trans_time, int):
                    # Convert milliseconds timestamp to datetime
                    trans_time = datetime.fromtimestamp(trans_time / 1000)
                if trans_time > cutoff_time:
                    recent.append(trans)
            except (TypeError, ValueError):
                # If we can't parse the time, include it anyway
                recent.append(trans)
    
    # Summarize by type
    summary = {
        'total_transactions': len(recent),
        'by_type': {},
        'recent_transactions': recent
    }
    
    for trans in recent:
        trans_type = trans.get('type', 'UNKNOWN')
        if trans_type not in summary['by_type']:
            summary['by_type'][trans_type] = 0
        summary['by_type'][trans_type] += 1
    
    return summary


def print_recent_transactions(league: League, limit: int = 20):
    """Print recent transactions in a human-readable format.
    
    Args:
        league: ESPN League object
        limit: Maximum number of transactions to display
    """
    transactions = get_recent_transactions(league, limit=limit)
    
    print(f"\n📊 RECENT LEAGUE TRANSACTIONS (Last {limit})\n")
    print(f"{'Period':<8} | {'Type':<10} | {'Date':<20} | {'Details':<50}")
    print("-" * 90)
    
    for trans in transactions:
        period = trans.get('scoring_period', 'N/A')
        trans_type = trans.get('type', 'N/A')
        date = format_timestamp(trans.get('date'))
        items = trans.get('items', 'N/A')
        
        # Truncate items for display
        if len(str(items)) > 50:
            items = str(items)[:47] + "..."
        
        print(f"{str(period):<8} | {str(trans_type):<10} | {date:<20} | {str(items):<50}")


def print_team_transactions(league: League, team_id: int, limit: int = 20):
    """Print transactions for a specific team.
    
    Args:
        league: ESPN League object
        team_id: Team ID to filter by
        limit: Maximum number of transactions to display
    """
    # Get team name
    team = next((t for t in league.teams if t.team_id == team_id), None)
    team_name = team.team_name if team else f"Team {team_id}"
    
    transactions = get_team_transactions(league, team_id, limit=limit)
    
    print(f"\n📊 TRANSACTIONS FOR {team_name.upper()} (Last {len(transactions)})\n")
    print(f"{'Period':<8} | {'Type':<10} | {'Date':<20} | {'Details':<50}")
    print("-" * 90)
    
    for trans in transactions:
        period = trans.get('scoring_period', 'N/A')
        trans_type = trans.get('type', 'N/A')
        date = format_timestamp(trans.get('date'))
        items = trans.get('items', 'N/A')
        
        if len(str(items)) > 50:
            items = str(items)[:47] + "..."
        
        print(f"{str(period):<8} | {str(trans_type):<10} | {date:<20} | {str(items):<50}")


def print_recent_pickups(league: League, limit: int = 20):
    """Print recent waiver pickups and free agent signings.
    
    Args:
        league: ESPN League object
        limit: Maximum number of pickups to display
    """
    pickups = get_recent_pickups(league, limit=limit)
    
    print(f"\n🔄 RECENT PICKUPS & FREE AGENT SIGNINGS (Last {len(pickups)})\n")
    print(f"{'Period':<8} | {'Type':<10} | {'Date':<20} | {'Details':<50}")
    print("-" * 90)
    
    for pickup in pickups:
        period = pickup.get('scoring_period', 'N/A')
        trans_type = pickup.get('type', 'N/A')
        date = format_timestamp(pickup.get('date'))
        items = pickup.get('items', 'N/A')
        
        if len(str(items)) > 50:
            items = str(items)[:47] + "..."
        
        print(f"{str(period):<8} | {str(trans_type):<10} | {date:<20} | {str(items):<50}")


def print_recent_trades(league: League, limit: int = 20):
    """Print recent trades between teams.
    
    Args:
        league: ESPN League object
        limit: Maximum number of trades to display
    """
    trades = get_recent_trades(league, limit=limit)
    
    print(f"\n💱 RECENT TRADES (Last {len(trades)})\n")
    print(f"{'Period':<8} | {'Date':<20} | {'Details':<60}")
    print("-" * 95)
    
    for trade in trades:
        period = trade.get('scoring_period', 'N/A')
        date = format_timestamp(trade.get('date'))
        items = trade.get('items', 'N/A')
        
        if len(str(items)) > 60:
            items = str(items)[:57] + "..."
        
        print(f"{str(period):<8} | {date:<20} | {str(items):<60}")


def main():
    """Main function to display recent league transactions.
    
    Creates a fresh league instance without using cache and displays
    recent transaction activity.
    """
    import sys
    from pathlib import Path
    
    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # Clear cache to force fresh data fetch
    cache_dir = os.path.expanduser("~/.fantasy_league_cache")
    cache_file = os.path.join(cache_dir, "league_2026.pkl")
    
    if os.path.exists(cache_file):
        try:
            os.remove(cache_file)
            print("🗑️  Cleared cached league data\n")
        except Exception as e:
            print(f"⚠️  Could not clear cache: {e}\n")
    
    # Import here to avoid circular imports
    from utils.create_league import create_league
    
    print("📡 Loading fresh league data from ESPN...\n")
    league = create_league()
    
    print("✅ League loaded successfully!\n")
    
    # Display transaction information
    print_recent_transactions(league, limit=100)
    print("\n" + "="*90)
    print_recent_pickups(league, limit=10)
    print("\n" + "="*90)
    print_recent_trades(league, limit=10)
    print("\n" + "="*90)
    
    # Display summary
    print("\n📈 TRANSACTION SUMMARY:\n")
    summary = get_transaction_summary(league, hours=24)
    print(f"Recent Transactions (24h): {summary['total_transactions']}")
    if summary['by_type']:
        print(f"By Type: {summary['by_type']}")
    print()


if __name__ == "__main__":
    main()
