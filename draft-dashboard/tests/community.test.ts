import { describe, it, expect, vi } from "vitest";
import { readFile, writeFile, mkdtemp, rm } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { tmpdir } from "node:os";
import {
  collectFeeds,
  emptyCache,
  parseFeed,
  type FeedCache,
} from "../scripts/community-feed.js";
import {
  validateCommunity,
  indexCommunity,
  communityText,
} from "../shared/community.js";
import { readCommunity } from "../server/community.js";
import { buildBriefing } from "../shared/briefing.js";
import { emptyState } from "../shared/draft.js";
import { fixture } from "./fixtures.js";
import { library as guides } from "./research-fixtures.js";
import {
  communityNow as now,
  communityPost,
  communityFixture,
} from "./community-fixtures.js";

const atom = (sub = "fantasybball", count = 1) =>
  `<feed xmlns="http://www.w3.org/2005/Atom">${Array.from({ length: count }, (_, i) => `<entry><title>Player 9 is interesting ${i}</title><id>t3_post${i}</id><link rel="alternate" href="https://www.reddit.com/r/${sub}/comments/post${i}/discussion/"/><published>2026-10-15T20:00:00Z</published><content type="html">&lt;table&gt;&lt;tr&gt;&lt;td&gt;&lt;div class="md"&gt;Player 9 may gain minutes.&lt;script&gt;bad()&lt;/script&gt;&lt;/div&gt;&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt;submitted by somebody [comments]</content></entry>`).join("")}</feed>`;
const persist = vi.fn(async (_cache: FeedCache) => {});
const cacheWithPost = () => ({
  ...emptyCache(2027),
  posts: [{ ...communityPost, body: "Saved original RSS text" }],
});

