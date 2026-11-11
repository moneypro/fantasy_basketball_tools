import type { Player } from "./types.js";

export const researchTags = [
  "target",
  "avoid",
  "sleeper",
  "breakout",
  "bust",
  "watch",
  "mention",
] as const;
export type ResearchTag = (typeof researchTags)[number];
export const tagLabels: Record<ResearchTag, string> = {
  target: "Draft target",
  avoid: "Do not draft",
  sleeper: "Sleeper",
  breakout: "Breakout",
  bust: "Bust risk",
  watch: "Watch",
  mention: "Context only",
};
export const formatLabels = {
  points: "Points",
  categories: "Categories",
  both: "Points + categories",
  general: "General strategy",
};
export interface ResearchMention {
  playerId: number;
  playerName: string;
  tags: ResearchTag[];
  note: string;
  section: string;
  analyst?: string;
  aliases?: string[];
}
export interface ResearchArticle {
  id: string;
  season: number;
  title: string;
  url: string;
  publisher: string;
  authors: string[];
  publishedAt: string;
  reviewedAt: string;
  format: keyof typeof formatLabels;
  summary: string;
  mentions: ResearchMention[];
}
export interface ResearchLibrary {
  version: 1;
  season: number;
  articles: ResearchArticle[];
}
export interface PlayerResearch {
  article: ResearchArticle;
  mentions: ResearchMention[];
}
export const normalizeName = (name: string) =>
  name
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();

export function sourceKey(value: string): string {
  const url = new URL(value);
  if (
    !["https:", "http:"].includes(url.protocol) ||
    url.username ||
    url.password
  )
    throw new Error(
      "Source links must be public HTTP or HTTPS URLs without credentials.",
    );
  const espnId = /\/id\/(\d+)/.exec(url.pathname)?.[1];
  if (/(^|\.)espn\.com$/.test(url.hostname) && espnId) return `espn:${espnId}`;
  url.hash = "";
  for (const key of [...url.searchParams.keys()])
    if (/^utm_|^(fbclid|gclid)$/.test(key)) url.searchParams.delete(key);
  return url.toString().replace(/\/$/, "");
}

/** Reject a whole invalid import; never silently drop a player's annotation. */
export function validateResearch(
  value: unknown,
  season: number,
  players?: Pick<Player, "id" | "name">[],
): ResearchLibrary {
  const fail = (message: string): never => {
    throw new Error(`Research: ${message}`);
  };
  const object = (v: unknown): Record<string, unknown> => {
    if (!v || typeof v !== "object" || Array.isArray(v))
      return fail("expected an object.");
    return v as Record<string, unknown>;
  };
  const str = (
    v: unknown,
    label: string,
    max: number,
    empty = false,
  ): string => {
    if (typeof v !== "string" || (!empty && !v.trim()) || v.length > max)
      return fail(`invalid ${label}.`);
    return v.trim();
  };
  const arr = (v: unknown, label: string, max: number): unknown[] => {
    if (!Array.isArray(v) || v.length > max) return fail(`invalid ${label}.`);
    return v;
  };
  const root = object(value);
  if (root.version !== 1 || root.season !== season)
    return fail(
      "this library belongs to another season or uses an unsupported version.",
    );
  const playerMap = players
    ? new Map(players.map((p) => [p.id, p]))
    : undefined;
  const ids = new Set<string>(),
    urls = new Set<string>();
  const articles = arr(root.articles, "articles", 500).map((raw) => {
    const a = object(raw);
    const id = str(a.id, "article ID", 100);
    if (!/^[a-z0-9][a-z0-9-]*$/.test(id) || ids.has(id))
      return fail(`duplicate or invalid article ID ${id}.`);
    ids.add(id);
    if (a.season !== season) return fail(`${id} belongs to another season.`);
    const url = str(a.url, "source URL", 2000),
      key = sourceKey(url);
    if (urls.has(key)) return fail(`duplicate source ${url}.`);
    urls.add(key);
    const publishedAt = str(a.publishedAt, "publication date", 10);
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(publishedAt) ||
      !Number.isFinite(Date.parse(publishedAt)) ||
      new Date(publishedAt).toISOString().slice(0, 10) !== publishedAt
    )
      return fail(`invalid publication date in ${id}.`);
    const reviewedAt = str(a.reviewedAt, "review date", 40);
    if (!Number.isFinite(Date.parse(reviewedAt)))
      return fail(`invalid review date in ${id}.`);
    if (typeof a.format !== "string" || !Object.hasOwn(formatLabels, a.format))
      return fail(`invalid scoring format in ${id}.`);
    const authors = arr(a.authors, "authors", 30).map((v) =>
      str(v, "author", 120),
    );
    if (!authors.length) return fail(`missing author in ${id}.`);
    const mentionKeys = new Set<string>();
    const mentions = arr(a.mentions, "mentions", 1500).map((rawMention) => {
      const m = object(rawMention);
      if (!Number.isSafeInteger(m.playerId) || Number(m.playerId) <= 0)
        return fail(`invalid player ID in ${id}.`);
      const playerId = Number(m.playerId),
        playerName = str(m.playerName, "player name", 100);
      const player = playerMap?.get(playerId);
      if (
        playerMap &&
        (!player || normalizeName(player.name) !== normalizeName(playerName))
      )
        return fail(
          `${playerName} does not match ESPN player ${playerId}. Review the name before importing.`,
        );
      const tags = arr(m.tags, "tags", 7).map((v) => {
        if (!researchTags.includes(v as ResearchTag))
          return fail(`invalid recommendation tag in ${id}.`);
        return v as ResearchTag;
      });
      if (
        !tags.length ||
        new Set(tags).size !== tags.length ||
        (tags.includes("mention") && tags.length > 1)
      )
        return fail(`invalid tag combination for ${playerName}.`);
      const note = str(m.note, "player note", 1200, true),
        section = str(m.section, "section", 200);
      const analyst =
        m.analyst === undefined ? undefined : str(m.analyst, "analyst", 120);
      const mentionKey = `${playerId}:${section}:${analyst ?? ""}`;
      if (mentionKeys.has(mentionKey))
        return fail(
          `duplicate player/section/analyst for ${playerName} in ${id}.`,
        );
      mentionKeys.add(mentionKey);
      if (!tags.includes("mention") && !note)
        return fail(`missing explanation for ${playerName}.`);
      const aliases =
        m.aliases === undefined
          ? undefined
          : arr(m.aliases, "aliases", 10).map((v) => str(v, "alias", 100));
      return {
        playerId,
        playerName,
        tags,
        note,
        section,
        ...(analyst ? { analyst } : {}),
        ...(aliases ? { aliases } : {}),
      };
    });
    return {
      id,
      season,
      title: str(a.title, "title", 240),
      url,
      publisher: str(a.publisher, "publisher", 100),
      authors,
      publishedAt,
      reviewedAt,
      format: a.format as ResearchArticle["format"],
      summary: str(a.summary, "summary", 6000),
      mentions,
    };
  });
  return { version: 1, season, articles };
}

