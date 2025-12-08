"""Migrate existing API keys to include tier information.

This script updates existing API keys in .api_keys.json to include the new
tier and description fields. All existing keys are set to "basic" tier.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

API_KEYS_FILE = os.getenv('API_KEYS_FILE', '.api_keys.json')


def migrate_keys():
    """Migrate existing keys to include tier and description fields."""
    if not os.path.exists(API_KEYS_FILE):
        print(f"✅ No existing keys file found at {API_KEYS_FILE}")
        print("   New keys will automatically include tier information.")
        return
    
    # Load existing keys
    try:
        with open(API_KEYS_FILE, 'r') as f:
            keys_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading API keys file: {e}")
        return
    
    # Track changes
    migrated = 0
    
    # Migrate each key
    for key, info in keys_data.items():
        # Add tier if not present
        if 'tier' not in info:
            info['tier'] = 'basic'
            migrated += 1
        
        # Add description if not present
        if 'description' not in info:
            info['description'] = None
    
    # Save migrated keys
    try:
        with open(API_KEYS_FILE, 'w') as f:
            json.dump(keys_data, f, indent=2)
        print(f"✅ Successfully migrated {migrated} key(s) to include tier information")
        print(f"   All keys are set to 'basic' tier")
        print(f"   File: {API_KEYS_FILE}")
    except Exception as e:
        print(f"❌ Error saving migrated keys: {e}")


def list_keys_by_tier():
    """Display all keys grouped by tier."""
    if not os.path.exists(API_KEYS_FILE):
        print("No API keys file found")
        return
    
    try:
        with open(API_KEYS_FILE, 'r') as f:
            keys_data = json.load(f)
    except Exception as e:
        print(f"Error reading API keys file: {e}")
        return
    
    # Group by tier
    by_tier: Dict[str, list] = {}
    
    for key, info in keys_data.items():
        tier = info.get('tier', 'basic')
        if tier not in by_tier:
            by_tier[tier] = []
        
        by_tier[tier].append({
            'key': f"{key[:10]}...{key[-10:]}",
            'name': info.get('name'),
            'active': info.get('active', True),
            'created_at': info.get('created_at'),
            'description': info.get('description')
        })
    
    # Print by tier
    for tier in ['basic', 'premium', 'enterprise']:
        keys = by_tier.get(tier, [])
        print(f"\n🔑 {tier.upper()} Tier ({len(keys)} keys):")
        
        if not keys:
            print("   (no keys)")
            continue
        
        for key_info in keys:
            status = "✅ active" if key_info['active'] else "❌ revoked"
            print(f"   • {key_info['name']} {status}")
            print(f"     {key_info['key']}")
            if key_info['description']:
                print(f"     {key_info['description']}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        list_keys_by_tier()
    else:
        migrate_keys()
        list_keys_by_tier()