describe("lightweight RSS collection", () => {
  it("caps the sample and extracts post text without author boilerplate or scripts", () => {
    const posts = parseFeed(
      atom("fantasybball", 40),
      "fantasybball",
      new Date(now).toISOString(),
    );
    expect(posts).toHaveLength(25);
    expect(posts[0].body).toBe("Player 9 may gain minutes.");
    expect(
      parseFeed(atom("nba"), "fantasybball", new Date(now).toISOString()),
    ).toEqual([]);
    expect(() => parseFeed("<html>Blocked</html>", "fantasybball", "")).toThrow(
      /Atom/,
    );
  });
  it("reserves a cooldown before requests, makes exactly two anonymous GETs and honors reset headers", async () => {
    const events: string[] = [];
    const sleep = vi.fn(async (ms: number) => {
      events.push(`sleep:${ms}`);
    });
    const request = vi.fn<typeof fetch>(async (url, options) => {
      events.push("request");
      expect(events[0]).toBe("persist");
      expect(options?.credentials).toBe("omit");
      expect(options?.redirect).toBe("manual");
      const headers = new Headers(options?.headers);
      expect(headers.has("authorization")).toBe(false);
      expect(headers.has("cookie")).toBe(false);
      expect(String(url)).toMatch(
        /\/r\/(fantasybball|nba)\/new\.rss\?limit=25$/,
      );
      return new Response(
        atom(String(url).includes("/nba/") ? "nba" : "fantasybball"),
        {
          headers: {
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "20",
            etag: '"rss-v1"',
          },
        },
      );
    });
    const result = await collectFeeds(
      emptyCache(2027),
      async (c) => {
        events.push("persist");
        expect(Date.parse(c.nextFetchAt!)).toBe(now + 6 * 3600000);
      },
      { fetch: request, now: () => now, sleep },
    );
    expect(result.requests).toBe(2);
    expect(request).toHaveBeenCalledTimes(2);
    expect(sleep).toHaveBeenCalledWith(21000);
    expect(result.cache.feeds.every((f) => f.status === "ok")).toBe(true);
    const skipped = await collectFeeds(result.cache, persist, {
      fetch: request,
      now: () => now + 1000,
      sleep,
    });
    expect(skipped.requests).toBe(0);
    expect(skipped.skipped).toBe(true);
    expect(request).toHaveBeenCalledTimes(2);
  });
  it.each([403, 429])(
    "stops the whole batch on HTTP %s without retry or losing cached evidence",
    async (status) => {
      const request = vi.fn<typeof fetch>(
        async () =>
          new Response("refused", {
            status,
            headers: { "retry-after": "172800" },
          }),
      );
      const before = cacheWithPost();
      const result = await collectFeeds(before, persist, {
        fetch: request,
        now: () => now,
        sleep: vi.fn(),
      });
      expect(request).toHaveBeenCalledTimes(1);
      expect(result.cache.posts).toEqual(before.posts);
      expect(result.cache.feeds[0].status).toBe("blocked");
      expect(result.cache.feeds[1].attemptedAt).toBeNull();
      expect(Date.parse(result.cache.nextFetchAt!)).toBe(now + 48 * 3600000);
    },
  );
  it("does not retry a redirect, network failure, invalid RSS or server error", async () => {
    for (const response of [
      () => Promise.reject(new Error("offline")),
      () => Promise.resolve(new Response("move", { status: 302 })),
      () => Promise.resolve(new Response("HTML challenge")),
      () => Promise.resolve(new Response("unavailable", { status: 503 })),
    ]) {
      const request = vi.fn<typeof fetch>(response);
      const result = await collectFeeds(cacheWithPost(), persist, {
        fetch: request,
        now: () => now,
        sleep: vi.fn(),
      });
      expect(request).toHaveBeenCalledTimes(1);
      expect(result.cache.posts).toHaveLength(1);
      expect(result.cache.feeds[0].status).toBe("error");
    }
  });
  it("stops instead of waiting a long reset and supports conditional unchanged responses", async () => {
    const cache = cacheWithPost();
    cache.feeds[0].etag = '"old"';
    const request = vi.fn<typeof fetch>(async (_url, options) => {
      expect(new Headers(options?.headers).get("if-none-match")).toBe('"old"');
      return new Response(null, {
        status: 304,
        headers: { "x-ratelimit-remaining": "0", "x-ratelimit-reset": "72000" },
      });
    });
    const sleep = vi.fn();
    const result = await collectFeeds(cache, persist, {
      fetch: request,
      now: () => now,
      sleep,
    });
    expect(result.requests).toBe(1);
    expect(sleep).not.toHaveBeenCalled();
    expect(result.cache.posts).toEqual(cache.posts);
    expect(result.cache.feeds[0].status).toBe("not-modified");
    expect(Date.parse(result.cache.nextFetchAt!)).toBeGreaterThanOrEqual(
      now + 72000000,
    );
  });
  it("makes no request if the cooldown is corrupt or cannot be persisted", async () => {
    const request = vi.fn<typeof fetch>();
    await expect(
      collectFeeds({ ...emptyCache(2027), nextFetchAt: "broken" }, persist, {
        fetch: request,
      }),
    ).rejects.toThrow(/cooldown/);
    await expect(
      collectFeeds(
        emptyCache(2027),
        async () => {
          throw new Error("disk full");
        },
        { fetch: request },
      ),
    ).rejects.toThrow(/disk full/);
    expect(request).not.toHaveBeenCalled();
  });
});

