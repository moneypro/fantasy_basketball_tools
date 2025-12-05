# Quick Start Guide

## Setup

No additional setup is required! The scripts are ready to use if:

1. You have Python 3.7+ installed
2. You have the `at` command available (pre-installed on macOS, install with `sudo apt-get install at` on Linux)
3. Your ESPN credentials are in:
   - `credentials/espn_s2.secret`
   - `credentials/swid.secret`

## Schedule Your First Transaction

```bash
# From the repository root, run:
python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025"
```

That's it! The transaction will be scheduled for 12:15 AM on Dec 5 2025.

## Verify It Worked

Check the log file to confirm scheduling was successful:

```bash
cat logs/schedule_free_agent.log
```

Or check the scheduled jobs:

```bash
atq
```

## What Happens Next

At 12:15 AM on the scheduled date:
- The `at` daemon automatically runs the posting script
- The script sends 45 POST requests to ESPN (one per minute for 45 minutes)
- Each request attempts to add the player to your team
- All activity is logged to `logs/post_free_agent.log`

## Common Use Cases

### Add a different player on a different date

```bash
python3 scheduling/schedule_free_agent_add.py 9876543 "Dec 10 2025"
```

### Add a player to a different team

```bash
python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025" --team-id=3
```

### Schedule for a different scoring period

```bash
python3 scheduling/schedule_free_agent_add.py 5211175 "Dec 5 2025" --scoring-period-id=10
```

## Troubleshooting

**Q: How do I check if the transaction ran successfully?**

A: Check the log files:
```bash
tail logs/post_free_agent.log
```

**Q: How do I cancel a scheduled transaction?**

A: List and remove scheduled jobs:
```bash
atq                    # List all scheduled jobs
atrm <job_number>      # Remove job
```

**Q: Can I run the posting script manually for testing?**

A: Yes:
```bash
PLAYER_ID=5211175 python3 scheduling/post_free_agent_transaction.py
```

**Q: What if the `at` command is not available?**

A: On Linux systems, install it:
```bash
sudo apt-get install at
sudo systemctl enable atd
sudo systemctl start atd
```

## More Information

For detailed documentation, see [README.md](README.md)
