# Complete Script Contents

This document shows the full content of both main scripts created for the ESPN Fantasy Basketball transaction scheduling system.

---

## Script 1: `scheduling/schedule_free_agent_add.py`

**Purpose:** Schedule a free agent transaction for a specific player on a specific date at 12:15 AM

**Location:** `scheduling/schedule_free_agent_add.py`

**Usage:**
```bash
python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025"
python3 scheduling/schedule_free_agent_add.py --player-id=5211175 --date="Dec 5 2025"
python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025" --team-id=3 --scoring-period-id=10
```

### Key Features:
- Parses flexible command-line arguments (positional or flag-based)
- Validates all inputs
- Finds the repository root automatically
- Locates the posting script
- Constructs and executes an `at` command to schedule the job
- Logs all actions to file and console
- Provides clear user feedback

### Key Functions:
- `parse_arguments()` - Parse command-line arguments
- `get_repo_root()` - Find the repository root directory
- `get_posting_script_path()` - Locate the posting script
- `schedule_with_at()` - Schedule the job using the `at` command
- `setup_logging()` - Configure logging
- `main()` - Entry point

---

## Script 2: `scheduling/post_free_agent_transaction.py`

**Purpose:** Send 45 POST requests to the ESPN Fantasy Basketball API (one per minute)

**Location:** `scheduling/post_free_agent_transaction.py`

**Usage:**
```bash
# Via environment variables (used by scheduler)
PLAYER_ID=5211175 python3 scheduling/post_free_agent_transaction.py

# Via command-line arguments
python3 scheduling/post_free_agent_transaction.py --player-id=5211175

# Mixed
PLAYER_ID=5211175 python3 scheduling/post_free_agent_transaction.py --team-id=3
```

### Key Features:
- Reads parameters from environment variables or command-line arguments
- Loads ESPN credentials from secure credential files
- Builds proper transaction payloads
- Sends 45 POST requests to ESPN API
- Includes proper authentication headers
- Logs all activity to file and console
- Comprehensive error handling

### Key Functions:
- `get_player_id()` - Get player ID from arguments or environment
- `get_team_id()` - Get team ID (default: 2)
- `get_scoring_period_id()` - Get scoring period ID (default: 45)
- `get_espn_credentials()` - Load credentials from files
- `build_transaction_payload()` - Build JSON payload
- `build_cookie_header()` - Build authentication header
- `post_transaction()` - Send the 45 POST requests
- `setup_logging()` - Configure logging
- `main()` - Entry point

---

## How They Work Together

```
┌─────────────────────────────────────────────────────────────┐
│ User runs:                                                  │
│ python3 scheduling/schedule_free_agent_add.py 5211175 ...   │
└─────────────────────────────────────────┬───────────────────┘
                                          │
                                          ▼
        ┌─────────────────────────────────────────────────────┐
        │ schedule_free_agent_add.py                          │
        │ ✓ Validates inputs                                  │
        │ ✓ Finds posting script                              │
        │ ✓ Constructs 'at' command                           │
        │ ✓ Schedules job for 12:15 AM                        │
        │ ✓ Logs the action                                   │
        └─────────────────────────────────────────────────────┘
                                          │
                                          ▼
        ┌─────────────────────────────────────────────────────┐
        │ At 12:15 AM on specified date:                      │
        │ 'at' daemon runs the posting script                 │
        └─────────────────────────────────────────────────────┘
                                          │
                                          ▼
        ┌─────────────────────────────────────────────────────┐
        │ post_free_agent_transaction.py                      │
        │ ✓ Reads PLAYER_ID from environment                  │
        │ ✓ Loads credentials from files                      │
        │ ✓ Sends 45 POST requests (one per minute)           │
        │ ✓ Logs all activity                                 │
        │ ✓ Completes after 45 minutes                        │
        └─────────────────────────────────────────────────────┘
                                          │
                                          ▼
        ┌─────────────────────────────────────────────────────┐
        │ Result:                                             │
        │ ✓ Transaction posted to ESPN                        │
        │ ✓ Activity logged for review                        │
        │ ✓ User can check logs to verify success             │
        └─────────────────────────────────────────────────────┘
```

---

## Parameter Flow

### When Scheduling:
```
User Input:
  player_id = 5211175
  date = "Dec 5 2025"
  team_id = 2 (default)
  scoring_period_id = 45 (default)
  │
  ▼
schedule_free_agent_add.py constructs:
  PLAYER_ID=5211175 TEAM_ID=2 SCORING_PERIOD_ID=45 python3 post_free_agent_transaction.py
  │
  ▼
at 12:15 AM Dec 5 2025 <<< "command above"
```

### When Posting:
```
Environment Variables:
  PLAYER_ID=5211175
  TEAM_ID=2
  SCORING_PERIOD_ID=45
  │
  ▼
post_free_agent_transaction.py reads from environment
  │
  ▼
Builds transaction payload with player_id=5211175
  │
  ▼
Sends 45 POST requests with:
  - Player ID in payload
  - Team ID in payload
  - Scoring Period ID in payload
  - ESPN credentials from credential files
```

---

## Credentials Handling

Both scripts use the existing credential loading mechanism:

```python
from common.io import get_file_content_from_crendential_folder

# In post_free_agent_transaction.py:
espn_s2 = get_file_content_from_crendential_folder('espn_s2.secret')
swid = get_file_content_from_crendential_folder('swid.secret')
```

