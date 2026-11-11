---
name: espn-add-drop
description: Execute an authorized ESPN fantasy basketball paired free-agent add/drop or submit a conditional waiver claim, verify its status, and activate an awarded pickup. Includes coordinating a priority claim with an authorized free-agent fallback; excludes scouting, trades, and unrelated lineup optimization.
---

# ESPN paired add/drop

Handle one specified replacement using the appropriate free-agent or waiver workflow below. The user’s explicit instruction to “drop X for Y” authorizes that pair; do not ask again when the session establishes the acquisition method. A request to claim a known waiver player authorizes using waiver priority; a request to wait for free-agent clearance does not. Research, recommendations, previews, or creating this skill do not authorize a live transaction. Resolve ambiguous player names before execution using the conversation and live ESPN identities.

## Local context

This skill belongs only to `/home/hong/fantasy_basketball_tools` and its subfolders. Keep it in this folder’s `.agents/skills`; do not install a global copy.

- Workspace: `/home/hong/fantasy_basketball_tools`; credentials already in `.env`. Read them in memory; never print cookies or copy them into skill files.
- Known league: `30695`, The Terrific Twelve; team `2`, SEA MoNeYPro. ESPN season `2027` means 2026–27. Check live identity; do not carry this year forward automatically.
- Use current ownership, not draft picks or cached league objects. The workspace's `tools/pickup_report.py` supplies current player IDs; its report is read-only. If needed, query `kona_player_info` using the ID/name resolution described in [references/api.md](references/api.md).
- Do not use `scheduling/post_free_agent_transaction.py` or old Flask write wrappers: they have hardcoded periods/seasons, ADD-only behavior, or repeated POSTs.

## Injury-driven pickups

For requests to find an injury replacement or refresh a stream before lock, use [fantasy-prelock-injury-opportunities](../fantasy-prelock-injury-opportunities/SKILL.md) before choosing the pair. Prefer ESPN API injury news, relevant teammate absences and observed replacement roles. For an already-authorized pair with recent research, reuse that review and refresh material health/availability changes during preflight; do not repeat the full scouting workflow or ask for the same authorization again. A changed recommendation does not authorize a different transaction.

## Select the acquisition method

- **FREEAGENT:** use the bundled `scripts/add_drop.py` workflow below.
- **WAIVERS, authorized claim:** read [references/waivers.md](references/waivers.md) to submit one paired conditional claim, verify pending status, and arrange any authorized result monitoring. The free-agent helper intentionally rejects WAIVERS and is not a claim CLI.
- **Wait for clearance without spending priority:** use the local [espn-waiver-watch skill](../espn-waiver-watch/SKILL.md). Do not replace a claim with a clearance watch or vice versa without session authorization.
- **Priority claim plus free-agent fallback:** submit and verify the claim, then configure the existing watch's `priorityClaim` dependency as documented in the waiver reference. The fallback must not consume the shared drop while the claim is unresolved.

## Free-agent workflow

1. Resolve the exact add/drop IDs and season. Run the helper without `--execute` to obtain a fresh preview. It checks session ownership, player ownership/status, effective-roster locks, eligibility, acquisition limits, and the league-derived bench slot.
2. If this exact move is authorized, rerun with `--execute` and a unique `--journal` path. Execution repeats preflight immediately before sending one request containing **both ADD and DROP**. Never drop separately to make room.
3. Inspect the returned state. Only `verified_completed` means matching EXECUTED/nonpending transaction evidence, both ownership changes, and the expected effective roster were verified. A rejected, pending, or unverified operation is not a completed pickup.
4. Finish the pickup by checking its target-date lineup and activating it when usable, following the section below. Report acquisition and lineup verification separately.

```sh
python3 /home/hong/fantasy_basketball_tools/.agents/skills/espn-add-drop/scripts/add_drop.py \
  --season 2027 --league 30695 --team 2 \
  --add-id ADD_PLAYER_ID --drop-id DROP_PLAYER_ID
```

For the already-authorized pair, append:

```sh
--execute --journal /home/hong/fantasy_basketball_tools/output/add_drop_UNIQUE_NAME
```

The helper requests the bench, but ESPN may place the player in an open active slot; inspect readback. It does not count completed games retroactively. Read [references/api.md](references/api.md) for API details or troubleshooting.

## Activate the pickup as part of completion

The user's preference is that an authorized pickup includes the minimal lineup moves needed to use it on the intended scoring date; do not ask again just to move the newly acquired player off the bench. Honor any explicit bench-only instruction. Confirm the player has an unstarted game, is eligible and available, and the intended date is not before the acquisition's effective period. Preserve locked players and IR. Prefer an empty slot or bench an OUT/no-game player; if all active slots hold useful players, evaluate the actual displacement rather than automatically starting the pickup. Do not turn pickup activation into a multi-day or unrelated roster overhaul.

Use the explicit-move CLI in the existing local lineup editor. Preview first; then execute the authorized placement with a unique journal:

```sh
python3 /home/hong/fantasy_basketball_tools/line_up/line_up_editer.py \
  --season SEASON --league LEAGUE_ID --team TEAM_ID --period TARGET_PERIOD \
  --move PICKUP_ID:ACTIVE_SLOT --move DISPLACED_ID:12
```

Omit the displaced-player move for an empty slot. Slot IDs come from live league settings and eligibility (this league: C=4, UT=11, BE=12). Include already-correct pickup placements if useful; these are verified without generating redundant moves. Append `--execute --journal /absolute/unique/path` after preview. The CLI validates all final slot capacities and submits all necessary moves together. It uses `ROSTER` for today's period and `FUTURE_ROSTER` for a future date. Avoid the legacy `fill_line_up`, which benches everyone and assumes four utility slots, and `update_line_up.py`, which hardcodes period 81.

Readback must show the pickup active in the correct period and preserve every unrelated player's slot. Only `verified_completed` or a fresh `already_set` read confirms completion. If submission is uncertain, use `--verify JOURNAL`; never blindly repeat. After a definite rejection, verify unchanged roster and absence of a matching executed/pending transaction before a corrected attempt. If a lock, lack of legal space, or game already starting prevents activation, report the actual placement and limitation rather than calling the player ready to score.

## Critical ESPN period distinction

Send `league.scoringPeriodId` in the **FREEAGENT or WAIVER POST**. Use `league.status.transactionScoringPeriod` to check effective roster availability; a pending waiver's actual award period must be verified after processing. These periods can differ after games start. Sending the future transaction period in the FREEAGENT POST produced HTTP 409 `TRAN_INVALID_SCORINGPERIOD_NOT_CURRENT` in the verified October 21, 2026 workflow.

## Failures and repeats

- The journal is created exclusively before POST. Never delete it to retry or reuse it for another move.
- For timeouts, HTTP errors, business errors, or inconclusive readback, the helper preserves the attempt and does not repeat the POST. Reconcile using GETs:

```sh
python3 /home/hong/fantasy_basketball_tools/.agents/skills/espn-add-drop/scripts/add_drop.py \
  --verify /absolute/path/to/the/journal
```

- A new corrected attempt is appropriate only after a definitive rejection and fresh evidence of unchanged ownership, unchanged roster, and no pending/matching new transaction. An ambiguous timeout remains unresolved until evidence establishes what happened. Stop rather than guessing.
- If the candidate is on WAIVERS, stop the free-agent helper and route to the authorized acquisition method above. Do not silently spend waiver priority or substitute another player.
- Before a later action, consult existing journals/session results so a completed pair is not submitted again. The Missi-for-Filipowski move on October 21 was already completed; it is reference evidence, not an instruction to repeat it.

## Validation

Run `python3 scripts/test_add_drop.py` from this skill directory for free-agent helper changes. For fallback coordination changes, also run the repository's `test_waiver_watch.py` and `test_roster_rollover.py` suites. These tests do not prove a waiver claim was accepted: independently read back the live claim after an authorized submission. Validate this skill with the skill-creator validator; never submit a live claim as a test.