/** Updating a URL replaces its annotations, preventing stale tags and duplicate sources. */
export function mergeResearch(
  current: ResearchLibrary,
  incoming: ResearchLibrary,
): ResearchLibrary {
  if (current.season !== incoming.season)
    throw new Error("Research seasons do not match.");
  const articles = [...current.articles];
  for (const article of incoming.articles) {
    const index = articles.findIndex(
      (a) => sourceKey(a.url) === sourceKey(article.url),
    );
    const conflicting = articles.find(
      (a) => a.id === article.id && sourceKey(a.url) !== sourceKey(article.url),
    );
    if (conflicting)
      throw new Error(
        `Article ID ${article.id} already belongs to another source.`,
      );
    if (index >= 0) articles[index] = { ...article, id: articles[index].id };
    else articles.push(article);
  }
  return validateResearch(
    {
      ...current,
      articles: articles.sort(
        (a, b) =>
          b.publishedAt.localeCompare(a.publishedAt) ||
          a.title.localeCompare(b.title),
      ),
    },
    current.season,
  );
}

export function indexResearch(
  library: ResearchLibrary,
): Map<number, PlayerResearch[]> {
  const result = new Map<number, PlayerResearch[]>();
  for (const article of library.articles) {
    for (const id of new Set(article.mentions.map((m) => m.playerId))) {
      result.set(id, [
        ...(result.get(id) ?? []),
        {
          article,
          mentions: article.mentions.filter((m) => m.playerId === id),
        },
      ]);
    }
  }
  return result;
}

export function researchText(article: ResearchArticle): string {
  return [
    article.title,
    `${article.publisher} | ${article.authors.join(", ")} | ${article.publishedAt}`,
    `Format: ${formatLabels[article.format]} | Season: ${article.season - 1}–${article.season}`,
    `Original: ${article.url}`,
    "",
    "Research notes — concise paraphrases, with source opinions as of publication.",
    article.summary,
    "",
    ...article.mentions.map(
      (m) =>
        `${m.playerName} — ${m.tags.map((t) => tagLabels[t]).join(", ")} | ${m.section}${m.analyst ? ` | ${m.analyst}` : ""}${m.note ? `\n${m.note}` : ""}`,
    ),
  ].join("\n");
}

/** Match whole names only. Accent/punctuation variants are safe; surnames are never guessed. */
export function nameSpans(
  text: string,
  people: { playerId: number; playerName: string; aliases?: string[] }[],
): { start: number; end: number; playerId: number }[] {
  let normalized = "";
  const offsets: { start: number; end: number }[] = [];
  let position = 0;
  for (const character of text) {
    const converted = character
      .normalize("NFD")
      .replace(/\p{M}/gu, "")
      .toLowerCase()
      .replace(/[^\p{L}\p{N}]/gu, " ");
    for (const c of converted) {
      if (c === " " && normalized.endsWith(" ")) {
        if (offsets.length)
          offsets[offsets.length - 1].end = position + character.length;
        continue;
      }
      normalized += c;
      offsets.push({ start: position, end: position + character.length });
    }
    position += character.length;
  }
  const names = new Map<string, Set<number>>();
  for (const person of people)
    for (const name of [person.playerName, ...(person.aliases ?? [])]) {
      const n = normalizeName(name);
      if (n) names.set(n, new Set([...(names.get(n) ?? []), person.playerId]));
    }
  const candidates: { start: number; end: number; playerId: number }[] = [];
  for (const [name, ids] of names) {
    if (ids.size !== 1) continue;
    let cursor = 0;
    while ((cursor = normalized.indexOf(name, cursor)) !== -1) {
      const end = cursor + name.length;
      if (
        (cursor === 0 || normalized[cursor - 1] === " ") &&
        (end === normalized.length || normalized[end] === " ")
      )
        candidates.push({
          start: offsets[cursor].start,
          end: offsets[end - 1].end,
          playerId: [...ids][0],
        });
      cursor = end;
    }
  }
  const spans: typeof candidates = [];
  for (const span of candidates.sort(
    (a, b) => a.start - b.start || b.end - a.end,
  )) {
    if (!spans.length || span.start >= spans[spans.length - 1].end)
      spans.push(span);
  }
  return spans;
}
