import express from "express";
import compression from "compression";
import dotenv from "dotenv";
import { readFile, writeFile, mkdir, rename } from "node:fs/promises";
import path from "node:path";
import type { Bootstrap, DraftResponse, Freshness } from "../shared/types.js";
import { normalizeLeague, normalizePlayers, type Raw } from "./normalize.js";
import { fetchLeague, fetchPlayers, fetchPreseason } from "./espn.js";
import { readResearch } from "./research.js";
import { readCommunity } from "./community.js";
import { applyDraftCapture } from "./draft-capture.js";

dotenv.config({ path: process.env.ENV_FILE ?? "../.env", quiet: true });
const season = Number(process.env.SEASON_YEAR ?? 2027),
  teamId = Number(process.env.TEAM_ID ?? 2),
  configuredId = Number(process.env.LEAGUE_ID);
const dataDir = path.resolve(process.env.DATA_DIR ?? "data");
const seedDir = path.resolve(
  process.env.SEED_DIR ?? "../output/draft_research_2026-10-06",
);
const load = async (file: string) => JSON.parse(await readFile(file, "utf8"));
let bundle: Bootstrap | null = null;
let preseason: Raw[] = [];
try {
  const cached = await load(path.join(dataDir, "cache.json"));
  if (
    cached.bundle.league.season === season &&
    cached.bundle.league.teamId === teamId &&
    (!configuredId || cached.bundle.league.id === configuredId)
  ) {
    bundle = cached.bundle;
    preseason = cached.preseason ?? [];
    bundle!.meta.source = "cache";
    bundle!.playerMeta.source = "cache";
  }
} catch {
  /* Fresh installation. */
}
if (!bundle)
  try {
    const seed = await load(path.join(seedDir, "league.json"));
    const league = normalizeLeague(seed, teamId);
    if (
      league.season !== season ||
      (configuredId && league.id !== configuredId)
    )
      throw new Error("Seed belongs to a different league or season.");
    const [players, pre, audit] = await Promise.all([
      load(path.join(seedDir, "players.json")),
      load(path.join(seedDir, "preseason.json")),
      load(path.join(seedDir, "api_audit.json")),
    ]);
    preseason = pre.players;
    const meta: Freshness = {
      source: "snapshot",
      fetchedAt: audit.savedAtUTC ?? "2026-10-07T00:00:00Z",
    };
    bundle = {
      league,
      players: normalizePlayers(players, league, preseason),
      meta: { ...meta },
      playerMeta: { ...meta },
      preseasonThrough: pre.dateRange?.[1] ?? null,
    };
  } catch {
    /* Live fetch can initialize without a snapshot. */
  }
const leagueId = configuredId || bundle?.league.id;
if (!leagueId || !Number.isInteger(season) || !Number.isInteger(teamId))
  throw new Error("Configure LEAGUE_ID, SEASON_YEAR, and TEAM_ID.");
let draftPending: Promise<DraftResponse> | null = null;
let lastAttempt = 0;
const errorMessage = (e: unknown) =>
  e instanceof Error &&
  (e.message.startsWith("Data provider") ||
    e.message.startsWith("ESPN") ||
    e.message.startsWith("Configured") ||
    e.message.startsWith("Draftroom"))
    ? e.message
    : "The data provider could not be reached. The last saved data is still available.";
