import { describe, expect, it } from "vitest";
import { readFile, mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fixture } from "./fixtures.js";
import {
  indexResearch,
  mergeResearch,
  nameSpans,
  researchText,
  sourceKey,
  validateResearch,
} from "../shared/research.js";
import { extractArticle } from "../scripts/research-extract.js";
import { buildBriefing } from "../shared/briefing.js";
import { emptyState } from "../shared/draft.js";
import { guide, library } from "./research-fixtures.js";

describe("reviewed research integrity", () => {
  it("rejects wrong seasons, unknown players and mismatched identities", () => {
    expect(() => validateResearch(library, 2026, fixture.players)).toThrow(
      /another season/,
    );
    for (const patch of [{ playerId: 9999 }, { playerName: "Player 8" }]) {
      const bad = structuredClone(library);
      Object.assign(bad.articles[0].mentions[0], patch);
      expect(() => validateResearch(bad, 2027, fixture.players)).toThrow(
        /does not match/,
      );
    }
  });
  it("rejects executable links, credentials, impossible dates and incomplete review", () => {
    for (const patch of [
      { url: "javascript:alert(1)" },
      { url: "https://name:secret@example.com/" },
      { publishedAt: "2026-02-30" },
      { reviewedAt: "" },
      { format: "toString" },
    ]) {
      const bad = structuredClone(library);
      Object.assign(bad.articles[0], patch);
      expect(() => validateResearch(bad, 2027)).toThrow();
    }
  });
  it("detects duplicates despite ESPN URL slug or tracking changes", () => {
    const url =
      "https://www.espn.com/fantasy/basketball/story/_/id/12345/first?utm_source=mail";
    expect(sourceKey(url)).toBe(
      sourceKey(
        "https://www.espn.com/fantasy/basketball/story/_/id/12345/renamed",
      ),
    );
    expect(() =>
      validateResearch(
        {
          ...library,
          articles: [
            { ...guide, url },
            { ...guide, id: "copy", url },
          ],
        },
        2027,
      ),
    ).toThrow(/duplicate source/);
  });
  it("replaces a source's old tags and keeps other analysts' opinions", () => {
    const other = { ...guide, id: "second", url: "https://example.com/second" };
    const update = structuredClone(guide);
    update.id = "incoming-id";
    update.mentions[0].tags = ["avoid"];
    const merged = mergeResearch(
      { ...library, articles: [guide, other] },
      { ...library, articles: [update] },
    );
    expect(merged.articles).toHaveLength(2);
    expect(merged.articles.find((a) => a.url === guide.url)?.id).toBe(guide.id);
    expect(
      indexResearch(merged)
        .get(9)
        ?.flatMap((e) => e.mentions.flatMap((m) => m.tags)),
    ).toEqual(expect.arrayContaining(["target", "avoid"]));
    expect(
      merged.articles.find((a) => a.id === guide.id)?.mentions[0].tags,
    ).toEqual(["avoid"]);
    expect(() =>
      mergeResearch(library, {
        ...library,
        articles: [{ ...guide, url: "https://example.com/unrelated" }],
      }),
    ).toThrow(/already belongs/);
  });
  it("keeps context-only mentions separate from recommendation tags", () => {
    const valid = validateResearch(library, 2027, fixture.players);
    expect(indexResearch(valid).get(3)?.[0].mentions[0].tags).toEqual([
      "mention",
    ]);
    const invalid = structuredClone(library);
    invalid.articles[0].mentions[0].tags = ["mention", "avoid"];
    expect(() => validateResearch(invalid, 2027)).toThrow(/tag combination/);
    expect(researchText(guide)).toContain("Player 3 — Context only");
  });
  it("matches accents, punctuation and suffixes without guessing surnames or close names", () => {
    const text =
      "Nikola Jokić, Kel’el Ware, Jaren Jackson Jr., Jaylin Williams. Jackson and Ware.";
    const people = [
      { playerId: 1, playerName: "Nikola Jokic" },
      { playerId: 2, playerName: "Kel'el Ware" },
      { playerId: 3, playerName: "Jaren Jackson Jr." },
      { playerId: 4, playerName: "Jalen Williams" },
    ];
    const matches = nameSpans(text, people);
    expect(matches.map((m) => m.playerId)).toEqual([1, 2, 3]);
    expect(matches.map((m) => text.slice(m.start, m.end))).toEqual([
      "Nikola Jokić",
      "Kel’el Ware",
      "Jaren Jackson Jr",
    ]);
    expect(
      nameSpans("Gary Trent", [
        { playerId: 1, playerName: "Gary Trent" },
        { playerId: 2, playerName: "Gary Trent Jr.", aliases: ["Gary Trent"] },
      ]),
    ).toEqual([]);
  });
  it("includes source URLs and analyst notes in the AI briefing without changing personal flags", () => {
    const saved = emptyState(fixture.league);
    const text = buildBriefing({
      data: fixture,
      saved,
      practice: false,
      question: "Who fits?",
      generatedAt: new Date().toISOString(),
      apiOrigin: "http://localhost:3030",
      research: library,
      focusIds: [9],
    });
    expect(text).toContain(guide.url);
    expect(text).toContain("Useful at a late price.");
    expect(saved.preferences).toEqual({});
  });
});

