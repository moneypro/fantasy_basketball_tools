---
name: espn-roster-rollover
description: Plan next-day and next-week ESPN basketball pickups around the first-game roster lock, and schedule an explicitly authorized paired replacement on this machine after the effective roster date rolls over. Includes target-date activation and protected-day verification; excludes waiver claims and speculative unattended player selection.
---

# ESPN roster-rollover pickups

Use this local skill for requests such as “find a Monday pickup and add him at Sunday's first tip” or “keep tonight's points, replace the player for tomorrow.” Read `/home/hong/fantasy_basketball_tools/tools/FANTASY_ASSISTANT.md` for current preferences and transaction history. Never repeat a historical pair or reuse its journal.

## Distinguish the two locks

The user's league locks **roster membership at the minute the first NBA game starts**, while **individual lineup positions remain editable until each player's own game starts**. Verify the live league still reports `FIRSTGAME_SCORINGPERIOD` and `INDIVIDUAL_GAME`. A later-effective replacement may preserve the protected day's roster, but do not claim preserved points until that exact dated roster is read back. A bench player on the protected day does not earn points merely because membership was preserved.

Resolve dates in America/Los_Angeles, especially around midnight. Explicitly name the protected date, intended pickup date, first tip time, and the target's game time. “Sunday tip for Monday” does not mean “Monday tip for Tuesday.” Retrieve first tip from ESPN's live scoreboard; confirm game cancellation/time changes before installing the timer. At execution, `status.transactionScoringPeriod` must equal the intended next-day period, and `scoringPeriodId` must still be the protected period. A clock time alone is insufficient.

## Make the recommendation concrete

Use the local `fantasy-free-agent-research` skill for live ownership, broad available-pool review, teammate injuries, minutes and legal lineup fit. Compare target-day value and the full next matchup; use `tools/matchup_report.py` to establish actual matchup boundaries rather than assuming seven days. Count usable games and consider sparse days, IR returns and what the dropped player gives up. Give one preferred exact add/drop pair and meaningful alternatives. A rest-driven breakout does not establish a durable role.

Research and a proposed schedule do not authorize live actions. Obtain the exact pair and intended execution window from the user's instruction or confirmation before enabling a job. Do not ask again once that pair/window is authorized. An authorized pickup includes minimal target-date activation per the user's established preference; preserve unrelated useful starters. A saved suggestion is not an active timer.

## Acquisition limits at matchup rollover

Roster lock and acquisition accounting are separate. “Already used seven” is not proof of risk-free execution. Read the live transaction counters and acquisition limits. The bundled runner passes `rollover_target_period` to the shared add/drop preflight, which verifies the actual next-day effective period, maps it through the season's `chui_default` calendar and league matchup settings, and checks that target matchup's allowance. The usual add/drop preflight still checks the current matchup by default.

ESPN may still enforce the protected/current matchup's limit. The job is authorized to make **one paired FREEAGENT request** after the observed rollover; ESPN determines acceptance and which allowance is charged. It always sends the current scoring period in the FREEAGENT payload. If rejected, retain Post/the specified drop and stop; never split ADD and DROP, bypass limits with separate requests, or silently postpone the attempt until midnight. Read back actual acquisition counters after success. Report acceptance uncertainty when scheduling.

## Local runner and scheduling

Runner: `.agents/skills/espn-roster-rollover/scripts/rollover_pickup.py`, from the workspace root. It uses the existing `espn-add-drop` helper and `line_up/line_up_editer.py`; credentials remain in the existing `.env`, never in the job config or logs.

Create a unique directory under `output/` and a `config.json` with explicit values:

```json
{
  "authorized": true,
  "season": 2027,
  "league": 30695,
  "team": 2,
  "addId": 4066436,
  "dropId": 4593016,
  "protectedPeriod": 6,
  "targetPeriod": 7,
  "start": "2026-10-25T14:00:00-07:00",
  "end": "2026-10-25T14:15:00-07:00"
}
```

These IDs/dates describe the October 25 authorized Melton-for-Post job, not standing authorization for another run. Resolve fresh values for every future request.

Preview with `python3 .agents/skills/espn-roster-rollover/scripts/rollover_pickup.py --config /absolute/config.json --preview`. Before tip, `waiting_for_roster_rollover` is expected. Preview never submits or persists terminal execution state. Do not use a live POST as a test.

Use a local systemd user timer with an absolute command/config path, starting at first tip, `AccuracySec=1s`, no randomized delay, and minute checks for a bounded window (normally 15 minutes; runner maximum one hour). Enable user lingering if needed and authorized, or use an already-working persistent scheduler. `Persistent=true` supports a restart, while the runner refuses execution after expiry. Do not silently fall back to a long-running chat or temporary shell process. Confirm the timer is enabled, active/waiting, and its next trigger is correct. State that the machine must be awake and online. Report the status-file path and exact cancellation command.

## Execution and completion

- Before rollover: GET-only waiting; no early acquisition and no drop.
- After the intended rollover: refresh identity, ownership, free-agent status, health, locks, target allowance, and roster; snapshot the protected-day lineup. Stop if unavailable or ruled out; do not choose an alternate unattended.
- Create an exclusive transaction journal before one paired request. A crash, timeout or ambiguous response permits verification reads only, never another acquisition POST. A definitive rejection ends this job.
- After verified acquisition, compare every protected-day roster member/slot against the snapshot. Any change stops activation for review.
- Activate the pickup on the target date using an empty eligible slot or replacing an OUT/no-game starter. The runner journals one minimal lineup request and verifies it. It does not bench a useful starter or rebuild the whole lineup; if no suitable slot exists, report that activation needs review. Target-date injury reports can change after the job.
- Save actual acquisition counters and distinguish `verified_completed`, unavailable, rejected, expired, or acquired-but-lineup-unverified. Only verified acquisition plus protected roster plus active target placement counts as full completion. If the status is unclear, inspect transaction and lineup journals and use their read-only verification helpers; do not schedule a second job for the same pair.

The scheduled process stores `status.json`, `checks.jsonl`, `protected-roster.json`, `transaction/`, and, when required, `lineup/` beside the config. There is no external notification unless separately requested.

## Validation

Run `python3 -m unittest discover -s tests -p test_roster_rollover.py`, the add/drop helper's offline tests, and `tests/test_explicit_lineup.py` after relevant code changes. Verify the live preview and installed timer without sending the future transaction early.
