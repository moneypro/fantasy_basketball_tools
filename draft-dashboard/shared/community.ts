import type { Player } from "./types.js";
import { normalizeName } from "./research.js";

export const communities = ["fantasybball", "nba"] as const;
export type CommunityName = (typeof communities)[number];
export type CommunityRating = 1 | 2 | 3 | 4 | 5;
export const ratingLabels: Record<CommunityRating, string> = {
  1: "Unfavorable",
  2: "Slightly unfavorable",
  3: "Mixed / neutral",
  4: "Slightly favorable",
  5: "Favorable",
};
export const communityPolicy = {
  maxPostsPerFeed: 25,
  cooldownHours: 6,
  refusalBackoffHours: 24,
  retentionDays: 14,
  maxStoredPosts: 300,
} as const;
export interface CommunityMention {
  playerId: number;
  playerName: string;
  rating: CommunityRating | null;
  note: string;
  aliases?: string[];
}
export interface CommunityPost {
  id: string;
  subreddit: CommunityName;
  title: string;
  url: string;
  publishedAt: string;
  collectedAt: string;
  reviewedAt: string;
  contentHash: string;
  rating: CommunityRating;
  confidence: "low" | "medium" | "high";
  basis: "title" | "title-and-body";
  summary: string;
  mentions: CommunityMention[];
}
export interface CommunityLibrary {
  version: 1;
  season: number;
  posts: CommunityPost[];
}
export interface FeedStatus {
  subreddit: CommunityName;
  attemptedAt: string | null;
  fetchedAt: string | null;
  status: "not-fetched" | "ok" | "not-modified" | "blocked" | "error";
  received: number;
  message: string;
}
export interface CommunitySnapshot extends CommunityLibrary {
  feeds: FeedStatus[];
  nextFetchAt: string | null;
  pendingCount: number;
  collectedCount: number;
}
export interface PlayerCommunity {
  post: CommunityPost;
  mention: CommunityMention;
}
export const emptyCommunity = (season: number): CommunitySnapshot => ({
  version: 1,
  season,
  posts: [],
  feeds: communities.map((subreddit) => ({
    subreddit,
    attemptedAt: null,
    fetchedAt: null,
    status: "not-fetched",
    received: 0,
    message: "",
  })),
  nextFetchAt: null,
  pendingCount: 0,
  collectedCount: 0,
});

export function redditIdentity(value: string): {
  id: string;
  subreddit: CommunityName;
} {
  const url = new URL(value);
  const match = /^\/r\/([^/]+)\/comments\/([a-z0-9]+)(?:\/|$)/i.exec(
    url.pathname,
  );
  if (
    url.protocol !== "https:" ||
    !["www.reddit.com", "reddit.com", "old.reddit.com"].includes(
      url.hostname,
    ) ||
    url.username ||
    url.password ||
    !match ||
    !communities.includes(match[1].toLowerCase() as CommunityName)
  )
    throw new Error("Community: expected a post from r/fantasybball or r/nba.");
  return {
    id: match[2].toLowerCase(),
    subreddit: match[1].toLowerCase() as CommunityName,
  };
}

