# ESPN Fantasy Basketball Transaction Scheduling

This module provides tools to schedule free agent transactions to be posted to the ESPN Fantasy Basketball API at a fixed time (12:15 AM) on a specified date.

## Overview

The module consists of two main scripts:

1. **`schedule_free_agent_add.py`** - The scheduling script that queues up a transaction using the `at` command
2. **`post_free_agent_transaction.py`** - The posting script that actually sends the transaction requests

## Components

### schedule_free_agent_add.py

This is the main entry point for scheduling a free agent transaction. It uses the Unix `at` command to schedule the posting script to run at 12:15 AM on a specified date.

**Usage:**

```bash
# Using positional arguments
python3 scheduling/schedule_free_agent_add.py <player_id> "<date>"

# Using flag-based arguments
python3 scheduling/schedule_free_agent_add.py --player-id=<id> --date="<date>"
```

**Examples:**

```bash
# Schedule adding player 5211175 on Dec 5 2025
python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025"

# Schedule with custom team and scoring period
python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025" --team-id=3 --scoring-period-id=10

# Using flag-based syntax
python3 scheduling/schedule_free_agent_add.py --player-id=5211175 --date="Dec 5 2025" --team-id=2
```

**Arguments:**

- `player_id` (required): The ESPN player ID to add to the team
- `date` (required): The date to schedule the transaction (e.g., "Dec 5 2025"). Format should be acceptable to the `at` command
- `--team-id=<id>` (optional): The team ID to add the player to (default: 2)
- `--scoring-period-id=<id>` (optional): The scoring period ID (default: 45)

**Output:**

The script will:
- Validate all arguments
- Find the posting script location
- Schedule the job using the `at` command
- Print confirmation with scheduled job details
- Log all actions to `logs/schedule_free_agent.log`

### post_free_agent_transaction.py

This script actually sends the free agent transaction requests to the ESPN API. It's designed to be called by the scheduler (via environment variables) or manually for testing.

**Usage:**

```bash
# With environment variables
PLAYER_ID=5211175 python3 scheduling/post_free_agent_transaction.py

# With command-line arguments
python3 scheduling/post_free_agent_transaction.py --player-id=5211175

# With all custom parameters
PLAYER_ID=5211175 TEAM_ID=3 SCORING_PERIOD_ID=10 python3 scheduling/post_free_agent_transaction.py
```

**Parameters:**

The script accepts parameters via environment variables or command-line arguments:

- `PLAYER_ID` / `--player-id=<id>` (required): The player ID to add
- `TEAM_ID` / `--team-id=<id>` (optional): The team ID (default: 2)
- `SCORING_PERIOD_ID` / `--scoring-period-id=<id>` (optional): The scoring period ID (default: 45)

**Behavior:**

- Loads ESPN credentials from `credentials/espn_s2.secret` and `credentials/swid.secret`
- Sends POST requests to the ESPN Fantasy Basketball API
- Runs for 45 iterations, sending one request per minute
- Logs all activity to both console and `logs/post_free_agent.log`
- Uses the ESPN Fantasy Basketball transaction endpoint:
  - `https://lm-api-writes.fantasy.espn.com/apis/v3/games/fba/seasons/2026/segments/0/leagues/30695/transactions/`

## Credentials

Both scripts require ESPN credentials to be present in the `credentials/` folder:

- `credentials/espn_s2.secret` - Your ESPN S2 token
- `credentials/swid.secret` - Your SWID token

These credentials are read from files, not hard-coded, for security.

## Logging

Both scripts log their output to files in the `logs/` directory:

- `logs/schedule_free_agent.log` - Logs from the scheduling script
- `logs/post_free_agent.log` - Logs from the posting script

Check these logs to verify successful scheduling and execution.

## System Requirements

- Python 3.7+
- The `at` command must be available on your system
  - On Ubuntu/Debian: `sudo apt-get install at`
  - On macOS: usually pre-installed
  - On Windows: use WSL (Windows Subsystem for Linux) or a similar solution

