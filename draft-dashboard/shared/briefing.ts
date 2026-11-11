import type { Bootstrap, Player, SavedState } from "./types.js";
import { indexResearch, tagLabels, type ResearchLibrary } from "./research.js";
import {
  indexCommunity,
  ratingLabels,
  type CommunityLibrary,
} from "./community.js";
import {
  emptyPreference,
  fitRoster,
  nextPick,
  reconcilePicks,
} from "./draft.js";

export interface BriefingOptions {
  data: Bootstrap;
  saved: SavedState;
  practice: boolean;
  question: string;
  generatedAt: string;
  apiOrigin: string;
  focusIds?: number[];
  research?: ResearchLibrary;
  community?: CommunityLibrary;
}
const num = (value: number | null | undefined) =>
  value == null ? "unknown" : value.toFixed(1);

/** Plain text only; personal preferences are supplied by the browser, never fetched from the server. */
export function buildBriefing({
  data,
  saved,
  practice,
  question,
  generatedAt,
  apiOrigin,
  focusIds = [],
  research,
  community,
}: BriefingOptions): string {
  const { league, players } = data;
  const { picks, conflicts } = reconcilePicks(
    practice
      ? league.picks.map((p) => ({ ...p, playerId: null }))
      : league.picks,
    practice ? saved.practicePicks : saved.manualPicks,
  );
  const byId = new Map(players.map((p) => [p.id, p]));
  const completed = picks.filter((p) => p.playerId != null);
  const taken = new Set(completed.map((p) => p.playerId));
  const current = nextPick(picks);
  const upcoming = picks.filter(
    (p) => p.teamId === league.teamId && !p.playerId,
  );
  const teamName = (id: number) =>
    league.teams.find((t) => t.id === id)?.name ?? `Team ${id}`;
  const pref = (id: number) => saved.preferences[id] ?? emptyPreference();
  const label = (id: number) =>
    `${byId.get(id)?.name ?? "Unknown player"} [ESPN ${id}]`;
  const row = (p: Player) =>
    `${label(p.id)} | ${p.team} ${p.positions.join("/")} | proj FP/G ${num(p.projected.fppg)} | GP ${num(p.projected.games)} | total FP ${num(p.projected.total)} | minutes ${num(p.projected.minutes)} | last FP/G ${num(p.previous.fppg)} (${num(p.previous.games)} GP) | ESPN rank ${p.rank ?? "unknown"} | ADP ${p.adpUncertain ? `uncertain (${num(p.adp)})` : num(p.adp)} | injury ${p.injury} | ${taken.has(p.id) ? "PICKED" : "AVAILABLE"}${pref(p.id).avoid ? " | AVOID" : ""}${p.preseason ? ` | preseason ${p.preseason.gamesPlayed} GP, ${p.preseason.starts} starts, ${num(p.preseason.minutesPerGame)} MIN, ${num(p.preseason.fantasyPointsPerGame)} FP/G` : " | preseason unknown"}`;
  const available = players.filter((p) => !taken.has(p.id));
  const candidates = available
    .filter((p) => p.projected.fppg != null && !pref(p.id).avoid)
    .sort((a, b) => (b.projected.fppg ?? 0) - (a.projected.fppg ?? 0))
    .slice(0, 25);
  const personal = players
    .filter((p) => {
      const x = pref(p.id);
      return (
        x.target || x.avoid || x.note || x.tier || x.round || x.priority !== 3
      );
    })
    .sort(
      (a, b) =>
        pref(a.id).priority - pref(b.id).priority ||
        (a.rank ?? 9999) - (b.rank ?? 9999),
    );
  const mine = completed
    .filter((p) => p.teamId === league.teamId)
    .flatMap((p) => (byId.has(p.playerId!) ? [byId.get(p.playerId!)!] : []));
  const fit = fitRoster(mine, league.slots);
  const upcomingLine =
    upcoming
      .slice(0, 4)
      .map((p) => `#${p.overall} (round ${p.round})`)
      .join(", ") || "No picks remaining";
  const researchIndex = research ? indexResearch(research) : new Map();
  const researchIds = [
    ...new Set([
      ...focusIds,
      ...personal.map((p) => p.id),
      ...candidates.map((p) => p.id),
    ]),
  ];
  const guideLines = researchIds.flatMap((id) =>
    (researchIndex.get(id) ?? []).flatMap(
      ({ article, mentions }: import("./research.js").PlayerResearch) => [
        `${label(id)} | ${article.title} | ${article.authors.join(", ")} | ${article.publishedAt} | ${article.format} | ${article.url}`,
        ...mentions.map(
          (m) =>
            `  ${m.tags.map((t) => tagLabels[t]).join(", ")} | ${m.section}${m.analyst ? ` | ${m.analyst}` : ""}: ${m.note || "Context only; no recommendation assigned."}`,
        ),
      ],
    ),
  );
  const draftAge = Date.parse(generatedAt) - Date.parse(data.meta.fetchedAt);
  const communityIndex = community ? indexCommunity(community) : new Map();
  const communityLines = researchIds.flatMap((id) =>
    (communityIndex.get(id) ?? []).map(
      ({ post, mention }: import("./community.js").PlayerCommunity) =>
        `${label(id)} | ${mention.rating === null ? "Context only" : `${mention.rating}/5 ${ratingLabels[mention.rating]}`} | r/${post.subreddit} | ${post.publishedAt} | ${post.confidence} confidence | ${post.basis} | ${post.url}\n  ${mention.note}`,
    ),
  );
  const lines = [
    "DRAFTROOM — ASSISTANT BRIEFING",
    `Generated: ${generatedAt}`,
    `MODE: ${practice ? "REHEARSAL — simulated selections; do not replace these with the real draft" : "REAL LEAGUE — ESPN-reported picks plus explicitly labeled local records"}`,
    "",
    "MY QUESTION",
    question.trim() || "Who should I target at my next pick, and who can wait?",
    "",
    "REQUEST",
    "Act as my fantasy basketball draft adviser. Recommend up to three AVAILABLE players, explain the tradeoffs for my points league, and give a backup if the first choice is taken. Respect my shortlist and avoid tags; distinguish my notes from verified facts. Consider projected points/game, games played, roster eligibility, injury uncertainty, draft cost, and the gap to my next turn. Do not submit picks or change my ESPN team.",
    "",
    "FRESHNESS AND LIMITS",
    `Draft data: ${data.meta.source}; fetched ${data.meta.fetchedAt}; ${draftAge > 20_000 || data.meta.source !== "live" || data.meta.error ? "STALE OR UNVERIFIED — refresh before advising" : "recent successful read; in-progress update latency is still unverified"}.`,
    ...(data.meta.error ? [`Draft error: ${data.meta.error}`] : []),
    `Player stats: ${data.playerMeta.source}; fetched ${data.playerMeta.fetchedAt}${data.playerMeta.error ? `; error: ${data.playerMeta.error}` : ""}.`,
    `Preseason sample through: ${data.preseasonThrough ?? "unknown"}${data.preseasonError ? `; ${data.preseasonError}` : ""}. Small samples describe role/minutes; they do not automatically change projections.`,
    "An HTTP 200 before the draft does not prove live picks update quickly. Blank picks do not prove nobody has picked if the feed is lagging. ADP near ESPN’s default of 140 is uncertain; other ADPs are market averages, not calibrated survival probabilities. Missing stats are unknown, not zero.",
    ...conflicts.map((x) => `RECONCILIATION CONFLICT: ${x}`),
    "",
    "LEAGUE AND SCORING",
    `${league.name} | leagueId=${league.id} | ESPN season=${league.season} (${league.season - 1}–${league.season}) | teamId=${league.teamId} (${teamName(league.teamId)})`,
    `${league.teams.length} teams | ${league.draftType} | ${league.secondsPerPick}s per pick | ${picks.length} total slots | ESPN inProgress=${league.inProgress}, completed=${league.completed}`,
    `Roster slots: ${Object.entries(league.slots)
      .map(([s, n]) => `${s}=${n}`)
      .join(", ")}`,
    `Fantasy scoring: ${Object.entries(league.weights)
      .map(([s, w]) => `${s}=${w}`)
      .join(", ")}`,
    "",
    "DRAFT POSITION",
    `Recorded selections: ${completed.length}/${picks.length}. ${current ? `Next unfilled slot: #${current.overall}, round ${current.round}, ${teamName(current.teamId)}.` : "Board is complete."}`,
    `My next picks: ${upcomingLine}`,
    "",
    "MY ROSTER",
    ...(mine.length ? mine.map(row) : ["No players recorded on my roster."]),
    `Open active slots in a valid eligibility assignment: ${
      fit.slots
        .filter((s) => !s.player)
        .map((s) => s.slot)
        .join(", ") || "none"
    }. Bench players: ${fit.bench.map((p) => p.name).join(", ") || "none"}.`,
    "",
    "MY SHORTLIST, AVOIDS, AND PERSONAL RESEARCH",
    ...(personal.length
      ? personal.flatMap((p) => [
          row(p),
          `  My preferences: target=${pref(p.id).target}; avoid=${pref(p.id).avoid}; priority=${pref(p.id).priority} (1 highest); tier=${JSON.stringify(pref(p.id).tier)}; target round=${JSON.stringify(pref(p.id).round)}; note=${JSON.stringify(pref(p.id).note)}`,
        ])
      : ["No personal research has been added in this browser."]),
    "",
    "PLAYERS I AM LOOKING AT",
    ...[...new Set(focusIds)]
      .filter((id) => byId.has(id))
      .map((id) => row(byId.get(id)!)),
    "",
    "TOP AVAILABLE BY PROJECTED FP/G",
    `Showing ${candidates.length} non-avoided projected players from ${available.length} remaining records; this is a sample, not the entire candidate pool. Shortlisted/unprojected players appear above.`,
    ...candidates.map(row),
    "",
    "ALL RECORDED PICKS / OPPONENT ROSTERS",
    ...(completed.length
      ? completed.map(
          (p) =>
            `#${p.overall} R${p.round} | ${teamName(p.teamId)} [team ${p.teamId}] | ${label(p.playerId!)} | ${practice ? "SIMULATED" : p.local ? "LOCAL, NOT ESPN-CONFIRMED" : "ESPN-REPORTED"}`,
        )
      : ["No selections recorded."]),
    "",
    "IMPORTED GUIDE NOTES FOR FOCUS, SHORTLIST, AND AVAILABLE CANDIDATES",
    "These are source-attributed paraphrases, not my personal preferences or live injury updates. Preserve disagreements and scoring-format differences. Context-only mentions are not recommendations.",
    ...(guideLines.length
      ? guideLines
      : ["No matching imported guide notes in this snapshot."]),
    "",
    "COMMUNITY NOTES — SEPARATE FROM PROFESSIONAL GUIDES",
    "Our reading of a limited recent Reddit RSS sample. Titles and post text only; no comment threads or votes. Ratings are fantasy outlook in these posts, not subreddit consensus or verified news. 1 unfavorable, 2 slightly unfavorable, 3 mixed/neutral, 4 slightly favorable, 5 favorable. Context-only mentions are unscored.",
    ...(communityLines.length
      ? communityLines
      : ["No matching reviewed community notes in this snapshot."]),
    "",
    "REFRESH IN THE SAME WORKSPACE",
    `Dashboard API origin in this browser: ${apiOrigin}. The default Docker address is http://localhost:3030; check draft-dashboard/compose.yaml and docker compose ps for port overrides or browser proxies.`,
    "GET /api/draft performs a fresh ESPN draft read (coalesced/cached for up to 4 seconds). GET /api/bootstrap returns the current saved player bundle and may be stale. POST /api/refresh refreshes league/player/preseason reads and a local cache; it makes no ESPN writes.",
    "Use league.picks from /api/draft and join playerId to players[].id from /api/bootstrap. Null playerId means an unfilled slot. These APIs do NOT include browser-local shortlist, notes, manual picks, or practice state: retain those from this briefing.",
    ...(practice
      ? [
          "This is a practice board. You may refresh player stats, but preserve the simulated picks above.",
        ]
      : [
          "Refresh ESPN-reported picks before advising. Match local picks to returned slots; retire matching confirmations. If an official pick conflicts with a local record, report the conflict and prefer the official record. If an official slot is still blank, keep the local record explicitly unconfirmed rather than silently dropping it.",
        ]),
    `Raw ESPN candidate: GET https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/${league.season}/segments/0/leagues/${league.id}?view=mDraftDetail`,
    'Python wrapper: league.espn_request.get_league_draft()["draftDetail"]. Both espn-api 0.45.1 (repository pin) and 1.0.0 have this method. The higher-level league.draft loader returns early when draftDetail.drafted is false, so do not rely on it for an in-progress draft. Reuse existing server-side credentials without printing or including them in prompts. Avoid the repository’s stale pickle/season defaults.',
    "If you cannot access this workspace or localhost, reason only from this timestamped snapshot and say so. Ask for a new briefing if freshness could change the recommendation.",
    "",
    "ANSWER FORMAT",
    "1. Best available choice and why. 2. Two backups with tradeoffs. 3. Who might be worth waiting on (uncertain, not a numeric probability). 4. Any stale data, missing information, or local/official conflict that changes the answer.",
  ];
  return lines.join("\n") + "\n";
}
