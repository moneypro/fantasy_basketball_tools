# Draftroom

During a live draft, the regular ESPN API may report no selections. From this host, run `npm run capture:draft` to capture the current draft using the existing ESPN login in the home browser. The capture disconnects as soon as ESPN sends its initial draft state, stops after 55 seconds, and publishes the selected players to the running local app. The board and Positions tab pick up the snapshot on their next poll. No picks are submitted.

Run captures between your turns: ESPN can disconnect your other draft session when this temporary session joins. This is a one-time snapshot, not continuous synchronization. The UI displays its capture time. The regular ESPN API takes over once it has at least as many selections. A failed capture keeps the previous snapshot. The runner requires host Chrome, Python 3, Docker, and the logged-in Chromium profile at `/home/hong/remote-browser/config/.config/chromium/Default/Cookies` (override with `ESPN_COOKIE_DB`). Cookies stay in memory; only draft picks and their capture time are persisted.

A local React + TypeScript draft companion for an ESPN head-to-head points league. A Node/Express server reads ESPN; the browser manages your personal research. No subscription or paid data provider is needed.

## Run with Docker

From the repository root:

```sh
docker compose -f draft-dashboard/compose.yaml up -d --build
```

Open the dashboard at any of these addresses on the home server:

- Local: **http://localhost:3030**
- Local LAN: **http://192.168.86.100:3030**
- Tailscale: **http://100.67.45.13:3030** (connect the visiting device to Tailscale)

Use the Tailscale address consistently at home and away to keep the same browser storage. Notes, shortlist, and manual/practice picks are stored per browser and origin: export a JSON backup from the old address and import it at the new address or on another device. They do not automatically sync between devices. The AI briefing export is for advice; use the JSON backup to transfer editable research.

The compose file uses the existing root `.env` (`LEAGUE_ID`, `ESPN_S2`, `SWID`), selects season **2027** (2026–27), and selects team **2**. Credentials remain inside the server container and are never bundled into JavaScript or written to the data cache. Port 3030 is bound specifically to loopback, the LAN IPv4 address, and the Tailscale IPv4 address. No public tunnel or router forwarding is configured by this project. Devices permitted to reach those addresses can view the league dashboard; there is no app login.

The existing `output/draft_research_2026-10-06` snapshot is mounted read-only. It lets the app open immediately when ESPN is unavailable. On a fresh checkout without that snapshot, valid ESPN credentials initialize the player pool. Live data caches persist in the `draftroom-data` Docker volume through container recreation. `restart: unless-stopped` restarts the app after a crash or host reboot; Docker and Tailscale are enabled at boot on this host. Keep the host powered on and connected while away. An explicitly stopped container stays stopped until started again; `down -v` deletes the data volume.

```sh
# Status and logs
docker compose -f draft-dashboard/compose.yaml ps
docker compose -f draft-dashboard/compose.yaml logs --tail 30

# Stop the app, keeping the data cache and browser notes
docker compose -f draft-dashboard/compose.yaml down
```

Set `DRAFTROOM_PORT=3031` before the compose command to use another port. `DRAFTROOM_LAN_IP` and `DRAFTROOM_TAILSCALE_IP` override the host-specific addresses when moving the service or changing the LAN address. Export your notes before changing the hostname or port.

## Draft workflow

1. Refresh stats before the draft. On opening, the app refreshes player data in the background when it is at least five minutes old.
2. Star your targets. Add a priority (1 is highest), tier, target round, and private notes. Avoid-tagged players are excluded from Next up.
3. Compare up to three players using the plus buttons. Points, games, minutes, injury flags, and preseason samples stay separate.
4. The live draft state is checked every five seconds. When a pick appears in ESPN, it leaves the available pool. Verify this behavior in the real draft room: pre-draft API access does not prove live synchronization latency.
5. If necessary, use **Record pick** to track a selection locally. Choose the selecting team; **Undo local pick** removes your latest local entry. These controls never submit picks to ESPN. If local and ESPN records disagree, ESPN wins and the app displays a conflict. Clear local overrides to reconcile.
6. Use **Rehearsal mode** to practice with a separate board. **Advance to my turn** simulates opponents using ADP, or rank when ADP is uncertain. This is a simple practice simulator, not a probability model. Reset only clears rehearsal picks.
7. Export a JSON backup after preparing your shortlist. Import validates league, season, team, and picks, then asks before replacing browser data.

