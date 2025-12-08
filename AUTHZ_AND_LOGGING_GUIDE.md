# Authorization (AuthZ) and Logging Implementation Guide

## Overview

Your Fantasy Basketball Service now has a complete authorization (authZ) and logging system that allows you to:

1. **Track API usage** - See which friends are using their keys and how often
2. **Manage API tiers** - Control what endpoints different keys can access
3. **Audit requests** - Complete request/response logging with tier information
4. **Scale safely** - Gate new endpoints to higher tiers before rolling out to everyone

## Key Features

### Authorization (authZ) System

#### API Tiers

Your service now supports three API tiers with different permission levels:

| Tier | Access | Use Case |
|------|--------|----------|
| **BASIC** | All original endpoints | Given to friends with existing keys |
| **PREMIUM** | BASIC + future premium features | Reserved for advanced users |
| **ENTERPRISE** | All endpoints (wildcard) | Full access for yourself |

#### Current Endpoint Access

All existing keys are set to **BASIC** tier with access to:

```
GET  /
GET  /api/v1/health
GET  /privacy
POST /api/v1/predictions/calculate
POST /api/v1/predictions/week-analysis
POST /api/v1/scout/players
GET  /api/v1/scout/teams
POST /api/v1/team/{team_id}
POST /api/v1/team/{team_id}/roster
POST /api/v1/players-playing/{scoring_period}
POST /api/v1/scoreboard/{week_index}
```

### Request Logging

Every API request is logged with the following information:

#### Log Format (api_requests.log)

```
2024-01-15 14:32:45 | POST | /api/v1/predictions/calculate | 200 | chatgpt_integration | basic | 245.32ms
```

Fields:
- **Timestamp** - When the request was made
- **Method** - HTTP method (GET, POST, etc.)
- **Path** - API endpoint path
- **Status** - HTTP response code
- **Key Name** - Human-readable key name (NOT the actual key)
- **Tier** - API tier of the key
- **Response Time** - How long the request took in milliseconds

#### JSON Log (api_usage.json)

Detailed JSON log for analytics:

```json
{
  "timestamp": "2024-01-15T14:32:45.123456",
  "method": "POST",
  "path": "/api/v1/predictions/calculate",
  "endpoint": "/api/v1/predictions/calculate",
  "status_code": 200,
  "key_name": "chatgpt_integration",
  "tier": "basic",
  "response_time_ms": 245.32,
  "user_agent": "Python-Requests/2.31.0",
  "ip_address": "192.168.1.1",
  "error": null
}
```

## File Structure

### New Files Created

```
auth/
├── authz.py                    # Authorization system with tiers
├── request_logger.py           # Request logging infrastructure
└── migrate_keys_to_tiers.py   # Migration script for existing keys

tests/
└── test_authz_and_logging.py  # 16 comprehensive tests
```

### Modified Files

```
auth/
├── api_key.py                 # Added tier and description fields
└── decorators.py              # Added authZ checks and logging
```

### Log Files (created at runtime)

```
logs/
├── api_requests.log          # Human-readable request log
└── api_usage.json            # JSON format for analytics
```

## Usage Guide

### Monitoring Friend Usage

#### View All Keys by Tier

```bash
python3 auth/migrate_keys_to_tiers.py list
```

Output:
```
🔑 BASIC Tier (4 keys):
   • test_team_endpoint ✅ active
     fba_FjX_wz...OpD4i8cnkY
   • chatgpt_integration ✅ active
     fba_n1o8Lo...HTBx8KJWIw
   [...]

🔑 PREMIUM Tier (0 keys):
   (no keys)

🔑 ENTERPRISE Tier (0 keys):
   (no keys)
```

#### View Request Logs

```bash
# Real-time monitoring
tail -f logs/api_requests.log

# See last 20 requests
tail -20 logs/api_requests.log

# Filter by key
grep "chatgpt_integration" logs/api_requests.log

# Count requests by key
cat logs/api_requests.log | awk '{print $NF}' | sort | uniq -c
```

#### View Detailed Usage Analytics

```python
from auth.request_logger import get_usage_summary

# Get overall statistics
stats = get_usage_summary()
print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['successful_requests']}/{stats['total_requests']}")
print(f"Requests by key: {stats['by_key']}")
print(f"Requests by tier: {stats['by_tier']}")
```

### Managing API Keys

#### Create a New Key

