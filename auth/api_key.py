"""API Key management and authentication."""
import os
import secrets
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import json

API_KEYS_FILE = os.getenv('API_KEYS_FILE', '.api_keys.json')


@dataclass
class APIKeyInfo:
    """Information about an API key."""
    key: str
    name: str
    created_at: str
    last_used: Optional[str] = None
    active: bool = True
    rate_limit: int = 100  # requests per hour
    requests_this_hour: int = 0
    

class APIKeyManager:
    """Manage API keys for authentication."""
    
    def __init__(self, keys_file: str = API_KEYS_FILE):
        """Initialize API key manager.
        
        Args:
            keys_file: Path to JSON file storing API keys
        """
        self.keys_file = keys_file
        self.keys: Dict[str, APIKeyInfo] = {}
        self._load_keys()
    
    def _load_keys(self):
        """Load API keys from file."""
        if os.path.exists(self.keys_file):
            try:
                with open(self.keys_file, 'r') as f:
                    data = json.load(f)
                    self.keys = {
                        k: APIKeyInfo(**v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"Warning: Could not load API keys: {e}")
                self.keys = {}
    
    def _save_keys(self):
        """Save API keys to file."""
        try:
            with open(self.keys_file, 'w') as f:
                data = {k: asdict(v) for k, v in self.keys.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save API keys: {e}")
    
    def generate_key(self, name: str, rate_limit: int = 100) -> str:
        """Generate a new API key.
        
        Args:
            name: Human-readable name for the key
            rate_limit: Requests per hour allowed (default: 100)
            
        Returns:
            New API key
        """
        # Generate key in format: fba_<random_32_chars>
        key = f"fba_{secrets.token_urlsafe(32)}"
        
        key_info = APIKeyInfo(
            key=key,
            name=name,
            created_at=datetime.utcnow().isoformat(),
            rate_limit=rate_limit
        )
        
        self.keys[key] = key_info
        self._save_keys()
        
        print(f"✅ Generated API key for '{name}':")
        print(f"   {key}")
        print(f"   Rate limit: {rate_limit} requests/hour")
        
        return key
    
    def verify_key(self, key: str) -> bool:
        """Verify if an API key is valid.
        
        Args:
            key: API key to verify
            
        Returns:
            True if key is valid and active
        """
        if key not in self.keys:
            return False
        
        key_info = self.keys[key]
        return key_info.active
    
    def get_key_info(self, key: str) -> Optional[APIKeyInfo]:
        """Get information about an API key.
        
        Args:
            key: API key
            
        Returns:
            APIKeyInfo or None if key doesn't exist
        """
        return self.keys.get(key)
    
    def revoke_key(self, key: str) -> bool:
        """Revoke an API key.
        
        Args:
            key: API key to revoke
            
        Returns:
            True if successfully revoked
        """
        if key in self.keys:
            self.keys[key].active = False
            self._save_keys()
            return True
        return False
    
    def check_rate_limit(self, key: str) -> bool:
        """Check if API key has exceeded rate limit.
        
        Args:
            key: API key
            
        Returns:
            True if within limit, False if exceeded
        """
        if key not in self.keys:
            return False
        
        key_info = self.keys[key]
        return key_info.requests_this_hour < key_info.rate_limit
    
    def increment_usage(self, key: str):
        """Increment usage counter for an API key.
        
        Args:
            key: API key
        """
        if key in self.keys:
            self.keys[key].requests_this_hour += 1
            self.keys[key].last_used = datetime.utcnow().isoformat()
            self._save_keys()
    
    def list_keys(self) -> Dict[str, Dict[str, Any]]:
        """List all API keys (without exposing full keys).
        
        Returns:
            Dictionary of API keys with info (keys truncated)
        """
        result = {}
        for key, info in self.keys.items():
            truncated = f"{key[:10]}...{key[-10:]}"
            result[truncated] = {
                'name': info.name,
                'created_at': info.created_at,
                'last_used': info.last_used,
                'active': info.active,
                'rate_limit': info.rate_limit
            }
        return result


# Global instance
_manager = None

def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager instance."""
    global _manager
    if _manager is None:
        _manager = APIKeyManager()
    return _manager
