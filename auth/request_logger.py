"""Request logging for API usage tracking."""

import os
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Configure logging directory
LOG_DIR = Path(os.getenv('LOG_DIR', './logs'))
LOG_DIR.mkdir(exist_ok=True)

# Create request logger
REQUEST_LOG_FILE = LOG_DIR / 'api_requests.log'
USAGE_LOG_FILE = LOG_DIR / 'api_usage.json'

# Set up request logger
request_logger = logging.getLogger('api_requests')
request_logger.setLevel(logging.INFO)

# File handler for requests
handler = logging.FileHandler(REQUEST_LOG_FILE)
handler.setLevel(logging.INFO)

# Formatter: timestamp | method | path | status | key_name | tier
formatter = logging.Formatter(
    '%(asctime)s | %(method)s | %(path)s | %(status)s | %(key_name)s | %(tier)s | %(response_time)sms',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
request_logger.addHandler(handler)

# Also log to console in debug mode
if os.getenv('FLASK_DEBUG', 'False').lower() == 'true':
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    request_logger.addHandler(console_handler)


def log_request(
    method: str,
    path: str,
    status_code: int,
    key_name: str,
    tier: str,
    response_time_ms: float,
    error_message: Optional[str] = None
):
    """Log an API request with usage information.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: Response status code
        key_name: Human-readable name of the API key (NOT the key itself)
        tier: API tier (basic, premium, enterprise)
        response_time_ms: Response time in milliseconds
        error_message: Optional error message if request failed
    """
    extra = {
        'method': method,
        'path': path,
        'status': status_code,
        'key_name': key_name,
        'tier': tier,
        'response_time': f"{response_time_ms:.2f}"
    }
    
    if status_code < 400:
        request_logger.info(f"Success", extra=extra)
    elif status_code < 500:
        request_logger.warning(f"Client error: {error_message}", extra=extra)
    else:
        request_logger.error(f"Server error: {error_message}", extra=extra)


def log_request_to_json(
    method: str,
    path: str,
    status_code: int,
    key_name: str,
    tier: str,
    response_time_ms: float,
    endpoint: Optional[str] = None,
    error_message: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """Log request to JSON file for analytics/auditing.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        key_name: API key name (NOT the key itself)
        tier: API tier
        response_time_ms: Response time in milliseconds
        endpoint: Matched endpoint pattern
        error_message: Optional error message
        user_agent: User-Agent header
        ip_address: Client IP address
    """
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": method,
            "path": path,
            "endpoint": endpoint,
            "status_code": status_code,
            "key_name": key_name,
            "tier": tier,
            "response_time_ms": response_time_ms,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "error": error_message,
        }
        
        # Append to JSON lines file
        with open(USAGE_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        request_logger.error(f"Failed to write JSON log: {e}")


def get_recent_requests(limit: int = 50, key_name: Optional[str] = None) -> list:
    """Get recent API requests from logs.
    
    Args:
        limit: Number of recent requests to return (default: 50)
        key_name: Filter by key name (optional)
    
    Returns:
        List of recent request entries
    """
    try:
        if not REQUEST_LOG_FILE.exists():
            return []
        
        requests_list = []
        
        with open(REQUEST_LOG_FILE, 'r') as f:
            # Read all lines
            lines = f.readlines()
            
            # Take the last `limit` lines
            for line in lines[-limit:]:
                try:
                    # Parse the log line
                    # Format: timestamp | method | path | status | key_name | tier | response_time
                    parts = line.strip().split(' | ')
                    if len(parts) >= 7:
                        entry = {
                            'timestamp': parts[0],
                            'method': parts[1],
                            'path': parts[2],
                            'status': parts[3],
                            'key_name': parts[4],
                            'tier': parts[5],
                            'response_time': parts[6]
                        }
                        
                        # Filter by key_name if specified
                        if key_name and entry['key_name'] != key_name:
                            continue
                        
                        requests_list.append(entry)
                except Exception:
                    continue
        
        return requests_list
    except Exception as e:
        return [{"error": f"Failed to read logs: {e}"}]


def get_usage_summary(key_name: Optional[str] = None) -> Dict[str, Any]:
    """Get usage summary from logs.
    
    Args:
        key_name: Filter by key name (optional)
    
    Returns:
        Dictionary with usage statistics
    """
    try:
        if not USAGE_LOG_FILE.exists():
            return {"error": "No usage data available"}
        
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        by_key = {}
        by_tier = {}
        by_endpoint = {}
        
        with open(USAGE_LOG_FILE, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    
                    # Filter by key name if specified
                    if key_name and entry.get('key_name') != key_name:
                        continue
                    
                    total_requests += 1
                    
                    # Status tracking
                    if entry.get('status_code', 500) < 400:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                    
                    # By key
                    kn = entry.get('key_name', 'unknown')
                    if kn not in by_key:
                        by_key[kn] = {'count': 0, 'tier': entry.get('tier')}
                    by_key[kn]['count'] += 1
                    
                    # By tier
                    tier = entry.get('tier', 'unknown')
                    by_tier[tier] = by_tier.get(tier, 0) + 1
                    
                    # By endpoint
                    endpoint = entry.get('endpoint', 'unknown')
                    by_endpoint[endpoint] = by_endpoint.get(endpoint, 0) + 1
                
                except json.JSONDecodeError:
                    continue
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "by_key": by_key,
            "by_tier": by_tier,
            "by_endpoint": by_endpoint,
        }
    except Exception as e:
        return {"error": f"Failed to read usage data: {e}"}