describe("community evidence and opinions", () => {
  it("validates source identity, player identity, review and score boundaries", () => {
    expect(
      validateCommunity(communityFixture, 2027, fixture.players).posts,
    ).toHaveLength(2);
    for (const patch of [
      { rating: 0 },
      { rating: 6 },
      { rating: 2.5 },
      { url: "https://evil.test/r/nba/comments/sample1/" },
      { url: "https://www.reddit.com/r/other/comments/sample1/" },
      { subreddit: "nba" },
      { reviewedAt: "" },
    ]) {
      const bad = structuredClone(communityFixture);
      Object.assign(bad.posts[0], patch);
      expect(() => validateCommunity(bad, 2027, fixture.players)).toThrow();
    }
    const bad = structuredClone(communityFixture);
    bad.posts[0].mentions[0].playerName = "Player 8";
    expect(() => validateCommunity(bad, 2027, fixture.players)).toThrow(
      /mismatched/,
    );
    expect(() => validateCommunity(communityFixture, 2026)).toThrow(/season/);
  });
  it("keeps player-specific disagreement and context-only mentions separate from professional advice", () => {
    expect(
      indexCommunity(communityFixture)
        .get(9)
        ?.map((p) => p.mention.rating),
    ).toEqual([4, 2]);
    expect(
      indexCommunity(communityFixture).get(3)?.[0].mention.rating,
    ).toBeNull();
    const saved = emptyState(fixture.league);
    const briefing = buildBriefing({
      data: fixture,
      saved,
      practice: false,
      question: "Who fits?",
      apiOrigin: "http://localhost:3030",
      generatedAt: new Date(now).toISOString(),
      focusIds: [9],
      research: guides,
      community: communityFixture,
    });
    expect(briefing).toContain(
      "COMMUNITY NOTES — SEPARATE FROM PROFESSIONAL GUIDES",
    );
    expect(briefing).toContain("4/5 Slightly favorable");
    expect(briefing).toContain("2/5 Slightly unfavorable");
    expect(briefing).toContain(communityPost.url);
    expect(saved.preferences).toEqual({});
    expect(communityText(communityFixture)).toContain("Player 3: Context only");
  });
  it("serves only reviewed current evidence and retains notes through feed errors", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "community-api-"));
    try {
      const cache = cacheWithPost();
      await writeFile(
        path.join(dir, "library.json"),
        JSON.stringify({ ...communityFixture, posts: [communityPost] }),
      );
      await writeFile(path.join(dir, "cache.json"), JSON.stringify(cache));
      expect((await readCommunity(2027, dir, now)).posts).toHaveLength(1);
      cache.feeds[0].status = "blocked";
      cache.feeds[0].message = "HTTP 429";
      await writeFile(path.join(dir, "cache.json"), JSON.stringify(cache));
      const retained = await readCommunity(2027, dir, now);
      expect(retained.posts).toHaveLength(1);
      expect(retained.feeds[0].status).toBe("blocked");
      expect(JSON.stringify(retained)).not.toContain("Saved original RSS text");
      cache.posts[0].contentHash = "b".repeat(64);
      await writeFile(path.join(dir, "cache.json"), JSON.stringify(cache));
      const changed = await readCommunity(2027, dir, now);
      expect(changed.posts).toHaveLength(0);
      expect(changed.pendingCount).toBe(1);
      const expired = await readCommunity(2027, dir, now + 15 * 86400000);
      expect(expired.posts).toHaveLength(0);
      expect(expired.collectedCount).toBe(0);
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });
  it("imports reviewed evidence atomically, deduplicates updates and rejects changed evidence", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "community-import-"));
    const libraryFile = path.join(dir, "library.json"),
      input = path.join(dir, "review.json"),
      pool = path.join(dir, "pool.json");
    const cache = cacheWithPost();
    const currentDate = new Date().toISOString();
    cache.posts[0].publishedAt = currentDate;
    const incoming = {
      version: 1,
      season: 2027,
      posts: [{ ...communityPost, publishedAt: currentDate }],
    };
    const run = (...args: string[]) =>
      execFileSync(
        process.execPath,
        [
          "--import",
          "tsx",
          "scripts/community.ts",
          "import",
          "--input",
          input,
          "--dir",
          dir,
          "--pool",
          pool,
          ...args,
        ],
        { encoding: "utf8", stdio: "pipe" },
      );
    try {
      await writeFile(path.join(dir, "cache.json"), JSON.stringify(cache));
      await writeFile(pool, JSON.stringify(fixture));
      await writeFile(input, JSON.stringify(incoming));
      await writeFile(
        libraryFile,
        JSON.stringify({ version: 1, season: 2027, posts: [] }),
      );
      run();
      expect(JSON.parse(await readFile(libraryFile, "utf8")).posts).toEqual([]);
      run("--write");
      const valid = await readFile(libraryFile, "utf8");
      run("--write");
      expect(
        JSON.parse(await readFile(libraryFile, "utf8")).posts,
      ).toHaveLength(1);
      incoming.posts[0].contentHash = "f".repeat(64);
      await writeFile(input, JSON.stringify(incoming));
      expect(() => run("--write")).toThrow();
      expect(await readFile(libraryFile, "utf8")).toBe(valid);
      await writeFile(path.join(dir, "community.lock"), "");
      expect(() => run("--write")).toThrow();
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  }, 15000);
});
