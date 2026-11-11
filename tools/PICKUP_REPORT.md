# Pickup research report

Generate a fresh, read-only packet from the authenticated ESPN league and public NBA feeds:

```sh
python3 tools/pickup_report.py --season 2027 --team 2
```

The season is ESPN's ending year: 2027 means 2026–27. The date defaults to today in Los Angeles. The default forward horizon is 14 days, starting at the first effective transaction date or today, whichever is later. Started games are excluded. Use `--days 7` through `--days 28` to change the horizon. Calendar-week comparisons are distinct from rolling seven-day totals and are not claimed to be fantasy matchup boundaries.

For a postgame review after midnight, separate the live roster date from the completed NBA slate:

```sh
python3 tools/pickup_report.py --season 2027 --team 2 \
  --date 2026-10-21 --slate-date 2026-10-20 --start-date 2026-10-21 --days 14
```

The standard-library-only collector reads existing `.env` credentials in memory, verifies the local dashboard, and uses direct ESPN endpoints for current ownership and transaction-period rosters. It does not use the Flask service's old season or pickle cache. It makes only GET requests and never submits transactions, changes lineups, sends messages, or schedules a job. See [the assistant handoff](FANTASY_ASSISTANT.md) for user preferences, recommendation history and write-API limitations.

Each timestamped directory under ignored `output/` contains:

- `report.html`: printable report with roster, NBA slate status, box scores, availability, waiver dates, forward schedule, legal-lineup replacement comparisons, separate calendar-week gains, ESPN headlines and source status.
- `packet.json`: normalized data and source URLs/retrieval times, without cookies or league member records.
- `research_queries.txt`: searches for fresh ESPN/Reddit research on drop candidates and available players.

The script rejects season/date mismatches and ownership/roster disagreement instead of treating stale or partial data as current. It preserves missing statistics as unknown, uses the league's scoring weights, and checks both ownership and availability. Today's scoring roster can differ from the transaction-period roster after an IR move or pickup. Available players on waivers are not immediate free agents.

## Complete the research review

1. Run the collector and inspect source failures, roster, injuries, live-game status and waiver dates.
2. Review the dated ESPN news (including role/minute context, not just headline), then current Reddit player discussions. Treat Reddit as opinion, not injury confirmation or league-specific availability. Avoid substituting prior-year results.
3. Compare usable starting-lineup games this week, next calendar week and over the full horizon. The model uses static season FP/G, excludes OUT/IR players for the full horizon, assumes DTD players play, and excludes a candidate's games before known waiver clearance. An unknown waiver-clear time contributes no new-player games. It does not predict a successful claim, future injury recovery, actual minutes or locks. It conservatively removes the dropped player for the whole horizon. Do not treat small differences as precise expected gains or count a short-term schedule win as a durable roster upgrade.
4. Write a dated `research-notes.json` outside source control with `date`, `leagueId`, `season`, `teamId`, and `sections` containing `title`, `paragraphs`, and `sources` (`title` and HTTPS `url`). Notes must match all four identity fields. Re-review conclusions even when refreshing on the same date.
5. Attach reviewed notes on a fresh run:

```sh
python3 tools/pickup_report.py --season 2027 --team 2 \
  --watch 4684793 6585 \
  --notes output/pickup_report_2026-10-20/research-notes.json
```

Without notes, the report explicitly says research review is pending. News fetching is automated; interpreting ESPN news and reading Reddit remain review steps. There is no unattended recommendation agent or recurring schedule. A request such as “refresh my pickup report and review ESPN/Reddit” can reuse this command and workflow.

## Verification

```sh
python3 -m pytest tests/test_pickup_report.py -q
```

The tests are offline. A normal report run provides a separate live, read-only integration check. The old ngrok Flask endpoint was unavailable on October 20, 2026; this collector does not depend on it. No remote Flask deployment is required.