## Position availability and team coverage

Open **Positions** for the remaining players ranked 1–150 by ESPN and each team's qualified candidates across **PG, SG, SF, PF, C, F, G**. Select a position total or team count to see the player names; selecting a player opens their profile. Top-150 availability follows ESPN rank even when a projection is missing. Team coverage includes all recorded picks, including players ranked outside the top 150.

Each player counts once in every eligible category: a SG/SF wing counts toward SG, SF, G, and F. Five single-position players at PG, SG, SF, PF, and C give counts of 1 for each base position, 2 for F, and 2 for G. These are candidate counts, not seven simultaneously filled slots. ESPN's combined lineup slots (F/C, PF/C, G/F, SG/SF) do not grant extra individual eligibility: a center with F/C eligibility does not automatically count at F. Live picks, local picks, undo, and the separate rehearsal board update both sections. Unknown drafted player records are flagged on their team.

## Slow connections

The server compresses API responses and caches versioned JavaScript, styles, and fonts in the browser. After the first successful load, the browser saves the player pool and latest received draft in IndexedDB, separate from personal notes and picks. On a repeat visit, that saved dashboard can open while bootstrap runs in the background; saved picks remain explicitly unverified until the server responds. Later data updates preserve your notes, selected tab, and any newer draft response.

Bootstrap stops waiting after 60 seconds and offers an in-place retry. Draft checks time out after eight seconds; player refreshes after 45 seconds. Saved data remains usable on a failed request. Automatic player refresh waits for bootstrap and skips data fetched within the last five minutes, avoiding two large downloads on opening. A first visit still requires a connection, and the app itself must load before the browser snapshot can be used; this is not a fully offline-installed app. Browser caches are per device and address and do not replace JSON backups of personal research.

## Read guides and player comments

Open **Guides** for concise plain-text research notes, source links, publication dates, and **Plain text** downloads. Search by player, author, or title; filter by draft target, do not draft, sleeper, breakout, bust risk, watch, or context only. Highlighted names open the corresponding player profile. The player pool shows how many guides mention each player; selecting a player in the pool, roster, or draft board shows their comments under **Overview** and **Guides**.

The initial library covers seven ESPN guides: André Snellings' Ultimate Draft Board, Eric Karabell's Do Draft and Do Not Draft lists, Sleepers/Breakouts/Busts, top sleepers, experts' favorite picks, and preseason position battles. Notes are short original paraphrases; the full articles remain at their source URLs. Each opinion retains its source and, for roundtables, its analyst. Contradictory opinions remain visible. Names mentioned only as teammates or comparisons receive **Context only**, not a recommendation. Source tags never change your personal shortlist or avoid flag. Publication-time advice is not live injury news, and category advice may differ from this league's custom points scoring.

The shared library lives in `research/library.json`, served through `GET /api/research`. Docker mounts that directory read-only, so every device sees the same library on page load or **Refresh guides**. Keep this file in project backups; browser JSON exports contain personal notes and picks, not the shared library. Updating article content does not require rebuilding or restarting the app.

### Add the next article

An assistant with this workspace can take a new article URL through the following workflow. Run from `draft-dashboard` with the app running; `DRAFTROOM_API` can override `http://127.0.0.1:3030`, or add `--pool /path/to/bootstrap.json` to use a saved API response.

```sh
# 1. Read HTML and produce local review evidence plus a review template.
npm run research -- extract 'https://example.com/article' --out /tmp/new-guide.json

# Alternatively, use HTML saved from a browser session with access to the article.
npm run research -- extract 'https://example.com/article' --html /tmp/article.html --out /tmp/new-guide.json

# 2. Review and edit /tmp/new-guide.review.json as described below.
# 3. Validate and preview the import, then save it.
npm run research -- import /tmp/new-guide.review.json
npm run research -- import /tmp/new-guide.review.json --write
npm run research -- check research/library.json
```

Extraction uses article HTML, structured metadata, ESPN player links, and unambiguous full-name matches against the league's player pool. It does not use OCR, guess surnames, or bypass access controls. Check the extracted paragraphs, headings, and `unresolved` identities. Manually resolve heading-only references, spelling errors, nicknames, or players absent from the current pool before importing. Non-ESPN sites with unusual markup may need an extractor adjustment or a manually prepared review file.