it("extracts article HTML while excluding unrelated headlines, biographies and ads", () => {
  const html = `<html><head><meta property="og:title" content="An original test guide"><script type="application/ld+json">{"@type":"NewsArticle","author":{"name":"Actual Author"},"datePublished":"2026-10-10T12:00:00Z"}</script></head><body><aside><div class="author">Unrelated Reporter</div><p>Player 2</p></aside><div class="article-body"><div class="article-meta"><div class="author">Actual Author</div></div><h3>Targets</h3><p><a href="https://www.espn.com/nba/player/_/id/9/player-nine">Player 9</a> could gain minutes. ${"Original fixture context. ".repeat(12)}</p><p>Player 3 is a teammate; Player 30 is outside this fixture.</p><aside class="inline"><p>Player 2 advertisement</p></aside><p>Another player has an <a href="https://www.espn.com/nba/player/_/id/9999/unknown">unknown identity</a>.</p></div></body></html>`;
  const result = extractArticle(html, guide.url, fixture.players);
  expect(result.authors).toEqual(["Actual Author"]);
  expect(result.publishedAt).toBe("2026-10-10");
  expect(result.candidates.map((p) => p.playerId)).toEqual([9, 3]);
  expect(result.unresolved[0].id).toBe(9999);
  expect(result.blocks.map((b) => b.text).join(" ")).not.toContain(
    "advertisement",
  );
  expect(() =>
    extractArticle("<p>Please sign in</p>", guide.url, fixture.players),
  ).toThrow(/No article body/);
});

it("imports atomically, previews without changing the library and preserves it after invalid input", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "draftroom-research-test-"));
  const target = path.join(dir, "library.json"),
    input = path.join(dir, "incoming.json"),
    pool = path.join(dir, "pool.json");
  const empty = JSON.stringify({ ...library, articles: [] });
  const run = (...args: string[]) =>
    execFileSync(
      process.execPath,
      [
        "--import",
        "tsx",
        "scripts/research.ts",
        "import",
        input,
        "--library",
        target,
        "--pool",
        pool,
        ...args,
      ],
      { cwd: process.cwd(), encoding: "utf8", stdio: "pipe" },
    );
  try {
    await writeFile(target, empty);
    await writeFile(input, JSON.stringify(library));
    await writeFile(pool, JSON.stringify(fixture));
    run();
    expect(await readFile(target, "utf8")).toBe(empty);
    run("--write");
    const written = await readFile(target, "utf8");
    expect(JSON.parse(written).articles).toHaveLength(1);
    run("--write");
    expect(JSON.parse(await readFile(target, "utf8")).articles).toHaveLength(1);
    await writeFile(input, JSON.stringify({ ...library, season: 2026 }));
    expect(() => run("--write")).toThrow();
    expect(await readFile(target, "utf8")).toBe(written);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}, 15000);
