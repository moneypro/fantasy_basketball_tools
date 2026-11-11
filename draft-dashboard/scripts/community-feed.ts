import { load } from "cheerio";
import { createHash } from "node:crypto";
import {
  communities,
  communityPolicy,
  redditIdentity,
  type CommunityName,
  type FeedStatus,
} from "../shared/community.js";

export interface CollectedPost {
  id: string;
  subreddit: CommunityName;
  title: string;
  body: string;
  url: string;
  publishedAt: string;
  collectedAt: string;
  contentHash: string;
}
export interface FeedCache {
  version: 1;
  season: number;
  nextFetchAt: string | null;
  feeds: (FeedStatus & { etag?: string; lastModified?: string })[];
  posts: CollectedPost[];
}
export const emptyCache = (season: number): FeedCache => ({
  version: 1,
  season,
  nextFetchAt: null,
  feeds: communities.map((subreddit) => ({
    subreddit,
    attemptedAt: null,
    fetchedAt: null,
    status: "not-fetched",
    received: 0,
    message: "",
  })),
  posts: [],
});
export function validateFeedCache(value: FeedCache, season: number): FeedCache {
  if (
    value.version !== 1 ||
    value.season !== season ||
    !Array.isArray(value.feeds) ||
    value.feeds.length !== communities.length ||
    !Array.isArray(value.posts) ||
    value.posts.length > communityPolicy.maxStoredPosts
  )
    throw new Error("Invalid community cache; collection stopped.");
  if (
    value.nextFetchAt !== null &&
    (typeof value.nextFetchAt !== "string" ||
      !Number.isFinite(Date.parse(value.nextFetchAt)))
  )
    throw new Error("Invalid saved cooldown; collection stopped.");
  for (const sub of communities) {
    const feeds = value.feeds.filter((f) => f.subreddit === sub);
    if (feeds.length !== 1)
      throw new Error("Invalid feed identities; collection stopped.");
    const f = feeds[0];
    for (const date of [f.attemptedAt, f.fetchedAt])
      if (
        date !== null &&
        (typeof date !== "string" || !Number.isFinite(Date.parse(date)))
      )
        throw new Error("Invalid saved feed timestamp; collection stopped.");
  }
  for (const p of value.posts)
    if (
      typeof p.body !== "string" ||
      typeof p.title !== "string" ||
      !Number.isFinite(Date.parse(p.publishedAt)) ||
      redditIdentity(p.url).id !== p.id ||
      !communities.includes(p.subreddit)
    )
      throw new Error("Invalid saved post; collection stopped.");
  return value;
}
const hour = 3_600_000;
export const feedUrl = (subreddit: CommunityName) =>
  `https://www.reddit.com/r/${subreddit}/new.rss?limit=${communityPolicy.maxPostsPerFeed}`;
export function parseFeed(
  xml: string,
  subreddit: CommunityName,
  collectedAt: string,
): CollectedPost[] {
  const $ = load(xml, { xml: true });
  if (!$("feed").length) throw new Error("Response was not an Atom RSS feed.");
  const result: CollectedPost[] = [];
  $("feed > entry")
    .slice(0, communityPolicy.maxPostsPerFeed)
    .each((_, entry) => {
      const title = $(entry).find("title").first().text().trim();
      const url =
        $(entry).find('link[rel="alternate"]').attr("href") ??
        $(entry).find("link").first().attr("href") ??
        "";
      let identity;
      try {
        identity = redditIdentity(url);
      } catch {
        return;
      }
      const published =
        $(entry).find("published").text() || $(entry).find("updated").text();
      if (
        identity.subreddit !== subreddit ||
        !title ||
        !Number.isFinite(Date.parse(published))
      )
        return;
      const html = load($(entry).find("content").text());
      html("script,style,iframe,video").remove();
      // Reddit wraps the original post text in .md; the remainder is author/link boilerplate.
      const body = html(".md")
        .map((_, el) => html(el).text().trim())
        .get()
        .join("\n")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 20000);
      const cleanTitle = title.slice(0, 500);
      result.push({
        ...identity,
        title: cleanTitle,
        body,
        url,
        publishedAt: new Date(published).toISOString(),
        collectedAt,
        contentHash: createHash("sha256")
          .update(cleanTitle + "\n" + body)
          .digest("hex"),
      });
    });
  return [...new Map(result.map((p) => [p.id, p])).values()];
}
export function retainPosts(
  posts: CollectedPost[],
  now: number,
): CollectedPost[] {
  return posts
    .filter(
      (p) =>
        Date.parse(p.publishedAt) >=
          now - communityPolicy.retentionDays * 24 * hour &&
        Date.parse(p.publishedAt) <= now + hour,
    )
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
    .slice(0, communityPolicy.maxStoredPosts);
}
const finiteHeader = (headers: Headers, key: string) => {
  const raw = headers.get(key);
  if (raw === null) return null;
  const n = Number(raw);
  return Number.isFinite(n) && n >= 0 ? n : null;
};
function retryDelay(headers: Headers, now: number): number {
  const raw = headers.get("retry-after");
  const seconds = raw === null ? NaN : Number(raw);
  return Number.isFinite(seconds)
    ? Math.max(0, seconds * 1000)
    : Math.max(0, (Date.parse(raw ?? "") || now) - now);
}
async function limitedText(response: Response): Promise<string> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("Empty RSS response");
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > 2_000_000)
        throw new Error("RSS response exceeded the size limit");
      chunks.push(value);
    }
  } finally {
    await reader.cancel();
  }
  return Buffer.concat(chunks).toString("utf8");
}

