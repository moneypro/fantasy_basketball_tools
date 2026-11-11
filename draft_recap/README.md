# Draft recap archive

The original report is `best_draft_2025.py`. The website’s **Draft Recap** tab
extends that report with season selection, rankings, the original top-five and
lowest-three scorer lists, steals/busts, and every original draft pick. The
2026–27 recap uses only ESPN's full-season projections, with projected steals
and reaches labeled separately from historical results.

Refresh the public snapshots from the repo root:

```sh
python3 webapp/scripts/build-draft-history.py --season 2027 --projected --latest-only
python3 -m unittest tests.test_draft_history
./webapp/scripts/deploy-amplify.sh
```

The season is ESPN’s ending year: 2027 means 2026–27. `--latest-only` preserves
all existing historical snapshots. Without it, the builder discovers and
refreshes all previous seasons from ESPN league metadata, including the
pre-2018 history endpoint. `--projected` applies only to the requested latest
season and requires a completed draft. Omit it to build actual season totals.
It uses `ESPN_S2`, `SWID`, and `LEAGUE_ID` environment variables or the
existing `fantasy-basketball/espn` AWS secret. Credentials remain in memory;
only selected player, team, and analysis fields enter `webapp/site/data/draft`.
No Lambda change is required: these sanitized snapshots are served with the site
and remain available when the live API is down. Refresh unfinished seasons when
updated results are needed; the page displays snapshot dates and season state.

Projected rankings sum each original pick's ESPN full-season projection under
the season's league scoring weights, including bench picks and ESPN's projected
games played. Only that season's projection records (`statSourceId=1`,
`statSplitTypeId=0`) are used. Actual stats, preseason results, ADP, and research
ratings never enter projected rankings. Missing projections stay unknown, with
no fallback to actuals. This compares drafted rosters, not optimized lineups or
predicted standings. Projection snapshots remain fixed until explicitly refreshed.

Original draft picks receive their entire NBA season’s fantasy points regardless
of lineup decisions or subsequent transactions. Historical points seasons use
their own scoring settings, not the latest year’s stats or projections. Category
seasons use the requested latest season’s points rules as an explicitly labeled
retrospective comparison, not an original category result. No comparisons or
aggregate rankings across differently scored seasons are made.

Value is overall pick minus scoring rank among drafted players. Tied point totals
share competition rank. Steals have positive value; busts/reaches have negative
value and were drafted in rounds 1–10. Missing totals stay null; incomplete team
totals and ranks remain unavailable. Historical rank awards are withheld when
coverage is incomplete. Projected steals and reaches remain visible as explicitly
provisional comparisons among players with projections, while team ranks compare
only fully projected teams. In 2026–27, Joan Beringer has no ESPN projection at
the time of the snapshot, leaving Dragon City Tiedan unranked. In 2016–17,
ESPN supplies no season total for Ben Simmons, so that year has incomplete coverage.