```python
from auth.api_key import get_api_key_manager

manager = get_api_key_manager()

# Create a basic tier key (default)
key = manager.generate_key(
    name="Friend A",
    tier="basic",
    description="For testing week predictions",
    rate_limit=100  # requests per hour
)
print(key)  # fba_...
```

#### Change a Key's Tier

```python
from auth.api_key import get_api_key_manager

manager = get_api_key_manager()

# Get the existing key
existing_key = "fba_..."  # the actual key

# Modify tier (note: you'll need to update the JSON manually or add a method)
key_info = manager.get_key_info(existing_key)
key_info.tier = "premium"
manager._save_keys()
```

#### Revoke a Key

```python
manager.revoke_key(existing_key)
```

### Adding New Premium Endpoints

When you want to add a new premium feature:

1. **Update authz.py** to add the endpoint to PREMIUM tier:

```python
TIER_PERMISSIONS = {
    APITier.BASIC: {
        # ... existing endpoints ...
    },
    APITier.PREMIUM: {
        # ... existing PREMIUM endpoints ...
        "POST /api/v1/new/premium/feature",
    },
    # ...
}
```

2. **Create the endpoint** in `app.py` with `@require_api_key` decorator

3. **Existing BASIC keys cannot access it** - they'll get a 403 error

4. **Upgrade a friend's key** to PREMIUM if they need it

## Security Features

### Key Security

✅ **API keys are NEVER logged**
- Only the human-readable key name is logged
- Actual keys are kept secret
- Even in error logs, keys are never exposed

✅ **Rate Limiting**
- Each key has a configurable rate limit (default: 100 requests/hour)
- Enforced at the decorator level
- Returns 429 Too Many Requests when exceeded

✅ **Tier-Based Access Control**
- Keys can only access endpoints for their tier
- Returns 403 Forbidden if tier insufficient
- Logged for audit trail

### Log Security

⚠️ **Logs contain IP addresses and User-Agent headers**
- Keep log files private
- Consider rotating logs regularly
- Don't commit logs to version control

✅ **Logs are JSON-parseable**
- Easy to analyze with Python, jq, or other tools
- Can be sent to analytics platforms

## Testing

### Run All AuthZ Tests

```bash
python3 -m pytest tests/test_authz_and_logging.py -v
```

### Run Specific Test

```bash
python3 -m pytest tests/test_authz_and_logging.py::TestAuthorizationSystem -v
```

## Configuration

### Environment Variables

```bash
# Change API keys file location (optional)
export API_KEYS_FILE=".api_keys.json"

# Change log directory (optional)
export LOG_DIR="./logs"

# Enable debug logging to console
export FLASK_DEBUG=true
```

## Troubleshooting

### "Rate limit exceeded" Error

**Problem**: Friend can't make requests
**Solution**: Check `logs/api_usage.json` to see their request count this hour. Rate limits reset hourly.

### "Access denied - insufficient tier" Error

**Problem**: Friend tries to access endpoint they don't have permission for
**Solution**: Upgrade their key's tier using the key management methods above.

### Missing Logs

**Problem**: No `logs/api_requests.log` file created
**Solution**: Make sure your Flask app is running and at least one authenticated request has been made. Logs are created on first use.

### JSON Parsing Error in api_usage.json

**Problem**: File is corrupted or has invalid JSON
**Solution**: Each line should be valid JSON. If a line is corrupt, delete it and continue. Consider implementing log rotation.

## Best Practices

1. **Check logs regularly** to see which friends are actually using their keys
2. **Set appropriate rate limits** per key (higher for heavy users)
3. **Archive old logs** to avoid disk space issues
4. **Create audit trail** by reviewing JSON logs periodically
5. **Test new tier assignments** before rolling out to production
6. **Use descriptive key names** so you can easily identify who has which key
7. **Document your tier strategy** so you remember why keys have certain tiers

## Future Enhancements

Consider adding:

- Dashboard for visualization of API usage
- Email alerts when rate limits are exceeded
- Automated tier upgrades based on usage patterns
- Webhook notifications for suspicious activity
- Integration with analytics platforms (DataDog, etc.)
- Automatic log rotation and compression

## Next Steps

To activate this on your remote service:

```bash
git pull origin docker_dev
# Restart your Docker container
docker-compose restart  # or your restart command
```

The authZ system is now live and logging all requests!
