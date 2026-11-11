import type { League, Pick, Player } from "./types.js";

export const positionCategories = [
  "PG",
  "SG",
  "SF",
  "PF",
  "C",
  "F",
  "G",
] as const;
export type PositionCategory = (typeof positionCategories)[number];
export type PositionCandidates = Record<PositionCategory, Player[]>;

export function playerPositions(player: Player): PositionCategory[] {
  // ESPN's F/C, PF/C, G/F and SG/SF are combined lineup slots, not
  // additional individual eligibility. Never split them into positions.
  const eligible = new Set([...player.positions, ...player.slots]);
  if (eligible.has("PG") || eligible.has("SG")) eligible.add("G");
  if (eligible.has("SF") || eligible.has("PF")) eligible.add("F");
  return positionCategories.filter((position) => eligible.has(position));
}

export function positionCandidates(players: Player[]): PositionCandidates {
  const result: PositionCandidates = {
    PG: [],
    SG: [],
    SF: [],
    PF: [],
    C: [],
    F: [],
    G: [],
  };
  const unique = [...new Map(players.map((p) => [p.id, p])).values()];
  unique.sort(
    (a, b) =>
      (a.rank ?? Infinity) - (b.rank ?? Infinity) ||
      a.name.localeCompare(b.name),
  );
  for (const player of unique)
    for (const position of playerPositions(player))
      result[position].push(player);
  return result;
}

export function positionOverview(
  players: Player[],
  picks: Pick[],
  teams: League["teams"],
) {
  const byId = new Map(players.map((p) => [p.id, p]));
  const taken = new Set(
    picks.flatMap((p) => (p.playerId === null ? [] : [p.playerId])),
  );
  const top = [...byId.values()].filter(
    (p) => p.rank !== null && p.rank >= 1 && p.rank <= 150,
  );
  const available = top.filter((p) => !taken.has(p.id));
  return {
    total: top.length,
    remaining: available.length,
    top: positionCandidates(top),
    available: positionCandidates(available),
    teams: teams.map((team) => {
      const ids = new Set(
        picks
          .filter((p) => p.teamId === team.id && p.playerId !== null)
          .map((p) => p.playerId!),
      );
      const roster = [...ids].flatMap((id) =>
        byId.has(id) ? [byId.get(id)!] : [],
      );
      return {
        ...team,
        drafted: ids.size,
        unknown: ids.size - roster.length,
        positions: positionCandidates(roster),
      };
    }),
  };
}
