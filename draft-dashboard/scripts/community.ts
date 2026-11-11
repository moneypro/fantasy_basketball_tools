import {
  readFile,
  writeFile,
  rename,
  mkdir,
  open,
  unlink,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  collectFeeds,
  emptyCache,
  retainPosts,
  validateFeedCache,
  type FeedCache,
} from "./community-feed.js";
import {
  validateCommunity,
  type CommunityLibrary,
} from "../shared/community.js";
import { nameSpans } from "../shared/research.js";
import type { Bootstrap } from "../shared/types.js";

const [command, ...args] = process.argv.slice(2);
const option = (key: string) => {
  const i = args.indexOf(key);
  return i < 0 ? undefined : args[i + 1];
};
const directory = path.resolve(
  option("--dir") ?? fileURLToPath(new URL("../community/", import.meta.url)),
);
const cacheFile = path.join(directory, "cache.json"),
  libraryFile = path.join(directory, "library.json");
const atomic = async (file: string, value: unknown) => {
  await writeFile(file + ".tmp", JSON.stringify(value, null, 2) + "\n", {
    mode: 0o600,
  });
  await rename(file + ".tmp", file);
};
async function read<T>(file: string, fallback: T): Promise<T> {
  try {
    return JSON.parse(await readFile(file, "utf8"));
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return fallback;
    throw e;
  }
}
try {
  if (!["fetch", "review", "import", "check"].includes(command))
    throw new Error(
      "Usage: npm run community -- fetch | review --out /tmp/community-review.json | import --input reviewed.json [--write] | check. Optional: --dir, --pool.",
    );
  const pool: Bootstrap = option("--pool")
    ? JSON.parse(await readFile(option("--pool")!, "utf8"))
    : await fetch(
        `${process.env.DRAFTROOM_API ?? "http://127.0.0.1:3030"}/api/bootstrap`,
        { signal: AbortSignal.timeout(15_000) },
      ).then((r) => {
        if (!r.ok) throw new Error("Local player pool unavailable");
        return r.json();
      });
  const season = pool.league.season;
  await mkdir(directory, { recursive: true });
  const lockFile = path.join(directory, "community.lock");
  const lock = await open(lockFile, "wx");
  try {
    const cache = validateFeedCache(
      await read<FeedCache>(cacheFile, emptyCache(season)),
      season,
    );
    const current = validateCommunity(
      await read(libraryFile, { version: 1, season, posts: [] }),
      season,
    );
    if (command === "fetch") {
      const result = await collectFeeds(cache, (value) =>
        atomic(cacheFile, value),
      );
      console.log(
        JSON.stringify(
          {
            requests: result.requests,
            skipped: result.skipped,
            nextFetchAt: result.cache.nextFetchAt,
            cachedPosts: result.cache.posts.length,
            feeds: result.cache.feeds.map(({ etag, lastModified, ...f }) => f),
          },
          null,
          2,
        ),
      );
    } else if (command === "review") {
      const out = option("--out");
      if (!out)
        throw new Error(
          "Choose --out for local evidence and a review template.",
        );
      const posts = retainPosts(cache.posts, Date.now()).filter(
        (p) =>
          !current.posts.some(
            (old) => old.id === p.id && old.contentHash === p.contentHash,
          ),
      );
      const names = pool.players.map((p) => ({
        playerId: p.id,
        playerName: p.name,
      }));
      const evidence = posts.map((p) => ({
        ...p,
        candidates: [
          ...new Set(
            nameSpans(p.title + " " + p.body, names).map((m) => m.playerId),
          ),
        ].map((id) => ({
          playerId: id,
          playerName: pool.players.find((p) => p.id === id)!.name,
        })),
      }));
      await mkdir(path.dirname(path.resolve(out)), { recursive: true });
      await atomic(out, evidence);
      const template: CommunityLibrary = {
        version: 1,
        season,
        posts: evidence.map(({ body, candidates, ...p }) => ({
          ...p,
          reviewedAt: "",
          rating: 3,
          confidence: "low",
          basis: body ? "title-and-body" : "title",
          summary: "",
          mentions: candidates.map((m) => ({ ...m, rating: null, note: "" })),
        })),
      };
      const reviewFile = out.replace(/\.json$/, "") + ".review.json";
      await atomic(reviewFile, template);
      console.log(
        JSON.stringify(
          {
            posts: posts.length,
            evidence: out,
            review: reviewFile,
            next: "Read each RSS post, resolve names, write a summary and per-player notes with 1–5 ratings. Null means context only. Set reviewedAt. No comment threads were fetched.",
          },
          null,
          2,
        ),
      );
    } else if (command === "check") {
      const valid = validateCommunity(current, season, pool.players);
      console.log(
        `Valid: ${valid.posts.length} community posts; ${new Set(valid.posts.flatMap((p) => p.mentions.map((m) => m.playerId))).size} linked players.`,
      );
    } else {
      const input = option("--input");
      if (!input) throw new Error("Choose --input with the reviewed JSON.");
      const incoming = validateCommunity(
        JSON.parse(await readFile(input, "utf8")),
        season,
        pool.players,
      );
      const active = new Map(
        retainPosts(cache.posts, Date.now()).map((p) => [p.id, p]),
      );
      for (const p of incoming.posts) {
        const source = active.get(p.id);
        if (
          !source ||
          source.contentHash !== p.contentHash ||
          source.title !== p.title ||
          source.url !== p.url ||
          source.subreddit !== p.subreddit ||
          source.publishedAt !== p.publishedAt ||
          (source.body ? "title-and-body" : "title") !== p.basis
        )
          throw new Error(
            `Post ${p.id} does not match the saved RSS evidence. Review again.`,
          );
      }
      const merged = new Map(
        current.posts
          .filter((p) => active.get(p.id)?.contentHash === p.contentHash)
          .map((p) => [p.id, p]),
      );
      for (const p of incoming.posts) merged.set(p.id, p);
      const result = validateCommunity(
        {
          version: 1,
          season,
          posts: [...merged.values()].sort((a, b) =>
            b.publishedAt.localeCompare(a.publishedAt),
          ),
        },
        season,
        pool.players,
      );
      console.log(
        JSON.stringify(
          {
            mode: args.includes("--write") ? "write" : "preview",
            incoming: incoming.posts.length,
            totalPosts: result.posts.length,
          },
          null,
          2,
        ),
      );
      if (args.includes("--write")) {
        await atomic(libraryFile + ".previous", current);
        await atomic(libraryFile, result);
        validateCommunity(
          JSON.parse(await readFile(libraryFile, "utf8")),
          season,
          pool.players,
        );
        console.log(
          "Saved and verified. Reload saved notes in Community; no rebuild needed.",
        );
      }
    }
  } finally {
    await lock.close();
    await unlink(lockFile);
  }
} catch (e) {
  console.error(e instanceof Error ? e.message : e);
  process.exitCode = 1;
}
