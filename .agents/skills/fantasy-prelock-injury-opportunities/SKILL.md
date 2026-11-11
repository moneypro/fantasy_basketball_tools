---
name: fantasy-prelock-injury-opportunities
description: Check significant NBA absences and identify available teammates gaining minutes, starts or usage before the first-game fantasy roster lock. Use for last-minute injury news, injury replacement pickups, or refreshing same-day streaming advice. ESPN API first; read-only unless a specific transaction is separately authorized.
---

# Pre-lock injury opportunities

Find who benefits when an important player is unavailable, then determine whether that beneficiary is available and useful in the user's ESPN points league. Scan the entire relevant slate before narrowing to a previously recommended player. A significant absence is a rotation, minutes or usage loss, not merely a famous name or an OUT flag.

Keep this skill local to `/home/hong/fantasy_basketball_tools/.agents/skills`. Read `tools/FANTASY_ASSISTANT.md` for current preferences and completed/scheduled actions. Known identity is league 30695, team 2, season 2027 for 2026–27; verify live identity, dates and season each time. Existing credentials stay in memory and never appear in outputs.

## Establish the deadline first

Use America/Los_Angeles for user-facing dates and times. Fetch today's ESPN scoreboard and live league settings/status before lengthy research. Report the retrieval time, first unstarted/started game, current scoring period and effective transaction period.

The known league's roster membership locks at the **first NBA game**, while individual lineup positions lock at each player's tip. Verify `FIRSTGAME_SCORINGPERIOD` and `INDIVIDUAL_GAME`; do not assume the candidate's later tip is the pickup deadline. Recheck at final recommendation or action if close to lock. After rollover, identify the earliest effective date and never promise today's points from a tomorrow-effective add. A cancelled/postponed game is not a usable start.

For a requested last-minute check, prioritize fresh status and a usable recommendation before the deadline. Do not wait beyond roster lock for a late game's final injury decision. If a recurring check is separately requested, derive that day's first tip rather than using one fixed time; a useful initial review is 30–60 minutes before tip, with a final refresh if requested or actively working near lock. Creating or invoking this skill alone does not install a daily timer or authorize unattended transactions.

## ESPN API first

Reuse the existing GET-only collectors instead of rebuilding league ingestion. See [data and evaluation](../fantasy-free-agent-research/references/data-and-evaluation.md) for exact endpoints, normalization and limitations, and `tools/PICKUP_REPORT.md` for report options.

```bash
python3 .agents/skills/fantasy-free-agent-research/scripts/injury_context.py --season SEASON --league LEAGUE --output output/UNIQUE_REVIEW/injury_context.json
python3 tools/pickup_report.py --season SEASON --team TEAM --compare-drop DROP_ID --limit 100 --output output/UNIQUE_REVIEW
```

Replace placeholders with freshly verified values. Use a new dated review directory; do not overwrite a completed transaction's evidence. The injury inventory contains the full player pool, including players missing season projections and injured players owned by other managers. The report's top candidates are only a screening list.

Retrieve these ESPN sources as needed:

- Authenticated league settings/roster/player pool: ownership, FREEAGENT versus WAIVERS, eligible slots, counters, injury flags and effective date.
- Public scoreboard and season `proTeamSchedules`: dates, opponents, tip times and started games.
- Athlete overview `rotowire` news for each meaningful injured player **and** candidate: publication time, probable/questionable/out designation, expected return, restrictions, rest and coach comments.
- Recent game summaries/box scores: actual starters, minutes, DNPs, usage and production under this league's scoring.

ESPN `DAY_TO_DAY` does not distinguish probable from questionable; interpret the dated story. An old OUT flag can conflict with a newer return report. Show both timestamps and the unresolved conflict rather than silently selecting the more favorable status. A newly fetched old article is not new news. ACTIVE is not proof of unrestricted minutes or confirmed participation in a back-to-back.