The review template deliberately leaves `summary` and `reviewedAt` empty, preventing unreviewed publication. Verify the title, source URL, authors, publication date, season, and scoring `format` (`points`, `categories`, `both`, or `general`). Write a concise original summary and player notes; do not copy the article body into the library. Retain price/round, health, role, and scoring qualifications. Assign tags from `target`, `avoid`, `sleeper`, `breakout`, `bust`, `watch`, or `mention`; `mention` is exclusive and means context only. Article titles alone are insufficient evidence for a player's tag. Finish by setting `reviewedAt` to the review's ISO timestamp.

Each `mentions` entry has the following shape. Use the exact ESPN ID and canonical player name from `/api/bootstrap`. Multiple opinions about the same player can use separate entries with different `section` or `analyst` values. Optional `aliases` allow reviewed spelling variants to highlight the same player.

```json
{
  "playerId": 1966,
  "playerName": "LeBron James",
  "tags": ["target"],
  "note": "Consider only at the source's stated fourth-round price.",
  "section": "Price exceptions",
  "analyst": "Eric Karabell"
}
```

Import validates all IDs, names, dates, tags, seasons, and source URLs before replacing the library atomically. Reimporting the same source replaces its old notes while retaining its stable article ID; ESPN URLs are deduplicated by article ID even if the slug changes. Other sources and their disagreements remain intact. The previous valid library is saved to `research/library.json.previous`. Raw extraction evidence stays outside the served app and should remain local to the review.

## Community notes from Reddit

**Community** is separate from the professional **Guides** library. It contains reviewed notes from recent `r/fantasybball` and `r/nba` RSS posts, with source links, publication dates, evidence coverage, and player links. Player profiles have their own **Community** tab; the overview previews community notes separately. Selecting a name in Community opens that player's community notes. Filters cover subreddit, player/text, rating, and player outlooks versus all reviewed posts. **Plain text** downloads the currently filtered notes.

The initial October 15 collection contains 25 posts from each subreddit, reviewed against the saved RSS evidence. The view defaults to posts with a player outlook; general questions, retrospective highlights, team-name discussions, and other background remain under **All reviewed posts**. Post ratings and player ratings are distinct, so an overall mixed post can favor one player and question another.

| Rating | Meaning              |
| ------ | -------------------- |
| 1      | Unfavorable          |
| 2      | Slightly unfavorable |
| 3      | Mixed or neutral     |
| 4      | Slightly favorable   |
| 5      | Favorable            |

These are our interpretations of the fantasy outlook supported by each post, **not** Reddit vote scores, an average of comments, a projection, or a claim of subreddit consensus. Confidence measures how clearly the sampled text supports the interpretation. Title-only posts are labeled. Passing references have a `null` player rating and display **Context only**. A question is not a confirmed injury report; historical highlights, platform complaints, and name lists must not become player endorsements. Category-specific advice retains that qualification. Community scores never change personal shortlist/avoid flags, professional-guide tags, or projections.

### Lightweight collection and review

The implementation follows the unauthenticated RSS pattern inspected in `/home/hong/reddit_bot/bot/reddit.py`. The existing bot, its database, subscription list, reply workflow, and credentials are unchanged. This collector has no Reddit login, OAuth, cookies, posting, voting, or comment-fetching code. It makes at most **two public GET requests** per run: one `/new.rss?limit=25` per subreddit, with no pagination or linked-page crawl. It waits at least ten seconds between feeds and respects Reddit reset headers. A long reset stops the run. HTTP 403/429 stops the entire run without retry and records a **24-hour minimum backoff**, extended by longer Retry-After/reset values. Other errors stop collection and preserve saved evidence.

**API token: none.** Basketball RSS collection needs no Reddit or OpenAI API key. Its only identifying request header is a descriptive User-Agent; conditional-cache headers may also be sent. The basketball commands do not call an AI model: the assistant reviews the saved post evidence in conversation, assigns the 1–5 ratings, and imports the reviewed notes. The separate DropRFID Reddit bot uses `OPENAI_API_KEY` from `/home/hong/rfid/.env`, injected through its Docker Compose `env_file`, for AI screening/reply drafts. That source was verified against the running bot on October 15, 2026, without exposing the key. It is not used by Draftroom's community collector.

