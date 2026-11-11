import { describe, it, expect } from "vitest";
import {
  availablePlayers,
  emptyState,
  fitRoster,
  practiceToTurn,
  reconcilePicks,
  retireConfirmedPicks,
  validateImport,
} from "../shared/draft.js";
import {
  normalizeLeague,
  normalizePlayers,
  statLine,
} from "../server/normalize.js";
import { fixture, league, player } from "./fixtures.js";

describe("draft reconciliation", () => {
  it("keeps unfilled ESPN slots available and merges a local pick", () => {
    const local = { ...league.picks[0], playerId: 3 };
    const result = reconcilePicks(league.picks, [local]);
    expect(result.picks[0].playerId).toBe(3);
    expect(
      availablePlayers(fixture.players, result.picks).some((p) => p.id === 3),
    ).toBe(false);
    expect(result.picks[1].playerId).toBeNull();
  });
  it("deduplicates a locally recorded pick after ESPN confirms it", () => {
    const confirmed = { ...league.picks[0], playerId: 3 };
    const result = reconcilePicks(
      [confirmed, ...league.picks.slice(1)],
      [confirmed],
    );
    expect(result.conflicts).toEqual([]);
    expect(result.picks.filter((p) => p.playerId === 3)).toHaveLength(1);
    expect(result.picks[0].local).toBeUndefined();
  });
  it("preserves ESPN authority and reports conflicting picks", () => {
    const remote = [
      { ...league.picks[0], playerId: 5 },
      ...league.picks.slice(1),
    ];
    const result = reconcilePicks(remote, [
      { ...league.picks[0], playerId: 3 },
    ]);
    expect(result.picks[0].playerId).toBe(5);
    expect(result.conflicts).toHaveLength(1);
  });
  it("never adds a player twice, including a player confirmed in a different slot", () => {
    const remote = [
      { ...league.picks[0], playerId: 5 },
      ...league.picks.slice(1),
    ];
    const result = reconcilePicks(remote, [
      { ...league.picks[1], playerId: 5 },
    ]);
    expect(result.picks[1].playerId).toBeNull();
    expect(result.conflicts).toHaveLength(1);
  });
  it("restores availability after undo without mutating the remote board", () => {
    const local = [{ ...league.picks[0], playerId: 3 }];
    expect(
      availablePlayers(
        fixture.players,
        reconcilePicks(league.picks, local.slice(0, -1)).picks,
      ),
    ).toHaveLength(20);
    expect(league.picks[0].playerId).toBeNull();
  });
  it("retires confirmations so an ESPN rollback does not resurrect a local pick", () => {
    const local = { ...league.picks[0], playerId: 3 };
    const confirmed = [local, ...league.picks.slice(1)];
    const remaining = retireConfirmedPicks(confirmed, [local]);
    expect(remaining).toHaveLength(0);
    expect(
      reconcilePicks(league.picks, remaining).picks[0].playerId,
    ).toBeNull();
  });
  it("uses the selecting team rather than previous owners of a traded pick", () => {
    const normalized = normalizeLeague(
      {
        id: 1,
        seasonId: 2027,
        teams: [{ id: 2, name: "Mine" }],
        settings: {
          name: "Test",
          draftSettings: {},
          rosterSettings: { lineupSlotCounts: {} },
          scoringSettings: { scoringType: "H2H_POINTS", scoringItems: [] },
        },
        draftDetail: {
          picks: [
            {
              overallPickNumber: 13,
              roundId: 2,
              teamId: 2,
              owningTeamIds: [20],
              playerId: 3,
            },
          ],
        },
      },
      2,
    );
    expect(normalized.picks[0].teamId).toBe(2);
  });
  it("handles a full 168-pick snake replay with unique players", () => {
    const slots = Array.from({ length: 168 }, (_, i) => ({
      overall: i + 1,
      round: Math.floor(i / 14) + 1,
      teamId: Math.floor(i / 14) % 2 ? 14 - (i % 14) : (i % 14) + 1,
      playerId: null,
    }));
    const log = slots.map((p, i) => ({ ...p, playerId: i + 1 }));
    for (let n = 0; n <= 168; n++) {
      const result = reconcilePicks(slots, log.slice(0, n));
      expect(result.conflicts).toHaveLength(0);
      expect(result.picks.filter((p) => p.playerId)).toHaveLength(n);
    }
  });
});
describe("practice and roster fit", () => {
  it("stops at your turn and keeps live picks untouched", () => {
    const result = practiceToTurn(league.picks, [], fixture.players, 2);
    expect(result).toHaveLength(1);
    expect(result[0].teamId).toBe(1);
    expect(league.picks.every((p) => p.playerId === null)).toBe(true);
  });
  it("finds valid assignments when guards overlap and leaves unfillable slots empty", () => {
    const result = fitRoster(
      [
        player(1, ["PG", "SG", "G", "UT"]),
        player(2, ["PG", "G", "UT"]),
        player(3, ["SG", "G", "UT"]),
      ],
      { PG: 1, SG: 1, F: 1, UT: 1, BE: 3 },
    );
    expect(result.bench).toHaveLength(0);
    expect(result.slots.find((s) => s.slot === "F")?.player).toBeUndefined();
    expect(
      new Set(result.slots.flatMap((s) => (s.player ? [s.player.id] : [])))
        .size,
    ).toBe(3);
  });
  it("keeps the stronger player in the starting lineup when only one fits", () => {
    const result = fitRoster([player(20, ["PG"]), player(1, ["PG"])], {
      PG: 1,
      BE: 1,
    });
    expect(result.slots[0].player?.id).toBe(1);
    expect(result.bench[0].id).toBe(20);
  });
});
describe("data quality and backups", () => {
  it("recomputes league scoring and preserves absent projections as unknown", () => {
    expect(statLine(undefined, league.weights).fppg).toBeNull();
    const line = statLine(
      {
        stats: {
          "0": 20,
          "3": 5,
          "6": 10,
          "1": 2,
          "2": 1,
          "13": 8,
          "14": 15,
          "15": 2,
          "16": 3,
          "17": 2,
          "11": 3,
          "42": 1,
        },
      },
      league.weights,
    );
    expect(line.total).toBe(48);
    expect(line.fppg).toBe(48);
  });
  it("flags fallback-like ADP values without hiding genuine top-player ADP", () => {
    const raw = (adp: number) => ({
      player: {
        id: 1,
        fullName: "Test Player",
        eligibleSlots: [0, 5, 11],
        ownership: { averageDraftPosition: adp },
        stats: [],
      },
    });
    expect(normalizePlayers([raw(140.02)], league)[0].adpUncertain).toBe(true);
    expect(normalizePlayers([raw(16.91)], league)[0].adpUncertain).toBe(false);
  });
  it("rejects backups from other leagues and malformed or duplicate picks", () => {
    const state = emptyState(league);
    expect(validateImport(state, league)).toEqual(state);
    expect(() => validateImport({ ...state, season: 2026 }, league)).toThrow(
      /another/,
    );
    expect(() =>
      validateImport(
        {
          ...state,
          manualPicks: [
            { ...league.picks[0], playerId: 3 },
            { ...league.picks[1], playerId: 3 },
          ],
        },
        league,
      ),
    ).toThrow(/duplicated/);
    expect(() =>
      validateImport({ ...state, preferences: { "1": { note: 4 } } }, league),
    ).toThrow(/Invalid/);
  });
});