Use web search when the user asks to search, or when ESPN lacks material role/injury detail, a final status or a timely update. Prefer official NBA/team reports and named beat reporters; use reputable reporting as corroboration. Check the original report time and target game, not just the search crawl date. Do not present an older preview's OUT label as a new ruling when the current feed says questionable. Label opinions and projections. If no new reliable update exists, say so; do not imply every refresh found a change.

## Trace each absence to a real opportunity

1. Scan all teams playing on the requested day, plus tomorrow for a two-day plan. Include significant new absences, rest, restrictions and existing absences still creating opportunity. Corroborate current team membership for legacy pool entries.
2. Establish the absent player's normal role from dated news/recent games: starting job, typical minutes, ball handling, rebounding or defensive responsibility. Separate confirmed OUT from uncertain availability.
3. Identify likely beneficiaries: direct backup, another starter shifting positions, reserve committee, or usage redistributed to existing starters. Matching nominal positions or fantasy eligibility is not enough. Do not assume all vacated minutes go to one player.
4. Verify each beneficiary's recent minutes, starts, closing role when evidenced, DNPs and competition. Compare games with and without the absent teammate where possible. Mark preseason, garbage-time blowouts, foul trouble and very small samples. A hot shooting or steals game is not evidence of a stable role by itself.
5. For a questionable teammate, explain both **plays** and **sits** cases. For multiple questionable players, explain which absence matters and who shares the benefit. If the starter returns tomorrow, reduce or end the short-term opportunity; do not project an uncertain absence across two weeks.
6. Join candidates to live fantasy ownership. Include lower-projected and unprojected players with credible minutes. An unavailable beneficiary is context, not a pickup recommendation. Distinguish immediate free agents from pending waivers, and respect the user's preference to reserve waiver priority for sustainable holds.

A useful evidence chain is: **absent player and status → vacated role → candidate and competing replacements → observed role evidence → expected opportunity (inference) → availability and usable starts**. If the chain is weak, downgrade confidence rather than inventing minutes.

## Rank for this roster

Use [fantasy-free-agent-research](../fantasy-free-agent-research/SKILL.md) for broader schedule/hold comparisons. Prioritize role and usable games over static season FP/G. Assess relevant opponent injuries and basketball fit; label unavailable pace/defensive ratings rather than manufacturing matchup multipliers.

Compare a two-day hold with a one-day pickup plus replacement, including acquisition cost and legal starting slots. Check the actual drop's games and current role, not just their old projection. Preserve productive emerging players and the core. Explain gross pickup production versus net gain after lost/displaced starts. Analyst ranges must be labeled estimates, not ESPN daily forecasts. Show short-stream versus sustainable-hold value and the news that would change the ranking.

Near a first-game deadline, refresh ownership, candidate availability and the decisive teammate news. If no clear upgrade survives the checks, recommend holding rather than forcing a transaction.

## Result and action handoff

Give a compact, phone-friendly result:

- Checked-at Pacific time, whether games started, and the **roster-membership deadline**.
- Preferred exact add/drop, team, FREEAGENT/WAIVERS status and confidence; meaningful alternatives only.
- Significant absence, replacement evidence and plays/sits caveat beside each candidate.
- Today/tomorrow opponents and usable starts, pickup budget, and stream/hold decision.
- What changed since earlier advice; source links and source publication times where freshness matters.
- Exact action state: research only, or separately verified transaction/lineup status.

Save dated `research-notes.json` beside the collector packet using its date/league/season/team fields, with sources and reasons for ranking changes. Retain source failures and uncertainties.

Research never authorizes add/drop, claims or scheduled swaps. Once the user authorizes an exact pair, route to [espn-add-drop](../espn-add-drop/SKILL.md) for fresh preflight, atomic transaction, minimal activation and readback. Reuse recent research; do not require redundant permission. If late news invalidates the specified move, explain the change rather than silently buying another player. Use [espn-roster-rollover](../espn-roster-rollover/SKILL.md) only for an explicitly authorized next-day scheduled replacement.
