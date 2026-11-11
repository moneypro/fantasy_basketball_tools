import type { Bootstrap, League } from "./types.js";

export const sameLeague = (a: League, b: League) =>
  a.id === b.id && a.season === b.season && a.teamId === b.teamId;

// A slow full-player response must not roll back newer draft polling.
export function mergeBootstrap(
  current: Bootstrap,
  incoming: Bootstrap,
): Bootstrap {
  if (!sameLeague(current.league, incoming.league)) return incoming;
  const draft =
    Date.parse(current.meta.fetchedAt) > Date.parse(incoming.meta.fetchedAt)
      ? current
      : incoming;
  const stats =
    Date.parse(current.playerMeta.fetchedAt) >
    Date.parse(incoming.playerMeta.fetchedAt)
      ? current
      : incoming;
  return { ...stats, league: draft.league, meta: draft.meta };
}
