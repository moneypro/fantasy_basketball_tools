import type { Bootstrap, League, Player, StatLine } from "../shared/types.js";
export const stats = (fppg: number): StatLine => ({
  fppg,
  total: fppg * 70,
  games: 70,
  minutes: 30,
  stats: { PTS: 20, REB: 5, AST: 4, MIN: 30 },
});
export const player = (
  id: number,
  slots = ["PG", "G", "UT", "BE"],
): Player => ({
  id,
  name: `Player ${id}`,
  team: "SEA",
  positions: slots.filter((s) => ["PG", "SG", "SF", "PF", "C"].includes(s)),
  slots,
  rank: id,
  adp: id + 1,
  adpUncertain: false,
  injury: "ACTIVE",
  outlook: "",
  projected: stats(60 - id),
  previous: stats(55 - id),
  preseason: null,
});
export const league: League = {
  id: 123,
  season: 2027,
  name: "Test League",
  teamId: 2,
  teams: [
    { id: 1, name: "First Team" },
    { id: 2, name: "My Team" },
  ],
  draftAt: 1792209600000,
  secondsPerPick: 60,
  draftType: "SNAKE",
  inProgress: false,
  completed: false,
  slots: { PG: 1, SG: 1, UT: 1, BE: 1, IR: 1 },
  weights: {
    PTS: 1,
    REB: 1,
    AST: 2,
    STL: 4,
    BLK: 4,
    FGM: 2,
    FGA: -1,
    FTM: 1,
    FTA: -1,
    "3PM": 1,
    TO: -2,
  },
  picks: Array.from({ length: 8 }, (_, i) => ({
    overall: i + 1,
    round: Math.floor(i / 2) + 1,
    teamId: [1, 2, 2, 1][i % 4],
    playerId: null,
  })),
};
export const fixture: Bootstrap = {
  league,
  players: Array.from({ length: 20 }, (_, i) =>
    player(i + 1, i % 2 ? ["SG", "G", "UT", "BE"] : ["PG", "G", "UT", "BE"]),
  ),
  meta: { source: "live", fetchedAt: new Date().toISOString() },
  playerMeta: { source: "live", fetchedAt: new Date().toISOString() },
  preseasonThrough: "2026-10-06",
};