async function draft(): Promise<DraftResponse> {
  if (draftPending) return draftPending;
  if (bundle && Date.now() - lastAttempt < 4000)
    return { league: bundle.league, meta: bundle.meta };
  lastAttempt = Date.now();
  draftPending = (async () => {
    try {
      const raw = await fetchLeague(season, leagueId!);
      const league = normalizeLeague(raw, teamId);
      if (league.id !== leagueId || league.season !== season)
        throw new Error("ESPN returned a different league or season.");
      const meta: Freshness = {
        source: "live",
        fetchedAt: new Date().toISOString(),
      };
      if (bundle) {
        bundle.league = league;
        bundle.meta = meta;
      }
      return { league, meta };
    } catch (e) {
      if (!bundle) throw e;
      bundle.meta = {
        ...bundle.meta,
        source: bundle.meta.source === "snapshot" ? "snapshot" : "cache",
        error: errorMessage(e),
      };
      return { league: bundle.league, meta: bundle.meta };
    }
  })();
  try {
    return await draftPending;
  } finally {
    draftPending = null;
  }
}
let refreshing: Promise<Bootstrap> | null = null;
let lastPlayerAttempt = 0;
async function refresh(): Promise<Bootstrap> {
  if (refreshing) return refreshing;
  if (bundle && Date.now() - lastPlayerAttempt < 15_000) return bundle;
  lastPlayerAttempt = Date.now();
  refreshing = (async () => {
    const state = await draft();
    let players = bundle?.players ?? [];
    let playerMeta = bundle?.playerMeta;
    let through = bundle?.preseasonThrough ?? null;
    let preseasonError: string | undefined;
    const [poolResult, preResult] = await Promise.allSettled([
      fetchPlayers(season, leagueId!),
      fetchPreseason(state.league, preseason, through),
    ]);
    if (preResult.status === "fulfilled") {
      preseason = preResult.value.players;
      through = preResult.value.through;
    } else
      preseasonError =
        "Preseason refresh failed; the previous game sample is shown.";
    if (poolResult.status === "fulfilled") {
      players = normalizePlayers(poolResult.value, state.league, preseason);
      playerMeta = { source: "live", fetchedAt: new Date().toISOString() };
    } else {
      if (!players.length || !playerMeta) throw poolResult.reason;
      playerMeta = {
        ...playerMeta,
        source: playerMeta.source === "snapshot" ? "snapshot" : "cache",
        error: errorMessage(poolResult.reason),
      };
      const pre = new Map(preseason.map((p) => [p.id, p]));
      players = players.map((p) => ({
        ...p,
        preseason: (pre.get(p.id) as typeof p.preseason) ?? null,
      }));
    }
    bundle = {
      ...(bundle ? { league: bundle.league, meta: bundle.meta } : state),
      players,
      playerMeta,
      preseasonThrough: through,
      preseasonError,
    };
    try {
      await mkdir(dataDir, { recursive: true });
      const temp = path.join(dataDir, "cache.tmp");
      await writeFile(temp, JSON.stringify({ bundle, preseason }));
      await rename(temp, path.join(dataDir, "cache.json"));
    } catch {
      console.warn("Could not persist the data cache.");
    }
    return bundle;
  })();
  try {
    return await refreshing;
  } finally {
    refreshing = null;
  }
}
const app = express();
async function withCapture(state: DraftResponse): Promise<DraftResponse> {
  try {
    return applyDraftCapture(
      state,
      await load(path.join(dataDir, "live-draft.json")),
    );
  } catch {
    return state;
  }
}
app.disable("x-powered-by");
app.use(compression());
app.use("/api", (req, res, next) => {
  res.set("Cache-Control", "no-store");
  const origin = req.get("origin");
  if (
    origin &&
    new URL(origin).host !== req.get("host") &&
    !["http://127.0.0.1:5173", "http://localhost:5173"].includes(origin)
  ) {
    res.status(403).json({ error: "Use Draftroom from its local address." });
    return;
  }
  next();
});
app.get("/api/health", (_req, res) => res.json({ ok: true, season }));
app.get("/api/research", async (_req, res) =>
  res.json(await readResearch(season)),
);
app.get("/api/community", async (_req, res) =>
  res.json(await readCommunity(season)),
);
app.get("/api/bootstrap", async (_req, res) => {
  if (!bundle) await refresh();
  res.json({ ...bundle!, ...(await withCapture(bundle!)) });
});
app.get("/api/draft", async (_req, res) => {
  if (bundle) {
    const captured = await withCapture(bundle);
    if (captured !== bundle) {
      // Serve the saved capture immediately even on a slow ESPN connection.
      void draft().catch(() => {});
      res.json(captured);
      return;
    }
  }
  res.json(await withCapture(await draft()));
});
app.post("/api/refresh", async (_req, res) => {
  const refreshed = await refresh();
  res.json({ ...refreshed, ...(await withCapture(refreshed)) });
});
app.use("/api", (_req, res) =>
  res.status(404).json({ error: "Unknown endpoint." }),
);
app.use(
  "/assets",
  express.static(path.resolve("dist/assets"), {
    maxAge: "1y",
    immutable: true,
  }),
);
app.use(express.static(path.resolve("dist")));
app.get("/{*path}", (_req, res) =>
  res.sendFile(path.resolve("dist/index.html")),
);
app.use(
  (
    error: unknown,
    _req: express.Request,
    res: express.Response,
    _next: express.NextFunction,
  ) => res.status(503).json({ error: errorMessage(error) }),
);
app.listen(Number(process.env.PORT ?? 3030), "0.0.0.0", () =>
  console.log(
    `Draftroom is listening on port ${process.env.PORT ?? 3030}. Season ${season}.`,
  ),
);
