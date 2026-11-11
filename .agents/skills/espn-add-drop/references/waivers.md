# Conditional waiver claims and free-agent fallbacks

Use this mode when the user authorizes a claim for a specified player with a specified conditional drop. The claim spends priority only if awarded under the league's rules. A pending claim is neither a completed acquisition nor an immediate drop. Research and skill maintenance do not authorize submitting or resubmitting claims.

## Prepare one claim

Reuse the authenticated `ESPN` client and sanitized journaling utilities in `scripts/add_drop.py`. Its `preflight`, `matching`, `execute`, and `verify` functions are FREEAGENT-specific: do not use them as waiver validators or disguise WAIVERS as FREEAGENT. There is currently no generic waiver command-line helper; construct a scoped one-shot runner using the checks below and the verified payload shape in [api.md](api.md#waiver-claim-submission).

Refresh with GETs:

- League/season/team identity, session ownership, active league and team transaction lock.
- Current scoring period, effective transaction period, actual matchup acquisition allowance, season limit, waiver rank and acquisition settings. The verified flow is traditional priority waivers without FAAB. If a different league requires a bid, obtain authorization for that amount rather than inventing one.
- Exact add/drop identities. Add must be unowned and WAIVERS; drop must be owned by the user, droppable, and present in the effective roster. Check effective-period roster/trade locks, lineup eligibility and roster capacity.
- `waiverProcessDate` in the user's timezone. Report weekday and calendar date; this is the scheduled processing time, not a guarantee of completion or free-agent availability.
- Existing pending claims and active jobs involving either player. Reuse/reconcile the existing exact claim instead of duplicating it. Never drop separately to make room.

Inspect the proposed paired payload before sending. Create a unique journal exclusively before the POST and save the sanitized plan, prior transaction IDs, effective roster, and any protected day's full roster/slots. Send once. Record the response even on error; an uncertain transport result must be reconciled by GET, not retried.

## Verify pending versus awarded

Read `mTransactions2` independently after submission. Match team, type WAIVER, exact ADD/DROP pair, and returned transaction ID or a new ID absent from the preflight snapshot. Ignore harmless source-slot normalization by ESPN.

- **Pending verified:** matching PENDING/`isPending=true` record, with ownership and roster unchanged. Report the claim as pending and retain the conditional drop until ESPN processes it.
- **Awarded:** matching EXECUTED/`isPending=false` record plus pickup ownership, drop removal from the user's roster, and the expected replacement in the actual effective roster. The dropped player may subsequently be owned elsewhere; verify the user's replacement rather than assuming permanent unowned status.
- **Failed/rejected/canceled:** inspect the definitive result and current roster. No successful acquisition occurred merely because the POST returned HTTP 200.
- **Missing/unknown/inconsistent:** preserve the journal and reconcile; do not call it a failure, submit again, or release a fallback that could invalidate a still-pending claim.

Once awarded, activate the pickup for its first intended usable game using the main skill's minimal-lineup workflow. The award date and first game date may differ. Verify preserved prior-day roster/slots when applicable. Never activate an unowned player or count pre-acquisition points.

ESPN processes an accepted claim server-side; it does not need this machine awake. Local result monitoring, lineup activation and free-agent fallback jobs do need the machine online. Only arrange recurring/overnight monitoring when the user has authorized it; otherwise report the pending claim and any activation still outstanding.

## Priority claim with an authorized fallback

For “claim A for X, but keep the free-agent watch for B,” treat B as the fallback using the same conditional drop X. Keep the existing authorized watch window unless the user changes it. Read [espn-waiver-watch](../../espn-waiver-watch/SKILL.md) for installation and verification.

After independently verifying A's claim, add this object to B's watcher config, using live IDs and absolute paths:

```json
{
  "priorityClaim": {
    "transactionId": "VERIFIED_ESPN_CLAIM_ID",
    "addId": 123,
    "activationPeriod": 9,
    "directory": "/absolute/path/to/unique/claim/journal"
  }
}
```

The directory must contain `protected-roster.json` for the watch config's `protectedPeriod`. Resolve `activationPeriod` from A's first intended game and legal availability; it can differ from B's `targetPeriod`. Update the config atomically, check competing jobs, then use a GET-only preview to verify the dependency and verify the timer remains enabled/active with the correct next trigger.

The watcher validates the referenced claim's team and exact pair. Pending, missing or unknown evidence waits. An EXECUTED claim with reconciled ownership activates A and ends the fallback. Only a definitive nonpending FAILED, REJECTED or CANCELED claim permits the original B-for-X free-agent workflow. B must actually be FREEAGENT; the watcher never submits a second waiver claim. An expired window ends local attempts without canceling the server-side primary claim.

Report the two states separately: **ESPN claim pending** and **local fallback enabled/waiting**. Disabling the local timer does not cancel the ESPN claim. A request to cancel the claim needs its own verified ESPN cancellation; do not imply the watcher does this.

## Verified example, not an instruction to repeat

On Oct. 26, 2026, one Diabaté-for-Pippen WAIVER request was accepted and independently read back pending under transaction `27e4a8a6-021d-4cfc-bbb7-6162727903a6`. The request used current period 7 while the effective roster was period 8; the roster remained unchanged. Evidence: `output/diabate_waiver_20261027/{plan,submission,readback}.json`. The existing Queta-for-Pippen free-agent watch was linked to that claim; Diabaté's intended activation was period 9 because he had no period-8 game. These are historical identities and dates, not reusable defaults. Do not rerun the historical `submit_claim.py --execute`.
