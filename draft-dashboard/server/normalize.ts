import type {
  League,
  Pick,
  Player,
  Preseason,
  StatLine,
} from "../shared/types.js";
// ESPN's undocumented payloads are normalized at this boundary; the app consumes typed models.
export type Raw = Record<string, any>;
export const slotNames: Record<string, string> = {
  0: "PG",
  1: "SG",
  2: "SF",
  3: "PF",
  4: "C",
  5: "G",
  6: "F",
  7: "SG/SF",
  8: "G/F",
  9: "PF/C",
  10: "F/C",
  11: "UT",
  12: "BE",
  13: "IR",
};
export const statNames: Record<string, string> = {
  0: "PTS",
  1: "BLK",
  2: "STL",
  3: "AST",
  6: "REB",
  11: "TO",
  13: "FGM",
  14: "FGA",
  15: "FTM",
  16: "FTA",
  17: "3PM",
  40: "MIN",
  42: "GP",
};
const teamNames: Record<string, string> = {
  0: "FA",
  1: "ATL",
  2: "BOS",
  3: "NOP",
  4: "CHI",
  5: "CLE",
  6: "DAL",
  7: "DEN",
  8: "DET",
  9: "GSW",
  10: "HOU",
  11: "IND",
  12: "LAC",
  13: "LAL",
  14: "MIA",
  15: "MIL",
  16: "MIN",
  17: "BKN",
  18: "NYK",
  19: "ORL",
  20: "PHI",
  21: "PHX",
  22: "POR",
  23: "SAC",
  24: "SAS",
  25: "OKC",
  26: "UTA",
  27: "WAS",
  28: "TOR",
  29: "MEM",
  30: "CHA",
};
const num = (x: unknown): number | null =>
  typeof x === "number" && Number.isFinite(x) ? x : null;
export function normalizeLeague(d: Raw, teamId: number): League {
  const s = d.settings;
  if (
    !s?.draftSettings ||
    !s.rosterSettings ||
    !s.scoringSettings ||
    !Array.isArray(d.teams)
  )
    throw new Error("ESPN returned incomplete league settings.");
  if (s.scoringSettings.scoringType !== "H2H_POINTS")
    throw new Error(
      "Draftroom currently supports head-to-head points leagues.",
    );
  const teams = d.teams.map((t: Raw) => ({
    id: t.id,
    name: t.name || `${t.location ?? ""} ${t.nickname ?? ""}`.trim(),
  }));
  if (!teams.some((t: Raw) => t.id === teamId))
    throw new Error("Configured team is not in this league.");
  const picks: Pick[] = (d.draftDetail?.picks ?? [])
    .map((p: Raw) => ({
      overall: p.overallPickNumber,
      round: p.roundId,
      teamId: p.teamId,
      playerId: p.playerId > 0 ? p.playerId : null,
    }))
    .sort((a: Pick, b: Pick) => a.overall - b.overall);
  return {
    id: d.id ?? d.leagueId,
    season: d.seasonId,
    name: s.name ?? d.name,
    teamId,
    teams,
    draftAt: s.draftSettings.date,
    draftType: s.draftSettings.type,
    secondsPerPick: s.draftSettings.timePerSelection,
    inProgress: !!d.draftDetail?.inProgress,
    completed: !!d.draftDetail?.drafted,
    slots: Object.fromEntries(
      Object.entries(s.rosterSettings.lineupSlotCounts)
        .filter(([, n]) => Number(n) > 0)
        .map(([id, n]) => [slotNames[id] ?? id, Number(n)]),
    ),
    weights: Object.fromEntries(
      s.scoringSettings.scoringItems.map((x: Raw) => [
        statNames[x.statId] ?? `STAT_${x.statId}`,
        x.points,
      ]),
    ),
    picks,
  };
}
export function statLine(
  raw: Raw | undefined,
  weights: Record<string, number>,
): StatLine {
  if (!raw?.stats || !Object.keys(raw.stats).length)
    return { fppg: null, total: null, games: null, minutes: null, stats: {} };
  const games = num(raw.stats["42"]);
  const totalStats = Object.fromEntries(
    Object.entries(raw.stats).map(([id, v]) => [
      statNames[id] ?? `STAT_${id}`,
      Number(v),
    ]),
  );
  const total = Object.entries(weights).reduce(
    (sum, [key, weight]) => sum + (totalStats[key] ?? 0) * weight,
    0,
  );
  const stats = Object.fromEntries(
    Object.entries(totalStats).map(([key, v]) => [
      key,
      games && games > 0 && key !== "GP" ? v / games : v,
    ]),
  );
  return {
    total,
    games,
    fppg: games && games > 0 ? total / games : null,
    minutes: stats.MIN ?? null,
    stats,
  };
}
export function normalizePlayers(
  entries: Raw[],
  league: League,
  preseason: Raw[] = [],
): Player[] {
  const pre = new Map(preseason.map((p) => [Number(p.id), p as Preseason]));
  return entries.map((e) => {
    const p = e.player ?? e;
    const seed = !e.player;
    const adp = num(p.ownership?.averageDraftPosition);
    const slots: string[] = seed
      ? p.eligibleSlots
      : (p.eligibleSlots ?? []).map((s: number) => slotNames[s] ?? String(s));
    return {
      id: p.id,
      name: p.fullName ?? p.name,
      team: p.nbaTeam ?? teamNames[p.proTeamId] ?? "FA",
      positions: slots.filter((s) => ["PG", "SG", "SF", "PF", "C"].includes(s)),
      slots,
      rank: num(p.draftRanksByRankType?.STANDARD?.rank),
      adp: adp && adp > 0 ? adp : null,
      adpUncertain: adp == null || adp <= 0 || Math.abs(adp - 140) <= 0.10001,
      injury: p.injuryStatus ?? "UNKNOWN",
      outlook: String(p.seasonOutlook ?? "").replace(/<[^>]*>/g, ""),
      projected: statLine(
        seed
          ? p.projection
          : p.stats?.find((s: Raw) => s.id === `10${league.season}`),
        league.weights,
      ),
      previous: statLine(
        seed
          ? p.previousSeason
          : p.stats?.find((s: Raw) => s.id === `00${league.season - 1}`),
        league.weights,
      ),
      preseason: pre.get(p.id) ?? null,
    };
  });
}
