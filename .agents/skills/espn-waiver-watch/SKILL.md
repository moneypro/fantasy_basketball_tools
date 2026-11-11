---
name: espn-waiver-watch
description: Watch an ESPN basketball waiver player during an authorized overnight window and execute a specified paired replacement only after free-agent clearance. Stop if owned, expired, or rejected; preserve the prior day's lineup and activate the pickup. Does not submit waiver claims.
---

# Waiver-clearance watch

Keep this skill local to `/home/hong/fantasy_basketball_tools/.agents/skills`. The user reserves waiver priority for potential long-term holds and prefers disposable streams from free agency. A listed waiver time is not proof of actual clearance.

Use `scripts/waiver_watch.py` for a newly authorized exact pair and dated window. Reuse the ESPN add/drop and roster-rollover helpers; do not rerun historical watches or the hardcoded Reed script. Credentials stay in the existing `.env`.

Before scheduling, refresh league identity, player ownership, the listed waiver time in America/Los_Angeles, target-day game and legal active slot, current/effective periods, acquisition budget, and conflicting jobs. Research alone does not authorize a watch. Authorization for the specific pair/window includes minimal target-day activation; no separate confirmation is needed.

Create a unique directory under `output/` with `config.json`. Required keys: `authorized` (true), integer `season`, `league`, `team`, `addId`, `dropId`, `protectedPeriod`, `targetPeriod` (protected + 1), and ISO timezone-aware `start` and `end`. The window may be up to two hours. Resolve all values freshly; the usual midnight–2 a.m. Pacific window is not standing authorization for future nights.

Preview with:

```sh
python3 .agents/skills/espn-waiver-watch/scripts/waiver_watch.py --config /absolute/config.json --preview
```

Preview is read-only and does not persist execution status. Before midnight it can report `waiting_for_free_agent` using current ownership. Install a systemd user oneshot service with an absolute runner/config path, working directory at the project root, and a bounded timer checking once per minute. Include a final tick at the end to record expiry. Use `AccuracySec=1s`, no randomized delay, and `Persistent=true`; the runner refuses late acquisitions. Verify enabled/active state, next trigger, and a manual service check returning `waiting_for_window`. The machine must remain awake and online. Report the exact cancellation command and status path.

The runner stops if anyone owns the target (regardless of whether acquired via waiver or free agency), the drop is no longer rostered, the window expires, the target is ruled out, or preflight rejects. It waits while unowned and WAIVERS. It never changes the target, submits a claim, or drops separately. An exclusive transaction journal gates one paired request; after a timeout/restart it only reconciles that request. Definitive rejection ends the job. Read failures can retry within the window.

When the user explicitly prioritizes an already-submitted ESPN waiver claim over this fallback, an optional `priorityClaim` object may contain `transactionId`, `addId`, `activationPeriod`, and an absolute `directory` holding that claim's `protected-roster.json`. Verify the exact pending claim independently before configuring it. The watcher waits while the claim is pending or evidence is missing/unknown. A verified EXECUTED claim with matching ownership activates that primary pickup for the specified period and ends the fallback. Only a definitive nonpending FAILED, REJECTED, or CANCELED claim permits the original free-agent pair to proceed. The watcher does not submit or cancel waiver claims. Preserve the existing bounded watch window unless the user authorizes another one.

After acquisition it verifies ownership and the previous day's full roster/slots, then minimally activates the pickup on the target date. It never benches another useful starter to force activation. `verified_completed` means acquisition, protected roster, and activation were verified; distinguish acquired-but-unverified outcomes. Terminal ticks make no further ESPN calls.

Validate changes with `python3 -m unittest discover -s tests -p test_waiver_watch.py`, the shared add/drop and rollover tests, and the skill-creator validator. Test live scheduling through GET-only previews; never submit a live acquisition as a test.
