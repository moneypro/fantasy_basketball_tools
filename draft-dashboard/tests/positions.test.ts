import { describe, expect, it } from "vitest";
import {
  playerPositions,
  positionCandidates,
  positionOverview,
} from "../shared/positions.js";
import { league, player } from "./fixtures.js";

describe("position eligibility", () => {
  it("does not turn ESPN combined lineup slots into individual positions", () => {
    expect(
      playerPositions(player(1, ["C", "PF/C", "F/C", "UT", "BE", "IR"])),
    ).toEqual(["C"]);
    expect(playerPositions(player(2, ["PG", "G", "G/F", "UT"]))).toEqual([
      "PG",
      "G",
    ]);
    expect(
      playerPositions(player(3, ["PF", "F", "G/F", "PF/C", "F/C"])),
    ).toEqual(["PF", "F"]);
    expect(playerPositions(player(4, ["SG/SF", "G/F", "F/C", "UT"]))).toEqual(
      [],
    );
  });
  it("counts a wing in both guard and forward without double counting flex eligibility", () => {
    const wing = player(1, ["SG", "SF", "G", "F", "SG/SF", "F/C"]);
    expect(playerPositions(wing)).toEqual(["SG", "SF", "F", "G"]);
    expect(playerPositions(player(2, ["PG", "SG"]))).toEqual(["PG", "SG", "G"]);
    const grouped = positionCandidates([
      wing,
      wing,
      player(2, ["PG", "SG", "G"]),
    ]);
    expect(grouped.G.map((p) => p.id)).toEqual([1, 2]);
    expect(grouped.F.map((p) => p.id)).toEqual([1]);
    expect(grouped.C).toEqual([]);
  });
  it("matches the five-player example across all seven categories", () => {
    const grouped = positionCandidates(
      ["PG", "SG", "SF", "PF", "C"].map((p, i) => player(i + 1, [p])),
    );
    expect(
      Object.fromEntries(
        Object.entries(grouped).map(([p, candidates]) => [
          p,
          candidates.length,
        ]),
      ),
    ).toEqual({ PG: 1, SG: 1, SF: 1, PF: 1, C: 1, F: 2, G: 2 });
  });
});

describe("position overview", () => {
  it("uses ESPN ranks 1–150 regardless of projections and counts all team picks", () => {
    const unprojected = player(150, ["C", "F/C"]);
    unprojected.projected.fppg = null;
    const players = [
      player(1),
      player(149),
      unprojected,
      player(151),
      { ...player(152), rank: null },
      { ...player(153), rank: 0 },
      { ...player(154), rank: -1 },
    ];
    const picks = league.picks.map((p, i) => ({
      ...p,
      playerId: [1, 151, 999, 1][i] ?? null,
    }));
    const result = positionOverview(players, picks, league.teams);
    expect(result.total).toBe(3);
    expect(result.remaining).toBe(2);
    expect(result.available.C.map((p) => p.id)).toEqual([150]);
    expect(result.available.G.map((p) => p.id)).toEqual([149]);
    expect(result.teams[0].drafted).toBe(1);
    expect(result.teams[0].positions.G.map((p) => p.id)).toEqual([1]);
    expect(result.teams[1].drafted).toBe(2);
    expect(result.teams[1].unknown).toBe(1);
    expect(result.teams[1].positions.G.map((p) => p.id)).toEqual([151]);
  });
  it("shows zero coverage and full availability before picks", () => {
    const result = positionOverview([player(1)], league.picks, league.teams);
    expect(result.remaining).toBe(1);
    expect(
      result.teams.every(
        (t) =>
          t.drafted === 0 &&
          Object.values(t.positions).every((p) => p.length === 0),
      ),
    ).toBe(true);
  });
});