This ensures:
- ✓ Credentials are never hard-coded
- ✓ Credentials are never stored in logs
- ✓ Credentials are loaded from secure files
- ✓ Consistent with existing codebase practices

---

## Logging

Both scripts log their actions:

### Scheduling Script Logs to: `logs/schedule_free_agent.log`
Example:
```
2025-12-04 22:30:45,123 - INFO - Scheduling FREEAGENT add: playerId=5211175 at 12:15 AM Dec 5 2025
2025-12-04 22:30:45,124 - INFO - Posting script: /Users/hcheng/src/fantasy_basketball_tools/scheduling/post_free_agent_transaction.py
2025-12-04 22:30:45,125 - INFO - Command to execute: cd /Users/hcheng/src/fantasy_basketball_tools && PLAYER_ID=5211175 TEAM_ID=2 SCORING_PERIOD_ID=45 python3 /Users/hcheng/src/fantasy_basketball_tools/scheduling/post_free_agent_transaction.py
2025-12-04 22:30:45,126 - INFO - Successfully scheduled job. Output: job 1 at Mon Dec  5 00:15:00 2025
```

### Posting Script Logs to: `logs/post_free_agent.log`
Example:
```
2025-12-05 00:15:00,100 - INFO - Starting transaction loop for playerId=5211175, teamId=2, scoringPeriodId=45
2025-12-05 00:15:01,101 - INFO - 2025-12-05T00:15:01.101234 - Request 1/45
2025-12-05 00:15:02,102 - INFO - Request 1/45 succeeded (HTTP 200)
2025-12-05 00:16:02,103 - INFO - 2025-12-05T00:16:02.103456 - Request 2/45
2025-12-05 00:16:03,104 - INFO - Request 2/45 succeeded (HTTP 200)
...
2025-12-05 00:59:00,500 - INFO - Transaction loop completed
```

---

## Error Handling

### Scheduling Script Error Examples:

**Missing player ID:**
```
Error: player_id is required
Usage:
  python3 schedule_free_agent_add.py <player_id> "<date>"
  ...
```

**Invalid date:**
```
Error: 'at' command failed: specification not valid
```

**Posting script not found:**
```
Configuration error: Posting script not found at: /path/to/script
```

### Posting Script Error Examples:

**Missing player ID:**
```
Argument error: PLAYER_ID must be provided via --player-id=<id> or PLAYER_ID environment variable
```

**Missing credentials:**
```
Configuration error: Failed to load ESPN credentials: ...
```

**API request failed:**
```
ERROR - Request 1/45 failed: Connection error: ...
```

---

## Integration with Existing Codebase

Both scripts integrate seamlessly with the existing codebase:

### Uses:
- `common.io.get_file_content_from_crendential_folder()` - Load credentials
- `common.io.find_root_folder()` - Find repository root (via internal logic)
- Standard Python libraries: `requests`, `logging`, `subprocess`, `os`, `sys`

### Follows:
- Existing project structure
- Existing credential handling patterns
- Existing logging practices
- Python best practices

### Compatible With:
- Existing test framework
- Existing CI/CD pipeline
- Existing deployment processes

---

## Performance

### Scheduling Operation:
- Time: < 1 second
- I/O: Minimal (reads credential files, writes log)
- Network: None
- Result: Job scheduled in `at` queue

### Posting Operation:
- Time: ~45 minutes (one request per minute)
- I/O: Logging to file
- Network: 45 HTTP POST requests to ESPN API
- Result: 45 transaction attempts logged

---

## Testing Coverage

All major functions have been tested:

✓ Argument parsing (positional and flag-based)
✓ Repository root detection from any directory
✓ Posting script path resolution
✓ Credential file loading
✓ Transaction payload generation
✓ Cookie header construction
✓ Environment variable reading
✓ Default parameter values
✓ Logging to file and console
✓ Error handling for missing arguments
✓ Error handling for missing files
✓ Error handling for invalid inputs

---

## Future Enhancements

Possible improvements (not implemented, but straightforward to add):

1. **Support for other transaction types:**
   - TRADE transactions
   - DROP transactions
   - Multi-player transactions

2. **Enhanced error handling:**
   - Automatic retry logic for failed requests
   - Exponential backoff for rate limiting
   - Better error reporting

3. **User notifications:**
   - Email when transaction completes
   - Slack notifications
   - Web dashboard

4. **Transaction tracking:**
   - Database to store scheduled transactions
   - History of executed transactions
   - Success/failure metrics

5. **Advanced scheduling:**
   - Multiple transactions in single command
   - Recurring transactions
   - Transaction dependencies

---

## Security Considerations

✓ **No hard-coded credentials** - Loaded from files
✓ **No credential logging** - Never printed or stored
✓ **Environment variable isolation** - Parameters passed securely
✓ **File permissions** - Credential files should be 600
✓ **Audit trail** - All actions logged for review
✓ **Input validation** - All user inputs validated
✓ **Error messages** - Safe, non-revealing error messages

---

## Deployment Checklist

Before running in production:

- [ ] Credential files exist and are readable
- [ ] Credential files have proper permissions (600)
- [ ] `at` service is installed and running
- [ ] Python 3.7+ is available
- [ ] `requests` library is installed
- [ ] Logging directory is writable
- [ ] Firewall allows outbound connections to ESPN API
- [ ] System time is accurate (important for scheduling)

---

## Support and Troubleshooting

See:
- `scheduling/README.md` - Comprehensive guide
- `scheduling/QUICKSTART.md` - Quick start
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- Log files in `logs/` directory

