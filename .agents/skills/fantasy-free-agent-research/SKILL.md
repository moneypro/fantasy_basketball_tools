---
name: fantasy-free-agent-research
description: Research ESPN fantasy basketball pickups, weakest roster spots, weekend streams and longer holds using live availability, teammate injuries, minutes, opponent matchups and usable schedules. Read-only research; route authorized acquisitions to espn-add-drop.
---

# Fantasy free-agent research

Recommend additions and corresponding drops for the user's points league. Start with live ESPN APIs; external search is a fallback for material gaps or an explicit user request. Research does not authorize transactions or lineup changes.

## Local context and first reads

- Workspace: `/home/hong/fantasy_basketball_tools`. Keep this skill local under `.agents/skills`.
- Known league `30695`, team `2`, SEA MoNeYPro; timezone America/Los_Angeles. Season `2027` means 2026–27. Verify live identity and season rather than carrying these forward automatically.
- Read `tools/FANTASY_ASSISTANT.md` for preferences and recommendation/transaction history, and `tools/PICKUP_REPORT.md` for the collector. Current ownership supersedes historical notes; never rerun a historical transaction.
- Credentials already exist locally. Read in memory; never print or copy them into reports.

Run the existing read-only report with the live season and relevant drop ID:

```bash
python3 tools/pickup_report.py --season 2027 --team 2 --compare-drop PLAYER_ID
```

Collect league-wide teammate injury context alongside it:

```bash
python3 .agents/skills/fantasy-free-agent-research/scripts/injury_context.py --season 2027 --league 30695 --output output/RESEARCH_DIRECTORY/injury_context.json
```

Read [references/data-and-evaluation.md](references/data-and-evaluation.md) for source endpoints, role verification, model limitations and future team-ratings integration. The supplemental helper captures all NBA teams' ESPN injury flags, including players owned by other fantasy managers. It does not determine starters or award automatic minutes boosts.

For shortlisted players, run `python3 tools/streaming_profile.py --season SEASON PLAYER_ID [PLAYER_ID ...]`. Include the teammate-return critique alongside the opponent recap in the recommendation itself. The profile compares recent minutes and league FP by teammate participation and links dated reports. Distinguish an observed return, a possible return and an absence of unknown cause. Check the candidate's role in games the returning competitor actually played.

## Last-minute injury review

For same-day injury replacements or a pre-lock refresh, use [fantasy-prelock-injury-opportunities](../fantasy-prelock-injury-opportunities/SKILL.md). Scan significant absences across the slate using ESPN APIs first, then trace actual replacement minutes/usage and check live ownership. Web search supplements material gaps or an explicit search request. Do not limit the scan to a prior recommendation or top season projections.

## Research decisions

For longer-term value pickups or waiver holds, read [references/long-term-holds.md](references/long-term-holds.md). It adds a role-first screening method, including injury-return competition and evidence that separates a durable opportunity from one big game. For a narrow timing or schedule follow-up, refresh those facts without repeating the entire scouting exercise.

1. **Establish roster and constraints.** Refresh ownership, FREEAGENT versus WAIVERS, injury flags, eligible slots, league scoring, matchup score, acquisition usage/limit, current scoring period and effective transaction period. Verify actual matchup boundaries; calendar Sunday is not automatically the matchup end. Separate live from settled scores. A healthy player without a game offers no points today.
2. **Build a broad shortlist.** Search the full available pool for the requested dates, including lower-projected players with emerging roles. The collector's default top 35 season projections are a starting point, not a complete recommendation set. Verify current NBA teams. Do not assume all available players are backups. Avoid treating one hot game or an early ejection as a stable baseline.
3. **Inspect teammates and opponents.** Review each candidate's NBA team's OUT, DAY_TO_DAY and other flags, including starters and competing reserves, regardless of fantasy ownership. Check opponent injuries too. Use current ESPN flags as the source of truth for ESPN's recorded status, then dated ESPN news and recent box scores to establish implications for the target game. DAY_TO_DAY is not confirmed OUT; ACTIVE does not guarantee full health or unrestricted minutes. Missing status is unknown.
4. **Explain opportunity.** Identify the absent player, evidence they normally start or occupy relevant minutes, likely replacements and competing beneficiaries. Check whether the candidate gains minutes, starts, handles the ball or closes games. The absence is evidence; a predicted role increase is an inference. Show plays/sits scenarios for uncertain availability and what happens when the starter returns. Dependable reserve minutes can be valuable without a starting role.
5. **Evaluate matchups.** Prioritize expected minutes and role, then production in this league's scoring, pace, opponent defense, opponent offensive tendencies, injuries and rest. For scorers consider shot quality/volume; for rebounders consider missed shots and competition; for steals/blocks consider opponent turnovers and shot profile. Overall win projections do not substitute for defensive ratings. Position-based allowances are secondary: nominal positions, switches and bench rotations differ. Prefer supported role evidence to a tiny season-projection advantage.
6. **Count usable games.** Compare a Saturday–Sunday back-to-back hold with a Saturday pickup followed by a Sunday replacement. Check opponents, tip times, home/away, travel/rest, back-to-back restrictions, transaction effective dates, waivers and pickup budget. Fit games into legal active slots; scheduled games are not always usable starts. Explain when the next move must occur and verify its effective period before execution. Do not assume a dropped player can be reacquired immediately or a future candidate remains available.
7. **Compare the drop and holding value.** Recommend the weakest fit with reasons, not simply the lowest projection. Assess requested days, rest of matchup, next full calendar week, rolling seven days and 14 days when useful. The user values sustainable holds alongside streaming. Distinguish gross pickup points from net improvement over the dropped player and displaced starters. Include plausible injury returns; never assume an uncertain OUT designation means zero points for two weeks. Preserve the core and don't discard an emerging high-minute player solely because of a poor opener.

## API-first evidence and ratings

ESPN league, schedule, box-score and athlete-news endpoints supply the initial review. Do not automatically run general web searches or require Reddit. If asked for online research, or a material injury/role/matchup gap remains, use dated sources and label opinion separately. Disclose conflicting feeds and timestamps. Direct API requests are live internet reads.

When the project's API exposes offensive rating, defensive rating and pace, incorporate source, season, sample size and retrieval time. Until then, label missing metrics unavailable; do not invent an endpoint or imply the existing collector provides them. Separate preseason forecasts, last-season actuals and current-season actuals. One or two games should not displace a sound preseason/roster baseline. Do not manufacture numerical matchup multipliers from qualitative ranks or double-count adjustments already included in daily projections.

## Result and action boundary

Lead with the preferred add/drop and confidence. Present the primary and every proposed backup in the reply using the scouting-table format in the workspace AGENTS.md. Give each the same coverage: identify the NBA team and opponent by name, show the usable schedule, and name the teammates competing for minutes. Keep the relevant numbers and return risk in the reply even when linking a longer report. Include availability and stream versus hold value. Label season baselines, daily forecasts and analyst estimates distinctly. Explain what changed from earlier advice and what news would change the choice; don't flip rankings merely because a new isolated stat was read.

Include pickup budget, acquisition timing, gross versus net benefit and uncertainty. Save a dated review with source links/times and action state beside the packet. The collector's optimized lineup is hypothetical, not a saved ESPN lineup.

For an explicitly authorized pair, use the local `espn-add-drop` skill with fresh preflight and verified readback. Its workflow includes minimal lineup activation for the intended scoring date, per the user's preference; verify the actual active slot before claiming the pickup is ready to score. Research alone does not authorize moves. Do not schedule unattended swaps or submit waiver claims as part of research.