## How It Works

1. **User runs the scheduling script:**
   ```bash
   python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025"
   ```

2. **The scheduling script:**
   - Validates the player ID and date
   - Locates the posting script
   - Uses the `at` command to schedule a job for 12:15 AM on Dec 5 2025
   - The job will run: `cd /path/to/repo && PLAYER_ID=5211175 python3 scheduling/post_free_agent_transaction.py`

3. **At the scheduled time (12:15 AM on Dec 5 2025):**
   - The `at` daemon executes the scheduled command
   - The posting script starts and reads the `PLAYER_ID` from the environment
   - The script makes 45 POST requests to the ESPN API, one per minute
   - Each request includes the specified player ID in the transaction payload

## Example Workflow

```bash
# Schedule a transaction for player 5211175 on Dec 5 2025
python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025"

# Output:
# 2025-12-04 22:30:45,123 - INFO - Scheduling FREEAGENT add: playerId=5211175 at 12:15 AM Dec 5 2025
# 2025-12-04 22:30:45,124 - INFO - Posting script: /Users/hcheng/src/fantasy_basketball_tools/scheduling/post_free_agent_transaction.py
#
# ✓ Successfully scheduled transaction
#   Player ID: 5211175
#   Date: Dec 5 2025
#   Time: 12:15 AM (fixed)
#   Team ID: 2
#   Scoring Period ID: 45
#
# Schedule output: job 1 at Mon Dec  5 00:15:00 2025

# Check scheduled jobs
atq

# View a specific job
at -c 1

# Remove a scheduled job
atrm 1
```

## Troubleshooting

### "Cannot find fantasy_basketball_tools in the current path hierarchy"

The scripts need to find the repository root. Make sure:
- The repository is named `fantasy_basketball_tools`
- You're running the scripts from within the repository structure
- The directory hierarchy is intact

### "Posting script not found at: ..."

Make sure the `scheduling/post_free_agent_transaction.py` file exists and is in the correct location.

### "'at' command failed: ..."

The `at` command might not be running or available:
- Check that the `at` service is installed and running
- On some systems, you may need to enable it: `sudo systemctl enable atd && sudo systemctl start atd`

### "Failed to load ESPN credentials"

Make sure both credential files exist and are readable:
- `credentials/espn_s2.secret`
- `credentials/swid.secret`

These files should contain your ESPN credentials (obtained from your browser cookies).

## Advanced Usage

### Scheduling Multiple Transactions

You can schedule multiple transactions for different dates and players:

```bash
python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025"
python3 scheduling/schedule_free_agent_add.py 1234567 "Dec 10 2025"
python3 scheduling/schedule_free_agent_add.py 9876543 "Dec 15 2025"
```

Each will be scheduled independently via the `at` command.

### Custom Team and Scoring Period

To schedule a transaction for a different team or scoring period:

```bash
python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025" --team-id=3 --scoring-period-id=10
```

### Running the Posting Script Manually

You can also run the posting script directly for testing:

```bash
# Test with default parameters
PLAYER_ID=5211175 python3 scheduling/post_free_agent_transaction.py

# This will send 45 requests (one per minute) immediately
```

## Integration with Existing Code

The scripts use the existing utility functions from the repository:

- `common.io.get_file_content_from_crendential_folder()` - To load credentials
- `common.io.find_root_folder()` - To locate the repository root

This ensures consistency with how the rest of the codebase handles file paths and credentials.

## Security Notes

- Credentials are never hard-coded; they're read from secure credential files
- The scripts use the `requests` library with proper headers
- Sensitive information (credentials, tokens) is not printed to logs
- The `at` command is used for secure scheduling (job runs with user's permissions)

## Future Enhancements

Possible improvements:

- Support for multiple transaction types (not just FREEAGENT ADD)
- Support for DROP and TRADE transactions
- Better error handling and retry logic for failed requests
- Notification when transactions complete
- Web UI for scheduling transactions
- Database to track scheduled and executed transactions