export function validateCommunity(
  value: unknown,
  season: number,
  players?: Pick<Player, "id" | "name">[],
): CommunityLibrary {
  const fail = (message: string): never => {
    throw new Error(`Community: ${message}`);
  };
  const object = (v: unknown): Record<string, unknown> => {
    if (!v || typeof v !== "object" || Array.isArray(v))
      return fail("expected object");
    return v as Record<string, unknown>;
  };
  const text = (v: unknown, max: number) => {
    if (typeof v !== "string" || !v.trim() || v.length > max)
      return fail("missing or invalid text");
    return v.trim();
  };
  const date = (v: unknown) => {
    const s = text(v, 40);
    if (!/^\d{4}-\d{2}-\d{2}T/.test(s) || !Number.isFinite(Date.parse(s)))
      return fail("invalid date");
    return s;
  };
  const rating = (v: unknown): CommunityRating => {
    if (!Number.isInteger(v) || Number(v) < 1 || Number(v) > 5)
      return fail("rating must be 1–5");
    return v as CommunityRating;
  };
  const root = object(value);
  if (
    root.version !== 1 ||
    root.season !== season ||
    !Array.isArray(root.posts) ||
    root.posts.length > communityPolicy.maxStoredPosts
  )
    return fail("invalid library or another season");
  const pool = players ? new Map(players.map((p) => [p.id, p.name])) : null;
  const seen = new Set<string>();
  const posts = root.posts.map((raw) => {
    const p = object(raw),
      url = text(p.url, 2000),
      identity = redditIdentity(url);
    if (
      p.id !== identity.id ||
      p.subreddit !== identity.subreddit ||
      seen.has(identity.id)
    )
      return fail("duplicate or mismatched post identity");
    seen.add(identity.id);
    if (
      !["low", "medium", "high"].includes(String(p.confidence)) ||
      !["title", "title-and-body"].includes(String(p.basis))
    )
      return fail("invalid confidence or evidence basis");
    const contentHash = text(p.contentHash, 64);
    if (!/^[a-f0-9]{64}$/.test(contentHash))
      return fail("invalid content hash");
    if (!Array.isArray(p.mentions) || p.mentions.length > 100)
      return fail("invalid mentions");
    const ids = new Set<number>();
    const mentions = p.mentions.map((rawMention) => {
      const m = object(rawMention),
        playerName = text(m.playerName, 100),
        playerId = Number(m.playerId);
      if (
        !Number.isSafeInteger(m.playerId) ||
        playerId < 1 ||
        ids.has(playerId) ||
        (pool &&
          (!pool.has(playerId) ||
            normalizeName(pool.get(playerId)!) !== normalizeName(playerName)))
      )
        return fail(`unknown, duplicated or mismatched player: ${playerName}`);
      ids.add(playerId);
      if (
        m.aliases !== undefined &&
        (!Array.isArray(m.aliases) || m.aliases.length > 10)
      )
        return fail("invalid aliases");
      const aliases =
        m.aliases === undefined
          ? undefined
          : (m.aliases as unknown[]).map((v) => text(v, 100));
      return {
        playerId,
        playerName,
        rating: m.rating === null ? null : rating(m.rating),
        note: text(m.note, 1000),
        ...(aliases ? { aliases } : {}),
      };
    });
    return {
      id: identity.id,
      subreddit: identity.subreddit,
      url,
      title: text(p.title, 500),
      publishedAt: date(p.publishedAt),
      collectedAt: date(p.collectedAt),
      reviewedAt: date(p.reviewedAt),
      contentHash,
      rating: rating(p.rating),
      confidence: p.confidence as CommunityPost["confidence"],
      basis: p.basis as CommunityPost["basis"],
      summary: text(p.summary, 2000),
      mentions,
    };
  });
  return { version: 1, season, posts };
}

export function indexCommunity(
  library: CommunityLibrary,
): Map<number, PlayerCommunity[]> {
  const result = new Map<number, PlayerCommunity[]>();
  for (const post of library.posts)
    for (const mention of post.mentions)
      result.set(mention.playerId, [
        ...(result.get(mention.playerId) ?? []),
        { post, mention },
      ]);
  return result;
}
export function communityText(library: CommunityLibrary): string {
  return [
    "DRAFTROOM — COMMUNITY NOTES",
    "Ratings describe the sampled post's fantasy outlook, not votes or subreddit consensus. RSS titles/body only; comments were not collected.",
    "1 Unfavorable · 2 Slightly unfavorable · 3 Mixed / neutral · 4 Slightly favorable · 5 Favorable",
    "",
    ...library.posts.flatMap((p) => [
      p.title,
      `r/${p.subreddit} | ${p.publishedAt} | ${p.url}`,
      `Post outlook: ${p.rating}/5 ${ratingLabels[p.rating]} | ${p.confidence} confidence | ${p.basis === "title" ? "Title only" : "Title + post text"}`,
      p.summary,
      ...p.mentions.map(
        (m) =>
          `${m.playerName}: ${m.rating === null ? "Context only" : `${m.rating}/5 ${ratingLabels[m.rating]}`} — ${m.note}`,
      ),
      "",
    ]),
  ].join("\n");
}
