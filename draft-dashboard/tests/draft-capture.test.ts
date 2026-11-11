import { describe, expect, it } from "vitest";
import { applyDraftCapture } from "../server/draft-capture";
import { fixture } from "./fixtures";
const state = {
  league: { ...fixture.league, draftAt: Date.now() - 60_000 },
  meta: fixture.meta,
};
const capture = {
  leagueId: state.league.id,
  season: state.league.season,
  capturedAt: new Date().toISOString(),
  picks: state.league.picks
    .slice(0, 2)
    .map((p, i) => ({ ...p, playerId: i + 100 })),
};
describe("live room captures", () => {
  it("fills the board while the regular ESPN API still has no picks", () => {
    const result = applyDraftCapture(state, capture);
    expect(result.league.picks.slice(0, 2).map((p) => p.playerId)).toEqual([
      100, 101,
    ]);
    expect(result.meta.source).toBe("snapshot");
    expect(result.meta.fetchedAt).toBe(capture.capturedAt);
    expect(state.league.picks[0].playerId).toBeNull();
    expect(applyDraftCapture(state, capture)).toEqual(result);
  });
  it("defers to the regular API once it catches up or the draft completes", () => {
    const caughtUp = {
      ...state,
      league: {
        ...state.league,
        picks: [...capture.picks, ...state.league.picks.slice(2)],
      },
    };
    expect(applyDraftCapture(caughtUp, capture)).toBe(caughtUp);
    const complete = { ...state, league: { ...state.league, completed: true } };
    expect(applyDraftCapture(complete, capture)).toBe(complete);
  });
  it("rejects wrong leagues, duplicate players, missing picks, and invalid dates", () => {
    for (const invalid of [
      { ...capture, leagueId: 999 },
      { ...capture, season: 2026 },
      { ...capture, capturedAt: "invalid" },
      { ...capture, capturedAt: "2020-01-01T00:00:00Z" },
      { ...capture, picks: [capture.picks[1]] },
      {
        ...capture,
        picks: capture.picks.map((p) => ({ ...p, playerId: 100 })),
      },
      { ...capture, picks: capture.picks.map((p) => ({ ...p, teamId: 999 })) },
    ])
      expect(applyDraftCapture(state, invalid)).toBe(state);
  });
});
