import {
  readFile,
  writeFile,
  rename,
  open,
  unlink,
  mkdir,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { extractArticle } from "./research-extract.js";
import {
  mergeResearch,
  sourceKey,
  validateResearch,
} from "../shared/research.js";
import type { Bootstrap } from "../shared/types.js";

const project = fileURLToPath(new URL("../", import.meta.url));
const [command, input, ...args] = process.argv.slice(2);
const option = (key: string) => {
  const index = args.indexOf(key);
  return index < 0 ? undefined : args[index + 1];
};
const libraryFile = path.resolve(
  option("--library") ?? path.join(project, "research/library.json"),
);
async function getPool(): Promise<Bootstrap> {
  const file = option("--pool");
  if (file) return JSON.parse(await readFile(file, "utf8"));
  const response = await fetch(
    `${process.env.DRAFTROOM_API ?? "http://127.0.0.1:3030"}/api/bootstrap`,
    { signal: AbortSignal.timeout(15_000) },
  );
  if (!response.ok)
    throw new Error(`Player pool unavailable (${response.status}).`);
  return response.json();
}
try {
  if (!input || !["extract", "import", "check"].includes(command))
    throw new Error(
      "Usage: npm run research -- extract URL --out /tmp/guide.json [--html saved.html] | import notes.json [--write] | check library.json. Optional: --pool bootstrap.json, --library path.",
    );
  const pool = await getPool();
  const season = pool.league.season;
  if (command === "extract") {
    const key = sourceKey(input);
    const htmlFile = option("--html");
    let html: string;
    if (htmlFile) html = await readFile(htmlFile, "utf8");
    else {
      const response = await fetch(input, {
        signal: AbortSignal.timeout(25_000),
      });
      if (!response.ok)
        throw new Error(
          `Article request failed (${response.status}). No access controls are bypassed.`,
        );
      if (!(response.headers.get("content-type") ?? "").includes("text/html"))
        throw new Error(
          "Expected HTML. Use a saved article HTML file with --html.",
        );
      html = await response.text();
    }
    const evidence = extractArticle(html, input, pool.players);
    const out = option("--out");
    if (!out)
      throw new Error("Choose a local --out file for the review evidence.");
    const id = key.startsWith("espn:")
      ? key.replace(":", "-")
      : `guide-${createHash("sha256").update(key).digest("hex").slice(0, 12)}`;
    const review = {
      version: 1,
      season,
      articles: [
        {
          id,
          season,
          title: evidence.title,
          url: input,
          publisher: new URL(input).hostname,
          authors: evidence.authors,
          publishedAt: evidence.publishedAt ?? "",
          reviewedAt: "",
          format: "general",
          summary: "",
          mentions: evidence.candidates.map((p) => ({
            playerId: p.playerId,
            playerName: p.playerName,
            tags: ["mention"],
            note: "",
            section: "Context",
            ...(p.matchedAs !== p.playerName ? { aliases: [p.matchedAs] } : {}),
          })),
        },
      ],
    };
    await mkdir(path.dirname(path.resolve(out)), { recursive: true });
    await writeFile(out, JSON.stringify(evidence, null, 2), { mode: 0o600 });
    const reviewFile = out.replace(/\.json$/, "") + ".review.json";
    await writeFile(reviewFile, JSON.stringify(review, null, 2), {
      mode: 0o600,
    });
    console.log(
      JSON.stringify(
        {
          title: evidence.title,
          players: evidence.candidates.length,
          unresolved: evidence.unresolved,
          evidence: out,
          review: reviewFile,
          next: "Review ALL named players and contextual mentions; write concise original notes, correct tags/bylines/format/date, set reviewedAt, then import the review file. Nothing is published by extraction.",
        },
        null,
        2,
      ),
    );
  } else if (command === "check") {
    const library = validateResearch(
      JSON.parse(await readFile(input, "utf8")),
      season,
      pool.players,
    );
    console.log(
      `Valid: ${library.articles.length} guides, ${new Set(library.articles.flatMap((a) => a.mentions.map((m) => m.playerId))).size} players.`,
    );
  } else {
    const incoming = validateResearch(
      JSON.parse(await readFile(input, "utf8")),
      season,
      pool.players,
    );
    await mkdir(path.dirname(libraryFile), { recursive: true });
    const lockFile = libraryFile + ".lock";
    const lock = await open(lockFile, "wx");
    try {
      let current;
      try {
        current = validateResearch(
          JSON.parse(await readFile(libraryFile, "utf8")),
          season,
        );
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
        current = { version: 1 as const, season, articles: [] };
      }
      const result = validateResearch(
        mergeResearch(current, incoming),
        season,
        pool.players,
      );
      console.log(
        JSON.stringify(
          {
            mode: args.includes("--write") ? "write" : "preview",
            incoming: incoming.articles.map((a) => ({
              title: a.title,
              players: new Set(a.mentions.map((m) => m.playerId)).size,
              action: current.articles.some(
                (old) => sourceKey(old.url) === sourceKey(a.url),
              )
                ? "replace source notes"
                : "add source",
            })),
            totalGuides: result.articles.length,
          },
          null,
          2,
        ),
      );
      if (args.includes("--write")) {
        await writeFile(
          libraryFile + ".previous",
          JSON.stringify(current, null, 2),
        );
        const temp = libraryFile + ".tmp";
        await writeFile(temp, JSON.stringify(result, null, 2) + "\n");
        await rename(temp, libraryFile);
        const verified = validateResearch(
          JSON.parse(await readFile(libraryFile, "utf8")),
          season,
          pool.players,
        );
        console.log(
          `Saved and verified ${verified.articles.length} guides. Refresh guides in Draftroom; no rebuild is needed for content updates.`,
        );
      }
    } finally {
      await lock.close();
      await unlink(lockFile);
    }
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
}
