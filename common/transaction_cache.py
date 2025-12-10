"""Cache for ESPN league transactions to avoid repeated API calls."""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Cache directory for transaction data
CACHE_DIR = Path(os.getenv('TRANSACTION_CACHE_DIR', './cache/transactions'))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_transaction_cache_file(league_id: int, scoring_period: int) -> Path:
    """Get the cache file path for a specific league and scoring period.
    
    Args:
        league_id: ESPN league ID
        scoring_period: Scoring period number
        
    Returns:
        Path to the cache file
    """
    return CACHE_DIR / f"league_{league_id}_period_{scoring_period}.json"


def load_transactions_from_cache(league_id: int, scoring_period: int) -> List[Any]:
    """Load transactions from cache file if it exists.
    
    Args:
        league_id: ESPN league ID
        scoring_period: Scoring period number
        
    Returns:
        List of transactions, or empty list if not cached
    """
    cache_file = get_transaction_cache_file(league_id, scoring_period)
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading transaction cache for period {scoring_period}: {e}")
            return []
    
    return []


def save_transactions_to_cache(league_id: int, scoring_period: int, transactions: List[Any]) -> bool:
    """Save transactions to cache file.
    
    Args:
        league_id: ESPN league ID
        scoring_period: Scoring period number
        transactions: List of transaction objects (will be serialized)
        
    Returns:
        True if saved successfully, False otherwise
    """
    cache_file = get_transaction_cache_file(league_id, scoring_period)
    
    try:
        # Convert transaction objects to dicts for JSON serialization
        transactions_data = []
        for trans in transactions:
            trans_dict = {
                'type': getattr(trans, 'type', None),
                'scoring_period': getattr(trans, 'scoring_period', None),
                'items': str(getattr(trans, 'items', [])),  # Convert items to string
                'date': getattr(trans, 'date', None),
            }
            transactions_data.append(trans_dict)
        
        with open(cache_file, 'w') as f:
            json.dump(transactions_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving transaction cache for period {scoring_period}: {e}")
        return False


def get_transactions_smart(league, league_id: int, current_period: int) -> List[Any]:
    """Get transactions, using cache for past periods and API for current.
    
    Strategy:
    - For past periods (< current_period): Load from cache, fetch if not cached, then cache it
    - For current period: Always fetch from API (it changes frequently)
    
    Args:
        league: ESPN League object
        league_id: ESPN league ID
        current_period: Current scoring period
        
    Returns:
        List of all transactions (cached + current)
    """
    all_transactions = []
    
    # Always get current period from API (it changes frequently)
    try:
        current_trans = league.transactions()
        all_transactions.extend(current_trans)
    except Exception as e:
        print(f"Error fetching current transactions: {e}")
    
    # For past periods, use cache
    for period in range(max(1, current_period - 7), current_period):
        # Try to load from cache first
        cached_trans = load_transactions_from_cache(league_id, period)
        
        if cached_trans:
            # Found in cache, use it
            all_transactions.extend(cached_trans)
        else:
            # Not in cache, fetch from API
            try:
                trans = league.transactions(scoring_period=period)
                all_transactions.extend(trans)
                
                # Cache for future use
                save_transactions_to_cache(league_id, period, trans)
            except Exception as e:
                print(f"Error fetching transactions for period {period}: {e}")
    
    return all_transactions


def clear_transaction_cache() -> bool:
    """Clear all cached transactions.
    
    Returns:
        True if cleared successfully
    """
    try:
        import shutil
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error clearing transaction cache: {e}")
        return False
