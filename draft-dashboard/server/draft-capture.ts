import type { DraftResponse, Pick } from "../shared/types.js";

export interface DraftCapture {
  leagueId: number;
  season: number;
  capturedAt: string;
  picks: Pick[];
}

/** Apply a complete live-room snapshot only while the regular API lags behind. */
export function applyDraftCapture(
  state: DraftResponse,
  value: unknown,
): DraftResponse {
  const capture = value as DraftCapture | null;
  const league = state.league;
  if (
    !capture ||
    capture.leagueId !== league.id ||
    capture.season !== league.season ||
    !Number.isFinite(Date.parse(capture.capturedAt)) ||
    Date.parse(capture.capturedAt) < league.draftAt - 86_400_000 ||
    Date.parse(capture.capturedAt) > Date.now() + 60_000 ||
    !Array.isArray(capture.picks) ||
    league.completed
  )
    return state;
  const slots = new Map(league.picks.map((p) => [p.overall, p]));
  const teams = new Set(league.teams.map((t) => t.id));
  const players = new Set<number>();
  const numbers = new Set<number>();
  for (const pick of capture.picks) {
    if (
      !pick ||
      !Number.isInteger(pick.overall) ||
      !slots.has(pick.overall) ||
      !Number.isInteger(pick.playerId) ||
      pick.playerId! <= 0 ||
      !teams.has(pick.teamId) ||
      players.has(pick.playerId!) ||
      numbers.has(pick.overall)
    )
      return state;
    players.add(pick.playerId!);
    numbers.add(pick.overall);
  }
  if (capture.picks.length <= league.picks.filter((p) => p.playerId).length)
    return state;
  // INIT is a full snapshot: reject partial or malformed captures.
  if (capture.picks.some((_, i) => !numbers.has(i + 1))) return state;
  const selected = new Map(capture.picks.map((p) => [p.overall, p]));
  return {
    league: {
      ...league,
      picks: league.picks.map((p) => {
        const captured = selected.get(p.overall);
        return captured
          ? { ...p, teamId: captured.teamId, playerId: captured.playerId }
          : p;
      }),
    },
    meta: {
      source: "snapshot",
      fetchedAt: capture.capturedAt,
      error:
        "Picks captured from the ESPN draft room. This is a snapshot; later picks need another capture or local tracking.",
    },
  };
}
