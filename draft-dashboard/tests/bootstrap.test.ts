import { expect, it } from "vitest";
import { mergeBootstrap } from "../shared/bootstrap.js";
import { fixture } from "./fixtures.js";

it("keeps newer picks when an older full-player request finishes late", () => {
  const current = structuredClone(fixture);
  const incoming = structuredClone(fixture);
  current.meta.fetchedAt = "2026-10-17T04:00:05Z";
  current.league.picks[0].playerId = 1;
  current.playerMeta.fetchedAt = "2026-10-17T03:00:00Z";
  incoming.meta.fetchedAt = "2026-10-17T04:00:00Z";
  incoming.playerMeta.fetchedAt = "2026-10-17T04:00:01Z";
  incoming.players[0].rank = 7;
  const result = mergeBootstrap(current, incoming);
  expect(result.league.picks[0].playerId).toBe(1);
  expect(result.players[0].rank).toBe(7);
  expect(result.meta).toEqual(current.meta);
  expect(result.playerMeta).toEqual(incoming.playerMeta);
});

it("does not mix a different league's picks or players into a bootstrap", () => {
  const incoming = structuredClone(fixture);
  incoming.league.id = 456;
  expect(mergeBootstrap(fixture, incoming)).toBe(incoming);
});