Collection is **on request**, not scheduled. A persisted **six-hour cooldown** is reserved before the first request; a file lock prevents concurrent runs. Repeated commands during that cooldown perform zero Reddit requests. ETag/Last-Modified validators are reused when available. These limits reduce traffic without guaranteeing that a public RSS endpoint will always permit access.

Opening the app and **Reload saved notes** call only the local `GET /api/community` endpoint. They never fetch Reddit. New collection and review use the CLI from `draft-dashboard`:

```sh
# Run on the home server, with Draftroom running.
cd /home/hong/fantasy_basketball_tools/draft-dashboard

# Collect at most 25 recent posts per subreddit, subject to the saved cooldown.
npm run community -- fetch

# Prepare evidence and a review template for new or edited posts only.
npm run community -- review --out /tmp/community-review.json

# Read the evidence, then fill /tmp/community-review.review.json.
# Preview, save, and check the reviewed notes.
npm run community -- import --input /tmp/community-review.review.json
npm run community -- import --input /tmp/community-review.review.json --write
npm run community -- check
```

For draft-day preparation, ask the assistant: **“Refresh both basketball RSS feeds, review the new posts, and import the community notes into Draftroom.”** This means the full fetch → review → import → check sequence above. Fetching alone does not publish new ratings, and **Reload saved notes** only displays already imported notes. After import, open **Community → Reload saved notes**. There is no automatic scheduled basketball refresh; check **Collection coverage and freshness** for successful fetch times, pending reviews, and the next permitted collection time. Run a reviewed refresh a few hours before the draft, allowing time to handle a feed failure without bypassing the cooldown.

`DRAFTROOM_API` overrides the local API address; `--pool /path/to/bootstrap.json` supplies an offline player pool. `--dir /path/to/community` isolates a collection and its library for development. Preserve the real collection's cache and cooldown between runs; do not use another directory to evade a cooldown or Reddit refusal.

The review template leaves `summary`, `reviewedAt`, and player notes empty so it cannot be published without review. Resolve nicknames and spelling variants to exact ESPN IDs/names, recording reviewed `aliases` where useful. Automatic candidates use full names without removing generational suffixes: a historical Gary Payton mention must not become Gary Payton II. Read each post before assigning its overall 1–5 rating, per-player ratings, concise summary, and confidence. A per-player rating can be `null` for context. Do not infer replies from an unanswered question or ratings from a title pointing to an uncollected article/video. `basis` records `title` or `title-and-body`; it must match the collected evidence.

Raw RSS text and request state live in ignored `community/cache.json`; reviewed notes live in `community/library.json`. Imports validate player identities and source URLs, verify that each review matches its saved source content hash, and replace notes atomically with a `.previous` backup. If a post changes in a later feed, old ratings are withheld until that version is reviewed. The app shows review backlog, source failures, and last successful feed times. Notes older than 14 days disappear from the app; the collector retains at most 300 recent posts. Each RSS body is capped at 20,000 characters and each feed response at 2 MB.

Docker mounts `community/` read-only, so new reviewed content is available after reloading saved notes, without a rebuild. Keep the reviewed library and cache together in local backups; personal browser JSON backups do not include either shared source library. The container runs as UID 1000, matching this host's owner of the private cache files; preserve readable ownership when moving the service.

## Ask an AI using a text briefing

Click **AI briefing** in the top bar, enter your question, then **Copy text** or **Download .txt**. Paste it into this conversation or another assistant. There is no model connection, API key, or AI subscription in the dashboard.

The briefing captures your league scoring, roster, next picks, all recorded selections, shortlist/avoid tags, notes, selected/comparison players, and 25 available players by projected FP/G. It also includes imported guide opinions and source URLs for those candidates and your researched players, separately from personal flags. Community notes have a distinct section with player scores, source links, dates, confidence, and RSS coverage limitations. It includes timestamps and separates ESPN, local, and rehearsal selections. The preview is a frozen snapshot; use **Refresh snapshot** after more picks. Opening or refreshing the briefing attempts a draft read with an eight-second timeout; failures retain the saved board with an explicit warning. Player stats have their own timestamp; **Refresh stats** updates them.

