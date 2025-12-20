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
        if trans_time and trans_time > cutoff_time:
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
        date = trans.get('date', 'N/A')
        items = trans.get('items', 'N/A')
        
        # Truncate items for display
        if len(str(items)) > 50:
            items = str(items)[:47] + "..."
        
        print(f"{str(period):<8} | {str(trans_type):<10} | {str(date):<20} | {str(items):<50}")


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
        date = trans.get('date', 'N/A')
        items = trans.get('items', 'N/A')
        
        if len(str(items)) > 50:
            items = str(items)[:47] + "..."
        
        print(f"{str(period):<8} | {str(trans_type):<10} | {str(date):<20} | {str(items):<50}")


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
        date = pickup.get('date', 'N/A')
        items = pickup.get('items', 'N/A')
        
        if len(str(items)) > 50:
            items = str(items)[:47] + "..."
        
        print(f"{str(period):<8} | {str(trans_type):<10} | {str(date):<20} | {str(items):<50}")


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
        date = trade.get('date', 'N/A')
        items = trade.get('items', 'N/A')
        
        if len(str(items)) > 60:
            items = str(items)[:57] + "..."
        
        print(f"{str(period):<8} | {str(date):<20} | {str(items):<60}")
