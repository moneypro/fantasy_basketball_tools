import type { League, PreseasonGame } from "../shared/types.js";
import type { Raw } from "./normalize.js";

export async function getJson(
  url: string,
  headers: Record<string, string> = {},
): Promise<Raw> {
  const res = await fetch(url, {
    headers,
    signal: AbortSignal.timeout(15_000),
  });
  if (!res.ok) throw new Error(`Data provider returned HTTP ${res.status}.`);
  try {
    return (await res.json()) as Raw;
  } catch {
    throw new Error("Data provider returned an invalid response.");
  }
}
export function leagueEndpoint(season: number, id: number) {
  return `https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/${season}/segments/0/leagues/${id}`;
}
function cookieHeaders() {
  const s2 = process.env.ESPN_S2,
    swid = process.env.SWID;
  if (!s2 || !swid)
    throw new Error(
      "ESPN credentials are not configured; using the saved snapshot.",
    );
  return { Cookie: `espn_s2=${s2}; SWID=${swid}` };
}
export async function fetchLeague(season: number, id: number) {
  return getJson(
    `${leagueEndpoint(season, id)}?view=mSettings&view=mTeam&view=mDraftDetail`,
    cookieHeaders(),
  );
}
export async function fetchPlayers(season: number, id: number) {
  const results: Raw[] = [];
  const seen = new Set<number>();
  for (let offset = 0; offset < 10000; offset += 500) {
    const filter = {
      players: {
        limit: 500,
        offset,
        sortDraftRanks: { sortPriority: 1, sortAsc: true, value: "STANDARD" },
        filterStatsForTopScoringPeriodIds: {
          value: 1,
          additionalValue: [`00${season - 1}`, `10${season}`],
        },
      },
    };
    const d = await getJson(
      `${leagueEndpoint(season, id)}?view=kona_player_info&scoringPeriodId=0`,
      { ...cookieHeaders(), "x-fantasy-filter": JSON.stringify(filter) },
    );
    if (!Array.isArray(d.players))
      throw new Error("ESPN returned no player pool.");
    let added = 0;
    for (const p of d.players)
      if (!seen.has(p.id)) {
        seen.add(p.id);
        results.push(p);
        added++;
      }
    if (d.players.length < 500) return results;
    if (!added) throw new Error("ESPN pagination did not advance.");
  }
  throw new Error("Player pool exceeded the pagination limit.");
}
export async function fetchPreseason(
  league: League,
  existing: Raw[],
  through: string | null,
) {
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Los_Angeles",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const start = `${league.season - 1}-10-01`,
    end =
      today < `${league.season - 1}-10-31`
        ? today
        : `${league.season - 1}-10-31`;
  if (end < start) return { players: existing, through: null };
  const from = through && through >= start && through <= end ? through : start;
  const dates: string[] = [];
  for (
    let date = new Date(`${from}T12:00:00Z`);
    date.toISOString().slice(0, 10) <= end;
    date.setUTCDate(date.getUTCDate() + 1)
  )
    dates.push(date.toISOString().slice(0, 10));
  const events = new Map<string, Raw>();
  for (let i = 0; i < dates.length; i += 3) {
    const boards = await Promise.all(
      dates
        .slice(i, i + 3)
        .map((day) =>
          getJson(
            `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=${day.replaceAll("-", "")}`,
          ),
        ),
    );
    for (const board of boards)
      for (const event of board.events ?? [])
        if (event.season?.type === 1 && event.status?.type?.completed)
          events.set(event.id, event);
  }
  const players = new Map<number, Raw>(
    existing.map((p) => [p.id, { ...p, games: [...p.games] }]),
  );
  const known = new Set(
    existing.flatMap((p) => p.games.map((g: PreseasonGame) => g.eventId)),
  );
  const missing = [...events.values()].filter((e) => !known.has(e.id));
  for (let i = 0; i < missing.length; i += 3) {
    const games = await Promise.all(
      missing.slice(i, i + 3).map(async (event) => ({
        event,
        box: await getJson(
          `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=${event.id}`,
        ),
      })),
    );
    for (const { event, box } of games)
      for (const team of box.boxscore?.players ?? [])
        for (const table of team.statistics ?? [])
          for (const row of table.athletes ?? []) {
            if (row.didNotPlay || !row.stats?.length) continue;
            const stats = Object.fromEntries(
              table.labels.map((label: string, index: number) => [
                label,
                row.stats[index],
              ]),
            ) as Record<string, string>;
            const mins = String(stats.MIN).split(":").map(Number);
            const minutes = mins[0] + (mins[1] ?? 0) / 60;
            if (!Number.isFinite(minutes) || minutes <= 0) continue;
            const pair = (key: string) =>
              (stats[key] ?? "").split("-").map(Number);
            const [fgm, fga] = pair("FG"),
              [ftm, fta] = pair("FT"),
              [threes] = pair("3PT");
            const values: Record<string, number> = {
              PTS: Number(stats.PTS),
              REB: Number(stats.REB),
              AST: Number(stats.AST),
              STL: Number(stats.STL),
              BLK: Number(stats.BLK),
              TO: Number(stats.TO),
              FGM: fgm,
              FGA: fga,
              FTM: ftm,
              FTA: fta,
              "3PM": threes,
            };
            const fantasyPoints = Object.entries(league.weights).reduce(
              (sum, [key, weight]) => sum + (values[key] ?? 0) * weight,
              0,
            );
            if (!Number.isFinite(fantasyPoints)) continue;
            const id = Number(row.athlete.id);
            const player = players.get(id) ?? {
              id,
              name: row.athlete.displayName,
              games: [],
            };
            player.games.push({
              eventId: event.id,
              date: event.date,
              starter: !!row.starter,
              minutes,
              fantasyPoints,
              stats,
            });
            players.set(id, player);
          }
  }
  return {
    through: end,
    players: [...players.values()].map((p) => ({
      ...p,
      gamesPlayed: p.games.length,
      starts: p.games.filter((g: PreseasonGame) => g.starter).length,
      minutesPerGame:
        p.games.reduce((s: number, g: PreseasonGame) => s + g.minutes, 0) /
        p.games.length,
      fantasyPointsPerGame:
        p.games.reduce(
          (s: number, g: PreseasonGame) => s + g.fantasyPoints,
          0,
        ) / p.games.length,
    })),
  };
}
