import { describe, expect, it } from "vitest";
import { buildBriefing, type BriefingOptions } from "../shared/briefing.js";
import { emptyPreference, emptyState } from "../shared/draft.js";
import { fixture } from "./fixtures.js";

function options(): BriefingOptions {
  return {
    data: structuredClone(fixture),
    saved: emptyState(fixture.league),
    practice: false,
    question: "Who should I take?",
    generatedAt: fixture.meta.fetchedAt,
    apiOrigin: "http://localhost:3030",
  };
}
describe("assistant briefing", () => {
  it("keeps notes and distinguishes local picks, official picks and avoids", () => {
    const o = options();
    o.data.league.picks[0].playerId = 1;
    o.saved.manualPicks = [
      { ...o.data.league.picks[1], playerId: 2, local: true },
    ];
    o.saved.preferences[3] = {
      ...emptyPreference(),
      target: true,
      avoid: true,
      note: "Check role\nbefore picking",
      tier: "B",
    };
    const text = buildBriefing(o);
    expect(text).toContain("Who should I take?");
    expect(text).toContain("Player 1 [ESPN 1] | ESPN-REPORTED");
    expect(text).toContain("Player 2 [ESPN 2] | LOCAL, NOT ESPN-CONFIRMED");
    expect(text).toContain('note="Check role\\nbefore picking"');
    const candidates = text
      .split("TOP AVAILABLE BY PROJECTED FP/G")[1]
      .split("ALL RECORDED PICKS")[0];
    for (const id of [1, 2, 3])
      expect(candidates).not.toContain(`Player ${id} [ESPN ${id}]`);
    expect(candidates).toContain("Player 4 [ESPN 4]");
    expect(text).toContain("AST=2");
    expect(text).toContain("GET /api/draft");
  });
  it("preserves the rehearsal board independently of real and manual picks", () => {
    const o = options();
    o.practice = true;
    o.data.league.picks[0].playerId = 1;
    o.saved.manualPicks = [{ ...o.data.league.picks[1], playerId: 2 }];
    o.saved.practicePicks = [{ ...o.data.league.picks[0], playerId: 3 }];
    const text = buildBriefing(o);
    expect(text).toContain("MODE: REHEARSAL");
    expect(text).toContain("Player 3 [ESPN 3] | SIMULATED");
    expect(text).toContain("Player 1 [ESPN 1] | SEA PG");
    expect(text).not.toContain("| ESPN-REPORTED");
    expect(text).not.toContain("| LOCAL, NOT ESPN-CONFIRMED");
    expect(text).toContain("preserve the simulated picks above");
  });
  it("reports stale data, missing stats and conflicts without fabricating values", () => {
    const o = options();
    o.data.meta = {
      source: "snapshot",
      fetchedAt: "2025-01-01T00:00:00Z",
      error: "Offline",
    };
    o.data.league.picks[0].playerId = 1;
    o.saved.manualPicks = [{ ...o.data.league.picks[0], playerId: 2 }];
    o.saved.preferences[2] = { ...emptyPreference(), target: true };
    o.data.players[1].projected.fppg = null;
    o.data.players[1].adp = 140;
    o.data.players[1].adpUncertain = true;
    const text = buildBriefing(o);
    expect(text).toContain("STALE OR UNVERIFIED");
    expect(text).toContain("Draft error: Offline");
    expect(text).toContain("RECONCILIATION CONFLICT:");
    expect(text).toContain("proj FP/G unknown");
    expect(text).toContain("ADP uncertain (140.0)");
  });
});
