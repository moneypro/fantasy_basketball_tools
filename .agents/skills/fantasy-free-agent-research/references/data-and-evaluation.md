# Data access and interpretation

## Existing read-only sources

`tools/pickup_report.py` makes standard-library authenticated GET requests. Reuse its `config`, `Collector`, `normalize`, `box_points` and legal-slot optimizer as appropriate. Run from the workspace root and use current ownership, not cached draft data.

- League base: `https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}/segments/0/leagues/{league}`. Views `mSettings`, `mTeam`, `mRoster`, `mMatchupScore` establish settings, roster and score.
- `?view=kona_player_info&scoringPeriodId={currentPeriod}` provides player flags and availability. Paginate in batches of 500 with `x-fantasy-filter`; reject nonadvancing pages. The helper contains the working filter.
- `league.scoringPeriodId` is today's period; `status.transactionScoringPeriod` is the effective transaction roster, possibly tomorrow after games start. Fetch that roster explicitly and reconcile ownership.
- Season URL `https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}?view=proTeamSchedules` supplies NBA teams and dated games. Convert to Pacific dates; exclude cancelled/postponed or already-started games from acquisition value.
- Scoreboard: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD`.
- Box score: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={eventId}`. Read `boxscore.players[].statistics[].athletes[]`, joining each tab's labels to stats. Inspect starter/DNP fields when supplied. Confirm minutes across multiple recent games when available; label preseason evidence separately.
- News: `https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{playerId}/overview`. `rotowire` contains headline, story and publication date. Fetch for shortlisted players AND relevant injured teammates, not just top season projections.

## Injury context helper

`scripts/injury_context.py` writes every NBA team with its flagged players, plus a normalized full pool with fantasy ownership and projected baselines. This supports finding injured starters owned by other managers and lower-projected candidates. `injuryFlagCount` counts flags, not verified current rotation absences. Legacy pool players can retain an NBA team ID and flag; corroborate current membership and role before using them as evidence. An empty list means no matching flags in this feed, not medical clearance for the team.

The helper uses GET only and records URLs, retrieval times and source failures, omitting credentials, members and raw league objects. It does not infer starters from `defaultPositionId` or fantasy lineup slots. Fantasy PG/BE is not an NBA depth chart.

For each opportunity claim distinguish:

- Injured teammate's raw flag and retrieval time versus expected availability on the target date.
- Confirmed starter/rotation role from dated news or box scores versus assumed depth-chart position.
- Observed candidate minutes/usage change versus projected change.
- Shared minutes among competing beneficiaries versus guaranteed replacement minutes.
- Scheduled back-to-back versus likely participation and any restrictions.

## Existing model limits

The collector uses static season projected FP/G, excludes OUT/IR players across the entire horizon, assumes DAY_TO_DAY players play, and may exclude players lacking projections. The candidate limit can miss useful reserves. Its legal-slot selection is not a complete locked-lineup optimizer. It does not automatically account for teammate absences, daily minutes, pace or opponent quality. Correct these limitations in the research review; the scenario table is not a calibrated forecast. Use league slot counts, not a hardcoded four-UTIL layout.

The older report workflow requests ESPN/Reddit review. For this skill the user's newer API-first preference takes precedence: dated ESPN API news starts the review; social discussion is optional unless requested.

## Future team ratings

No team-ratings endpoint is established here. Discover the actual project/API schema before integration. Preserve team ID, season, date range, games/possessions sampled, source and retrieval time for:

- Offensive rating: points scored per 100 possessions; higher is better.
- Defensive rating: points allowed per 100 possessions; lower is better.
- Pace: verify provider possessions/time definition before comparing.
- Optional opponent turnovers, rebounding, rim/three-point allowances and lineup splits.

Map provider IDs and season labels explicitly. Separate forecasts from observed ratings. Use league-relative values only when a numerical adjustment is justified and explain the method; otherwise report a qualitative matchup assessment. Include opponent defense for scoring efficiency and opponent offense for steals, blocks and rebound opportunities. An easy matchup cannot create minutes for someone outside the rotation.

## Decision checks

- DAY_TO_DAY starter: show plays/sits cases; no automatic full minutes boost.
- Two games with recent DNPs versus one game with dependable minutes: schedule alone cannot choose the winner.
- A 14-day gain driven by assuming the dropped player stays OUT: expose the assumption and compare a plausible return.
- A report after tipoff: verify current/effective roster and exclude retroactive scoring.
- A strong real-life opponent: assess defense and pace separately from projected wins.
- Missing team rating: say unavailable, proceed with supported evidence and search when useful or requested.
