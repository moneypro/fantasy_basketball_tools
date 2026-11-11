import { readFile } from "node:fs/promises";
import path from "node:path";
import {
  communityPolicy,
  emptyCommunity,
  validateCommunity,
  type CommunitySnapshot,
} from "../shared/community.js";
import type { FeedCache } from "../scripts/community-feed.js";

export async function readCommunity(
  season: number,
  directory = process.env.COMMUNITY_DIR ?? "community",
  now = Date.now(),
): Promise<CommunitySnapshot> {
  const read = async (file: string) => {
    try {
      return JSON.parse(await readFile(path.join(directory, file), "utf8"));
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code === "ENOENT") return null;
      throw e;
    }
  };
  try {
    const library = validateCommunity(
      (await read("library.json")) ?? { version: 1, season, posts: [] },
      season,
    );
    const cache: FeedCache | null = await read("cache.json");
    if (
      cache &&
      (cache.version !== 1 ||
        cache.season !== season ||
        !Array.isArray(cache.posts) ||
        !Array.isArray(cache.feeds))
    )
      throw new Error("Invalid community cache");
    const recent = (p: { publishedAt: string }) =>
      Date.parse(p.publishedAt) >=
        now - communityPolicy.retentionDays * 86400000 &&
      Date.parse(p.publishedAt) <= now + 3600000;
    const collected = cache?.posts.filter(recent) ?? [];
    const current = new Map(collected.map((p) => [p.id, p]));
    const posts = library.posts.filter(
      (p) =>
        recent(p) &&
        (!cache || current.get(p.id)?.contentHash === p.contentHash),
    );
    return {
      ...emptyCommunity(season),
      posts,
      feeds: cache
        ? cache.feeds.map(({ etag, lastModified, ...feed }) => feed)
        : emptyCommunity(season).feeds,
      nextFetchAt: cache?.nextFetchAt ?? null,
      collectedCount: cache ? collected.length : posts.length,
      pendingCount: cache ? collected.length - posts.length : 0,
    };
  } catch {
    throw new Error(
      "Draftroom could not read the community notes. Check the saved community data.",
    );
  }
}
