import type { League, Pick, Player, Preference, SavedState } from "./types.js";
export const emptyPreference = (): Preference => ({
  target: false,
  avoid: false,
  priority: 3,
  tier: "",
  round: "",
  note: "",
});
export const emptyState = (league: League): SavedState => ({
  version: 1,
  leagueId: league.id,
  season: league.season,
  teamId: league.teamId,
  preferences: {},
  manualPicks: [],
  practicePicks: [],
});

export function reconcilePicks(slots: Pick[], manual: Pick[]) {
  const picks = slots.map((p) => ({ ...p }));
  const conflicts: string[] = [];
  const known = new Map(
    picks.filter((p) => p.playerId).map((p) => [p.playerId, p.overall]),
  );
  for (const local of manual) {
    const slot = picks.find((p) => p.overall === local.overall);
    if (!slot || !local.playerId) {
      conflicts.push(`Local pick ${local.overall} is outside the draft.`);
      continue;
    }
    if (slot.playerId) {
      if (slot.playerId !== local.playerId || slot.teamId !== local.teamId)
        conflicts.push(
          `ESPN and your local record differ at pick ${local.overall}. ESPN is shown.`,
        );
      continue;
    }
    if (known.has(local.playerId)) {
      conflicts.push(
        `Local pick ${local.overall} repeats a player already selected. The earlier record is shown.`,
      );
      continue;
    }
    Object.assign(slot, local, { local: true });
    known.set(local.playerId, local.overall);
  }
  return { picks, conflicts };
}
export function nextPick(picks: Pick[]) {
  return picks.find((p) => !p.playerId);
}
export function retireConfirmedPicks(remote: Pick[], manual: Pick[]) {
  return manual.filter(
    (local) =>
      !remote.some(
        (p) =>
          p.overall === local.overall &&
          p.playerId === local.playerId &&
          p.teamId === local.teamId,
      ),
  );
}
export function availablePlayers(players: Player[], picks: Pick[]) {
  const drafted = new Set(picks.map((p) => p.playerId));
  return players.filter((p) => !drafted.has(p.id));
}
export function demand(p: Player): number {
  return !p.adpUncertain && p.adp != null ? p.adp : (p.rank ?? 9999);
}
export function practiceToTurn(
  slots: Pick[],
  current: Pick[],
  players: Player[],
  teamId: number,
) {
  const result = [...current];
  const blank = slots.map((p) => ({ ...p, playerId: null }));
  while (true) {
    const picks = reconcilePicks(blank, result).picks;
    const pick = nextPick(picks);
    if (!pick || pick.teamId === teamId) break;
    const player = availablePlayers(players, picks)
      .filter((p) => p.projected.fppg != null)
      .sort((a, b) => demand(a) - demand(b))[0];
    if (!player) break;
    result.push({ ...pick, playerId: player.id, local: true });
  }
  return result;
}
// Find a valid assignment across overlapping eligibility (PG/G/UTIL, etc.).
export function fitRoster(players: Player[], slots: Record<string, number>) {
  const active = Object.entries(slots)
    .filter(([s]) => !["BE", "IR", ""].includes(s))
    .flatMap(([slot, count]) =>
      Array.from({ length: count }, (_, index) => ({ slot, index })),
    );
  const assigned = new Map<number, Player>();
  const place = (player: Player, visited: Set<number>): boolean => {
    for (let i = 0; i < active.length; i++) {
      if (!player.slots.includes(active[i].slot) || visited.has(i)) continue;
      visited.add(i);
      const incumbent = assigned.get(i);
      if (!incumbent || place(incumbent, visited)) {
        assigned.set(i, player);
        return true;
      }
    }
    return false;
  };
  for (const player of [...players].sort(
    (a, b) => (b.projected.fppg ?? -1) - (a.projected.fppg ?? -1),
  ))
    place(player, new Set());
  return {
    slots: active.map((s, i) => ({ ...s, player: assigned.get(i) })),
    bench: players.filter(
      (p) => ![...assigned.values()].some((a) => a.id === p.id),
    ),
  };
}
export function validateImport(value: unknown, league: League): SavedState {
  if (!value || typeof value !== "object")
    throw new Error("This is not a Draftroom backup.");
  const s = value as SavedState;
  if (
    s.version !== 1 ||
    s.leagueId !== league.id ||
    s.season !== league.season ||
    s.teamId !== league.teamId
  )
    throw new Error("This backup belongs to another league, team, or season.");
  if (
    !s.preferences ||
    typeof s.preferences !== "object" ||
    Array.isArray(s.preferences)
  )
    throw new Error("Invalid shortlist data.");
  for (const [id, p] of Object.entries(s.preferences)) {
    if (
      !/^\d+$/.test(id) ||
      !p ||
      typeof p.target !== "boolean" ||
      typeof p.avoid !== "boolean" ||
      !Number.isInteger(p.priority) ||
      p.priority < 1 ||
      p.priority > 5 ||
      ["tier", "round", "note"].some(
        (k) => typeof p[k as keyof Preference] !== "string",
      ) ||
      p.note.length > 10000
    )
      throw new Error("Invalid player preferences.");
  }
  for (const list of [s.manualPicks, s.practicePicks]) {
    if (!Array.isArray(list) || list.length > league.picks.length)
      throw new Error("Invalid draft records.");
    const used = new Set<number>();
    const numbers = new Set<number>();
    for (const p of list) {
      if (
        !p ||
        !Number.isInteger(p.playerId) ||
        !p.playerId ||
        p.playerId < 1 ||
        !league.teams.some((t) => t.id === p.teamId) ||
        !league.picks.some(
          (x) => x.overall === p.overall && x.round === p.round,
        ) ||
        used.has(p.playerId) ||
        numbers.has(p.overall)
      )
        throw new Error("Invalid or duplicated draft pick.");
      used.add(p.playerId);
      numbers.add(p.overall);
    }
  }
  return {
    version: 1,
    leagueId: s.leagueId,
    season: s.season,
    teamId: s.teamId,
    preferences: s.preferences,
    manualPicks: s.manualPicks,
    practicePicks: s.practicePicks,
  };
}