/** At most two credential-free GETs. Reserve the cooldown on disk BEFORE any request. */
export async function collectFeeds(
  cache: FeedCache,
  persist: (value: FeedCache) => Promise<void>,
  dependencies: {
    fetch?: typeof fetch;
    now?: () => number;
    sleep?: (ms: number) => Promise<void>;
  } = {},
): Promise<{ cache: FeedCache; requests: number; skipped: boolean }> {
  const request = dependencies.fetch ?? fetch,
    now = dependencies.now ?? Date.now,
    sleep =
      dependencies.sleep ??
      ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  const result = structuredClone(validateFeedCache(cache, cache.season));
  const started = now();
  if (result.nextFetchAt && Date.parse(result.nextFetchAt) > started)
    return { cache: result, requests: 0, skipped: true };
  result.posts = retainPosts(result.posts, started);
  result.nextFetchAt = new Date(
    started + communityPolicy.cooldownHours * hour,
  ).toISOString();
  await persist(result);
  let requests = 0;
  for (const subreddit of communities) {
    const state = result.feeds.find((f) => f.subreddit === subreddit)!;
    state.attemptedAt = new Date(now()).toISOString();
    try {
      const headers: Record<string, string> = {
        "User-Agent": "draftroom/1.0 (personal basketball RSS reader; no auth)",
        Accept: "application/atom+xml, application/rss+xml",
      };
      if (state.etag) headers["If-None-Match"] = state.etag;
      if (state.lastModified) headers["If-Modified-Since"] = state.lastModified;
      requests++;
      const response = await request(feedUrl(subreddit), {
        headers,
        credentials: "omit",
        redirect: "manual",
        signal: AbortSignal.timeout(20_000),
      });
      if (response.status === 403 || response.status === 429) {
        state.status = "blocked";
        state.message = `Reddit returned HTTP ${response.status}; collection stopped. Cached notes remain available.`;
        const wait = Math.max(
          communityPolicy.refusalBackoffHours * hour,
          retryDelay(response.headers, now()),
          (finiteHeader(response.headers, "x-ratelimit-reset") ?? 0) * 1000,
        );
        result.nextFetchAt = new Date(now() + wait).toISOString();
        await response.body?.cancel();
        await persist(result);
        break;
      }
      if (response.status === 304) {
        state.status = "not-modified";
        state.fetchedAt = new Date(now()).toISOString();
        state.message = "Feed unchanged.";
        await response.body?.cancel();
      } else {
        if (!response.ok) {
          await response.body?.cancel();
          throw new Error(`HTTP ${response.status}; no retry attempted.`);
        }
        const posts = parseFeed(
          await limitedText(response),
          subreddit,
          new Date(now()).toISOString(),
        );
        state.status = "ok";
        state.received = posts.length;
        state.fetchedAt = new Date(now()).toISOString();
        state.message = posts.length
          ? "Recent RSS sample."
          : "Feed returned no readable posts.";
        state.etag = response.headers.get("etag") ?? undefined;
        state.lastModified = response.headers.get("last-modified") ?? undefined;
        result.posts = retainPosts(
          [
            ...new Map(
              [...result.posts, ...posts].map((p) => [p.id, p]),
            ).values(),
          ],
          now(),
        );
      }
      await persist(result);
      const remaining = finiteHeader(response.headers, "x-ratelimit-remaining"),
        reset = finiteHeader(response.headers, "x-ratelimit-reset") ?? 0;
      const wait = Math.max(
        10_000,
        remaining !== null && remaining < 1 ? (reset + 1) * 1000 : 0,
        retryDelay(response.headers, now()),
      );
      if (wait > 60_000) {
        result.nextFetchAt = new Date(
          Math.max(Date.parse(result.nextFetchAt!), now() + wait),
        ).toISOString();
        await persist(result);
        break;
      }
      if (subreddit !== communities.at(-1)) await sleep(wait);
    } catch (error) {
      state.status = "error";
      state.message =
        error instanceof Error ? error.message : "RSS unavailable";
      await persist(result);
      break;
    }
  }
  return { cache: result, requests, skipped: false };
}