An assistant with access to this same workspace can follow the included local API instructions to refresh picks and stats. Browser-only notes and manual picks remain in the pasted text. An assistant without local access must use the snapshot. The export is generated in your browser and contains your personal notes, but no server credentials.

### Candidate live-draft endpoint

The existing dashboard reads ESPN's `mDraftDetail` view:

```text
GET https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/2027/segments/0/leagues/{leagueId}?view=mDraftDetail
```

Checked October 7, 2026: the repository pins `espn-api==0.45.1`; [the latest release is 1.0.0](https://github.com/cwendt94/espn-api/releases/tag/v1.0.0), published October 2. Both versions include `league.espn_request.get_league_draft()`. However, the [high-level draft loader](https://github.com/cwendt94/espn-api/blob/v1.0.0/espn_api/base_league.py) returns early when `draftDetail.drafted` is false. Use the raw request for investigating an ongoing draft; no dependency upgrade is required to access it.

The actual league currently returns its 168 slots before the draft starts. This verifies access and structure, **not live pick latency**. Confirm changes during the real draft before relying on automatic tracking. The dashboard polls every five seconds, with server reads cached/coalesced for up to four seconds.

## How the numbers work

- Fantasy totals are recomputed from the league's scoring settings. Per-game figures divide those totals by games played. Missing projections remain unknown, not zero.
- ADP is shown for context. Missing/nonpositive values and values within 0.1 of ESPN's observed default of 140 are marked uncertain and excluded from draft-demand estimates. This heuristic does not establish that every other ADP is statistically reliable. ESPN exposes no usable sample size or calibrated next-pick probability here.
- Next up prioritizes your shortlist and priority, then projected FP/G; it explains whether the player can fill an open starting slot. It is not an optimized draft strategy or an injury-adjusted forecast.
- The roster view finds a position-valid assignment favoring stronger projected scorers. Its combined starter FP/G is not a weekly forecast or a guarantee that those players all play on the same date.
- Preseason data comes from completed ESPN box scores, starting October 1 of the season. It includes starts, minutes, per-game fantasy points, and links to the individual games. The sample is labeled and does not alter projections. Athletes absent from the fantasy pool are not guessed by name.
- The player table starts with projected players and your starred targets. **Include unprojected** opens the full pool.
- Every data set shows whether it is live or saved. If ESPN fails, the last known snapshot remains available. Notes do not require internet, but the local Docker server must be running to load the app.

## Local development

Node 22.12+ is required.

```sh
cd draft-dashboard
npm ci
npm run dev       # API on port 3030; stop Docker first if using this port
npm run dev:web   # Run in a second terminal; Vite on port 5173
```

`ENV_FILE`, `SEASON_YEAR`, `TEAM_ID`, `DATA_DIR`, `SEED_DIR`, `RESEARCH_DIR`, `COMMUNITY_DIR`, and `PORT` override server defaults. The default `.env` is the repository root file. Never put ESPN cookies in `VITE_*` variables or browser storage.

## Verification

```sh
npm run build
npm test
npx playwright install chromium
npm run test:e2e  # The production app must be running on port 3030
```

For an existing Chrome installation, set `DRAFTROOM_BROWSER=/path/to/google-chrome`. `DRAFTROOM_TEST_URL` overrides the test URL. Browser tests intercept the API with fictional league data so they do not change your real browser research or depend on ESPN availability.

Tests cover custom scoring, missing data, ADP flags, overlapping position eligibility, local/ESPN conflicts, duplicates, undo, a 168-pick replay, backup validation, notes surviving reload, comparisons, rehearsal isolation, offline sync, and mobile overflow. Research checks cover HTML extraction, player identity and alias matching, validation, atomic imports and source updates, conflicting opinions, context-only mentions, player/guide navigation, text downloads, refresh failures, and briefing integration.

Community checks cover the request cap, cooldown reservation, rate-limit resets, refusal backoff, conditional requests, failure preservation, source-change review, expiration, atomic imports, player-score attribution, separate guide/community views, filtering, exports, and phone navigation. Collector tests use fake responses and never contact Reddit.

The server exposes `GET /api/bootstrap`, `GET /api/draft`, `POST /api/refresh`, `GET /api/research`, `GET /api/community`, and `GET /api/health`. All external ESPN operations are GET requests. No account, roster, lineup, or draft mutations are implemented.
