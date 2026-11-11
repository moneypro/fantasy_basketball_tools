import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  Copy,
  Download,
  Flag,
  FlaskConical,
  LayoutGrid,
  List,
  LoaderCircle,
  MessageCircle,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  Star,
  Table2,
  Undo2,
  Upload,
  Users,
  X,
} from "lucide-react";
import type {
  Bootstrap,
  DraftResponse,
  League,
  Pick,
  Player,
  Preference,
  SavedState,
} from "../shared/types";
import {
  availablePlayers,
  demand,
  emptyPreference,
  emptyState,
  fitRoster,
  nextPick,
  practiceToTurn,
  reconcilePicks,
  retireConfirmedPicks,
  validateImport,
} from "../shared/draft";
import { buildBriefing, type BriefingOptions } from "../shared/briefing";
import {
  indexResearch,
  validateResearch,
  type ResearchLibrary,
  type PlayerResearch,
} from "../shared/research";
import { PlayerGuides, ResearchLibraryView } from "./Research";
import {
  emptyCommunity,
  indexCommunity,
  validateCommunity,
  type CommunitySnapshot,
  type PlayerCommunity,
} from "../shared/community";
import { CommunityView, PlayerCommunityNotes } from "./Community";
import { PositionsView } from "./Positions";
import { api } from "./api";
import { readSnapshot, saveSnapshot, saveDraftSnapshot } from "./snapshot";
import { mergeBootstrap, sameLeague } from "../shared/bootstrap";

const number = (n: number | null | undefined, digits = 1) =>
  n == null || !Number.isFinite(n) ? "—" : n.toFixed(digits);
const timestamp = (value: string) =>
  new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
const injuryLabel = (p: Player) =>
  p.injury === "ACTIVE"
    ? ""
    : p.injury === "UNKNOWN"
      ? "Status unknown"
      : p.injury.replaceAll("_", " ").toLowerCase();
const storageKey = (l: League) =>
  `draftroom:v1:${l.id}:${l.season}:${l.teamId}`;
function loadSaved(l: League) {
  try {
    const raw = localStorage.getItem(storageKey(l));
    return {
      state: raw ? validateImport(JSON.parse(raw), l) : emptyState(l),
      error: "",
    };
  } catch {
    return {
      state: emptyState(l),
      error:
        "Saved draft data could not be read. Import a backup before making new changes.",
    };
  }
}
export function App() {
  const [initial, setInitial] = useState<Bootstrap | null>(null),
    [error, setError] = useState("");
  const [pending, setPending] = useState(true);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    let received = false;
    const controller = new AbortController();
    setPending(true);
    setError("");
    void readSnapshot().then((saved) => {
      if (active && !received && saved)
        setInitial((current) => current ?? saved);
    });
    api<Bootstrap>("/api/bootstrap", "GET", { signal: controller.signal })
      .then((d) => {
        received = true;
        if (active) setInitial(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setPending(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [attempt]);
  if (!initial)
    return (
      <div className="loading-page">
        <div className="brand-mark">
          d<span>.</span>
        </div>
        <h1>{error ? "Couldn’t open Draftroom" : "Opening your draft room"}</h1>
        <p>{error || "Loading your league, projections, and player pool."}</p>
        {error ? (
          <button onClick={() => setAttempt((a) => a + 1)}>Try again</button>
        ) : (
          <LoaderCircle className="spin" />
        )}
      </div>
    );
  return (
    <Workspace
      key={`${initial.league.id}:${initial.league.season}:${initial.league.teamId}`}
      initial={initial}
      bootstrapPending={pending}
      bootstrapError={error}
      onRetry={() => setAttempt((a) => a + 1)}
    />
  );
}
function Workspace({
  initial,
  bootstrapPending,
  bootstrapError,
  onRetry,
}: {
  initial: Bootstrap;
  bootstrapPending: boolean;
  bootstrapError: string;
  onRetry: () => void;
}) {
  const [data, setData] = useState(initial);
  useEffect(() => {
    setData((current) => mergeBootstrap(current, initial));
  }, [initial]);
  useEffect(() => {
    void saveSnapshot(data);
  }, [data.players, data.playerMeta]);
  useEffect(() => {
    void saveDraftSnapshot({ league: data.league, meta: data.meta });
  }, [data.league, data.meta]);
  const [loaded] = useState(() => loadSaved(initial.league));
  const [saved, setSaved] = useState(loaded.state);
  const [practice, setPractice] = useState(false),
    [view, setView] = useState<
      "players" | "roster" | "board" | "positions" | "guides" | "community"
    >("players");
  const [research, setResearch] = useState<ResearchLibrary>({
    version: 1,
    season: initial.league.season,
    articles: [],
  });
  const [researchError, setResearchError] = useState("");
  const [researchLoading, setResearchLoading] = useState(true);
  const [activeGuideId, setActiveGuideId] = useState<string | null>(null);
  const researchIndex = useMemo(() => indexResearch(research), [research]);
  const refreshResearch = async () => {
    setResearchLoading(true);
    try {
      const value = await api<unknown>("/api/research");
      setResearch(validateResearch(value, initial.league.season));
      setResearchError("");
    } catch {
      setResearchError(
        "Guide updates are unavailable. Previously loaded notes, if any, remain visible; use Refresh guides to retry.",
      );
    } finally {
      setResearchLoading(false);
    }
  };
  useEffect(() => {
    void refreshResearch();
  }, []);
  const openGuide = (id: string) => {
    setActiveGuideId(id);
    setView("guides");
  };
  const [community, setCommunity] = useState<CommunitySnapshot>(() =>
    emptyCommunity(initial.league.season),
  );
  const [communityError, setCommunityError] = useState("");
  const [communityLoading, setCommunityLoading] = useState(true);
  const [communityFocusKey, setCommunityFocusKey] = useState(0);
  const communityIndex = useMemo(() => indexCommunity(community), [community]);
  const refreshCommunity = async () => {
    setCommunityLoading(true);
    try {
      const value = await api<CommunitySnapshot>("/api/community");
      const library = validateCommunity(value, initial.league.season);
      if (
        !Array.isArray(value.feeds) ||
        !Number.isInteger(value.pendingCount) ||
        !Number.isInteger(value.collectedCount)
      )
        throw new Error("Invalid community snapshot");
      setCommunity({ ...value, ...library });
      setCommunityError("");
    } catch {
      setCommunityError(
        "Community updates are unavailable. Previously loaded notes remain visible; reload saved notes to retry.",
      );
    } finally {
      setCommunityLoading(false);
    }
  };
  useEffect(() => {
    void refreshCommunity();
  }, []);
  const [query, setQuery] = useState(""),
    [position, setPosition] = useState("ALL"),
    [filter, setFilter] = useState("available"),
    [allPlayers, setAllPlayers] = useState(false);
  const [sort, setSort] = useState<
      "rank" | "fppg" | "adp" | "total" | "previous" | "games" | "preseason"
    >("rank"),
    [ascending, setAscending] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(
    initial.players.find((p) => p.rank === 9)?.id ??
      initial.players[0]?.id ??
      null,
  );
  const [compare, setCompare] = useState<number[]>([]),
    [compareOpen, setCompareOpen] = useState(false),
    [refreshing, setRefreshing] = useState(false),
    [notice, setNotice] = useState(loaded.error);
  const [syncError, setSyncError] = useState(""),
    [logPlayer, setLogPlayer] = useState<Player | null>(null),
    [logTeam, setLogTeam] = useState(initial.league.teamId);
  const [tick, setTick] = useState(Date.now());
  const [briefing, setBriefing] = useState<BriefingOptions | null>(null);
  const [briefingQuestion, setBriefingQuestion] = useState(
    "Who should I target at my next pick, and who can wait?",
  );
  const [preparingBriefing, setPreparingBriefing] = useState(false);
  const briefingPreview = useRef<HTMLTextAreaElement>(null);
  const briefingText = briefing
    ? buildBriefing({ ...briefing, question: briefingQuestion })
    : "";
  const importInput = useRef<HTMLInputElement>(null);
  const league = data.league;
  const byId = useMemo(
    () => new Map(data.players.map((p) => [p.id, p])),
    [data.players],
  );
  const preference = (id: number): Preference =>
    saved.preferences[id] ?? emptyPreference();
  const update = (fn: (s: SavedState) => SavedState) =>
    setSaved((prev) => {
      const next = fn(prev);
      if (next === prev) return prev;
      try {
        localStorage.setItem(storageKey(league), JSON.stringify(next));
      } catch {
        setNotice(
          "Browser storage is unavailable. Export a backup to keep your changes.",
        );
      }
      return next;
    });
  const changePreference = (id: number, patch: Partial<Preference>) =>
    update((s) => ({
      ...s,
      preferences: {
        ...s.preferences,
        [id]: { ...(s.preferences[id] ?? emptyPreference()), ...patch },
      },
    }));
  const { picks, conflicts } = useMemo(
    () =>
      reconcilePicks(
        practice
          ? league.picks.map((p) => ({ ...p, playerId: null }))
          : league.picks,
        practice ? saved.practicePicks : saved.manualPicks,
      ),
    [practice, league.picks, saved],
  );
  const current = nextPick(picks),
    myTeam = league.teams.find((t) => t.id === league.teamId)!;
  const teamName = (id: number) =>
    league.teams.find((t) => t.id === id)?.name ?? `Team ${id}`;
  const myPicks = picks.filter((p) => p.teamId === league.teamId);
  const upcoming = myPicks.filter((p) => !p.playerId).slice(0, 3);
  const drafted = new Map(
    picks.filter((p) => p.playerId).map((p) => [p.playerId, p]),
  );
  const available = availablePlayers(data.players, picks);
  const roster = myPicks.flatMap((p) =>
    p.playerId && byId.has(p.playerId) ? [byId.get(p.playerId)!] : [],
  );
  const fitted = fitRoster(roster, league.slots);
  const targets = data.players
    .filter((p) => preference(p.id).target && !drafted.has(p.id))
    .sort(
      (a, b) =>
        preference(a.id).priority - preference(b.id).priority ||
        (a.rank ?? 9999) - (b.rank ?? 9999),
    );
  const selected = selectedId ? byId.get(selectedId) : null;
  const nextAfterCurrent = upcoming.find(
    (p) => p.overall > (current?.overall ?? 0),
  );
  const nextOptions = [...available]
    .filter((p) => !preference(p.id).avoid && p.projected.fppg != null)
    .sort((a, b) => {
      const aPref = preference(a.id),
        bPref = preference(b.id);
      return (
        Number(bPref.target) - Number(aPref.target) ||
        (aPref.target && bPref.target ? aPref.priority - bPref.priority : 0) ||
        (b.projected.fppg ?? 0) - (a.projected.fppg ?? 0)
      );
    })
    .slice(0, 3);
  const recommendations = nextOptions.map((p) => ({
    player: p,
    reason: preference(p.id).target
      ? "On your shortlist"
      : fitted.slots.some((s) => !s.player && p.slots.includes(s.slot))
        ? "Fills an open starting slot"
        : "Adds projected scoring depth",
  }));
  const visible = useMemo(() => {
    const term = query.toLowerCase();
    const get = (p: Player): number | null =>
      sort === "fppg"
        ? p.projected.fppg
        : sort === "total"
          ? p.projected.total
          : sort === "previous"
            ? p.previous.fppg
            : sort === "games"
              ? p.projected.games
              : sort === "preseason"
                ? (p.preseason?.fantasyPointsPerGame ?? null)
                : sort === "adp"
                  ? p.adpUncertain
                    ? null
                    : p.adp
                  : p.rank;
    return data.players
      .filter(
        (p) =>
          (allPlayers ||
            p.projected.fppg != null ||
            !!saved.preferences[p.id]?.target) &&
          (!term || `${p.name} ${p.team}`.toLowerCase().includes(term)) &&
          (position === "ALL" || p.slots.includes(position)) &&
          (filter === "all" ||
            (filter === "available" && !drafted.has(p.id)) ||
            (filter === "targets" &&
              saved.preferences[p.id]?.target &&
              !drafted.has(p.id)) ||
            (filter === "drafted" && drafted.has(p.id))),
      )
      .sort((a, b) => {
        const av = get(a),
          bv = get(b);
        if (av == null) return bv == null ? a.name.localeCompare(b.name) : 1;
        if (bv == null) return -1;
        return (av - bv) * (ascending ? 1 : -1) || a.name.localeCompare(b.name);
      });
  }, [
    data.players,
    query,
    position,
    allPlayers,
    filter,
    sort,
    ascending,
    saved.preferences,
    picks,
  ]);
  useEffect(() => {
    const timer = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    update((s) => {
      const pending = retireConfirmedPicks(league.picks, s.manualPicks);
      return pending.length === s.manualPicks.length
        ? s
        : { ...s, manualPicks: pending };
    });
  }, [league.picks]);
  useEffect(() => {
    if (bootstrapPending) return;
    let active = true;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const state = await api<DraftResponse>("/api/draft", "GET", {
          signal: controller.signal,
        });
        if (!sameLeague(state.league, initial.league))
          throw new Error(
            "The server’s league has changed. Retry the connection to load it.",
          );
        if (active) {
          setData((d) => ({ ...d, ...state }));
          setSyncError("");
        }
      } catch (e) {
        if (active) setSyncError((e as Error).message);
      } finally {
        if (active) timer = setTimeout(poll, 5000);
      }
    };
    void poll();
    return () => {
      active = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [bootstrapPending]);
  useEffect(() => {
    if (bootstrapPending || bootstrapError) return;
    if (
      !initial.playerMeta.error &&
      Date.now() - Date.parse(initial.playerMeta.fetchedAt) < 5 * 60_000
    )
      return;
    let active = true;
    const controller = new AbortController();
    setRefreshing(true);
    api<Bootstrap>("/api/refresh", "POST", { signal: controller.signal })
      .then((fresh) => {
        if (active && sameLeague(fresh.league, initial.league))
          setData((current) => mergeBootstrap(current, fresh));
      })
      .catch((e) => {
        if (active) setNotice(e.message);
      })
      .finally(() => {
        if (active) setRefreshing(false);
      });
    return () => {
      active = false;
      controller.abort();
      setRefreshing(false);
    };
  }, [bootstrapPending, bootstrapError, initial]);
  const doRefresh = async () => {
    setRefreshing(true);
    try {
      const fresh = await api<Bootstrap>("/api/refresh", "POST");
      if (!sameLeague(fresh.league, initial.league))
        throw new Error("The server’s league has changed. Reload to open it.");
      setData((current) => mergeBootstrap(current, fresh));
      setNotice(
        fresh.playerMeta.error ??
          fresh.preseasonError ??
          "Player data refreshed.",
      );
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setRefreshing(false);
    }
  };
  const toggleSort = (key: typeof sort) => {
    if (sort === key) setAscending(!ascending);
    else {
      setSort(key);
      setAscending(["rank", "adp"].includes(key));
    }
  };
  const chooseCompare = (id: number) => {
    if (compare.includes(id)) setCompare(compare.filter((x) => x !== id));
    else if (compare.length < 3) setCompare([...compare, id]);
    else setNotice("Choose up to three players to compare.");
  };
  const openLog = (p: Player) => {
    if (!current) return;
    setLogPlayer(p);
    setLogTeam(current.teamId);
  };
  const log = () => {
    if (!logPlayer || !current || drafted.has(logPlayer.id)) return;
    const pick = {
      ...current,
      playerId: logPlayer.id,
      teamId: logTeam,
      local: true,
    };
    update((s) => ({
      ...s,
      [practice ? "practicePicks" : "manualPicks"]: [
        ...(practice ? s.practicePicks : s.manualPicks),
        pick,
      ],
    }));
    setLogPlayer(null);
  };
  const undo = () =>
    update((s) => ({
      ...s,
      [practice ? "practicePicks" : "manualPicks"]: (practice
        ? s.practicePicks
        : s.manualPicks
      ).slice(0, -1),
    }));
  const exportBackup = () => {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(saved, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `draftroom-${league.season}-team-${league.teamId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const prepareBriefing = async () => {
    setPreparingBriefing(true);
    let snapshot = data;
    try {
      const response = await fetch("/api/draft", {
        signal: AbortSignal.timeout(8000),
      });
      if (!response.ok)
        throw new Error("Draft refresh failed; using the saved board.");
      const fresh: DraftResponse = await response.json();
      snapshot = { ...data, ...fresh };
    } catch {
      snapshot = {
        ...data,
        meta: {
          ...data.meta,
          error: "Draft refresh failed; this briefing uses the saved board.",
        },
      };
    }
    setBriefing({
      data: snapshot,
      saved,
      practice,
      question: briefingQuestion,
      generatedAt: new Date().toISOString(),
      apiOrigin: location.origin,
      focusIds: [...compare, ...(selectedId ? [selectedId] : [])],
      research,
      community,
    });
    setPreparingBriefing(false);
  };
  const copyBriefing = async () => {
    try {
      await navigator.clipboard.writeText(briefingText);
      setNotice("Briefing copied. Paste it into your AI conversation.");
    } catch {
      briefingPreview.current?.focus();
      briefingPreview.current?.select();
      setNotice("Text selected. Press Ctrl+C or ⌘C to copy.");
    }
  };
  const downloadBriefing = () => {
    const url = URL.createObjectURL(
      new Blob([briefingText], { type: "text/plain;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `draftroom-${league.season}-team-${league.teamId}-briefing.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const restore = async (file: File | undefined) => {
    if (!file) return;
    try {
      if (file.size > 3_000_000) throw new Error("Backup is too large.");
      const state = validateImport(JSON.parse(await file.text()), league);
      for (const p of [...state.manualPicks, ...state.practicePicks])
        if (!byId.has(p.playerId!))
          throw new Error(
            "Backup contains a player outside this league’s player pool.",
          );
      if (
        confirm(
          "Replace this browser’s notes, shortlist, and tracked picks with the backup?",
        )
      ) {
        update(() => state);
        setNotice("Backup restored.");
      }
    } catch (e) {
      setNotice((e as Error).message);
    }
    if (importInput.current) importInput.current.value = "";
  };
  const elapsed = Math.max(
    0,
    Math.floor((tick - Date.parse(data.meta.fetchedAt)) / 1000),
  );
  const stale =
    !!(syncError || data.meta.error) ||
    elapsed > 20 ||
    data.meta.source !== "live";
  const age =
    elapsed < 60
      ? `${elapsed}s ago`
      : elapsed < 3600
        ? `${Math.floor(elapsed / 60)}m ago`
        : `${Math.floor(elapsed / 3600)}h ago`;
  const sortHead = (label: string, key: typeof sort, title?: string) => (
    <button
      className="column-sort"
      title={title}
      onClick={() => toggleSort(key)}
    >
      {label}
      {sort === key ? (
        ascending ? (
          <ArrowUp size={12} />
        ) : (
          <ArrowDown size={12} />
        )
      ) : null}
    </button>
  );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setView("players");
          }}
        >
          <div className="brand-mark">
            d<span>.</span>
          </div>
          <div>
            draftroom
            <span className="brand-sub">
              BASKETBALL / {league.season - 1}–{String(league.season).slice(-2)}
            </span>
          </div>
        </a>
        <div className="league-card">
          <span className="eyebrow">YOUR LEAGUE</span>
          <h3>{league.name}</h3>
          <div>
            {league.teams.length} teams <span>·</span> H2H points
          </div>
          <p>{myTeam.name}</p>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          <button
            className={view === "players" ? "active" : ""}
            onClick={() => setView("players")}
          >
            <List size={18} />
            Player pool
            <span>
              {available.filter((p) => p.projected.fppg != null).length}
            </span>
          </button>
          <button
            className={view === "roster" ? "active" : ""}
            onClick={() => setView("roster")}
          >
            <Users size={18} />
            My roster
            <span>
              {roster.length}/{myPicks.length}
            </span>
          </button>
          <button
            className={view === "board" ? "active" : ""}
            onClick={() => setView("board")}
          >
            <LayoutGrid size={18} />
            Draft board
          </button>
          <button
            className={view === "positions" ? "active" : ""}
            onClick={() => setView("positions")}
          >
            <Table2 size={18} />
            Positions
          </button>
          <button
            className={view === "guides" ? "active" : ""}
            onClick={() => setView("guides")}
          >
            <BookOpen size={18} /> Guides{" "}
            <span>{research.articles.length}</span>
          </button>
          <button
            className={view === "community" ? "active" : ""}
            onClick={() => setView("community")}
          >
            <MessageCircle size={18} />
            Community <span>{community.posts.length}</span>
          </button>
        </nav>
        <div className="sidebar-note">
          <span className="eyebrow">DRAFT NIGHT</span>
          <strong>
            {new Date(league.draftAt).toLocaleDateString("en-US", {
              timeZone: "America/Los_Angeles",
              month: "long",
              day: "numeric",
            })}
          </strong>
          <span>
            {new Date(league.draftAt).toLocaleTimeString("en-US", {
              timeZone: "America/Los_Angeles",
              hour: "numeric",
              minute: "2-digit",
            })}{" "}
            Pacific
          </span>
          <div>
            {league.draftType.toLowerCase()} · {league.secondsPerPick}s / pick
          </div>
        </div>
        <div className="sidebar-bottom">
          <button
            className={`practice-toggle ${practice ? "enabled" : ""}`}
            onClick={() => setPractice(!practice)}
          >
            <FlaskConical size={18} />
            {practice ? "Exit rehearsal" : "Rehearsal mode"}
            <span className="toggle-dot" />
          </button>
          <p>Practice locally before the real thing.</p>
          <div className="backup-actions">
            <button onClick={exportBackup}>
              <Download size={14} />
              Export
            </button>
            <button onClick={() => importInput.current?.click()}>
              <Upload size={14} />
              Import
            </button>
            <input
              ref={importInput}
              type="file"
              accept=".json,application/json"
              hidden
              onChange={(e) => void restore(e.target.files?.[0])}
            />
          </div>
          <span className="local-note">Notes saved on this browser</span>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div
            className={`connection ${stale ? "warning" : ""}`}
            title={
              syncError ||
              data.meta.error ||
              `Draft data checked ${timestamp(data.meta.fetchedAt)}`
            }
          >
            <span className="status-dot" />
            {stale ? "Saved draft data" : "ESPN connected"}
            <span className="dim">· {age}</span>
          </div>
          <div className="header-actions">
            <button
              className="quiet"
              onClick={prepareBriefing}
              disabled={preparingBriefing}
            >
              {preparingBriefing ? (
                <LoaderCircle size={15} className="spin" />
              ) : (
                <Copy size={15} />
              )}
              {preparingBriefing ? "Preparing…" : "AI briefing"}
            </button>
            <button className="quiet" onClick={doRefresh} disabled={refreshing}>
              <RefreshCw size={15} className={refreshing ? "spin" : ""} />
              {refreshing ? "Refreshing…" : "Refresh stats"}
            </button>
            <a
              className="espn-link"
              href={`https://fantasy.espn.com/basketball/league?leagueId=${league.id}`}
              target="_blank"
              rel="noreferrer"
            >
              Open ESPN
              <ArrowUpRight size={15} />
            </a>
          </div>
        </header>
        {practice && (
          <div className="practice-banner">
            <FlaskConical size={16} />
            <strong>Rehearsal</strong>
            <span>Simulated picks. Your live draft stays separate.</span>
            <button
              onClick={() =>
                update((s) => ({
                  ...s,
                  practicePicks: practiceToTurn(
                    league.picks,
                    s.practicePicks,
                    data.players,
                    league.teamId,
                  ),
                }))
              }
              disabled={!current || current.teamId === league.teamId}
            >
              Advance to my turn
              <ChevronRight size={14} />
            </button>
            <button
              className="quiet"
              onClick={() => {
                if (
                  confirm(
                    "Clear practice picks? Your notes and shortlist will stay.",
                  )
                )
                  update((s) => ({ ...s, practicePicks: [] }));
              }}
            >
              Reset
            </button>
          </div>
        )}
        {(stale ||
          data.playerMeta.source !== "live" ||
          bootstrapPending ||
          bootstrapError) && (
          <div className="data-notice">
            <ShieldAlert size={15} />
            <span>
              {bootstrapPending
                ? "Showing this browser’s saved data while reconnecting. "
                : bootstrapError
                  ? `${bootstrapError} `
                  : ""}
              {stale
                ? `${data.meta.error || "Live pick updates are unverified or unavailable. Use local tracking if needed."} `
                : ""}
              Stats: {data.playerMeta.source},{" "}
              {timestamp(data.playerMeta.fetchedAt)}.
            </span>
            {bootstrapError && (
              <button className="quiet" onClick={onRetry}>
                Retry connection
              </button>
            )}
          </div>
        )}
        {conflicts.length > 0 && (
          <div className="conflict-banner">
            <ShieldAlert size={16} />
            <span>{conflicts.join(" ")}</span>
            <button onClick={() => update((s) => ({ ...s, manualPicks: [] }))}>
              Clear local overrides
            </button>
          </div>
        )}
        <section className="page-heading">
          <div>
            <span className="eyebrow">YOUR EDGE ON DRAFT NIGHT</span>
            <h1>
              {view === "players"
                ? "Make your next pick count."
                : view === "roster"
                  ? "Build a team that fits."
                  : view === "positions"
                    ? "Know where every team stands."
                    : view === "community"
                      ? "Hear the community’s take."
                      : view === "guides"
                        ? "Put the reading to work."
                        : "See the whole board."}
            </h1>
            <p>
              {view === "players"
                ? "Your research, your shortlist, and every available option."
                : view === "roster"
                  ? "Position flexibility and projected scoring, as your roster takes shape."
                  : view === "positions"
                    ? "Top 150 availability and every team’s qualified position candidates."
                    : view === "community"
                      ? "Recent Reddit posts, linked to players and rated for fantasy context."
                      : view === "guides"
                        ? "Source-linked notes, named players, and every analyst’s point of view."
                        : "Every round, every team. Select a player to see the details."}
            </p>
          </div>
          <span className={`mode-pill ${practice ? "practice" : ""}`}>
            {practice
              ? "PRACTICE"
              : league.completed
                ? "COMPLETE"
                : league.inProgress
                  ? "LIVE DRAFT"
                  : "DRAFT PREP"}
          </span>
        </section>
        <section className="draft-strip">
          <div className="pick-now">
            <span className="eyebrow">
              {current ? "NEXT SELECTION" : "DRAFT COMPLETE"}
            </span>
            <div>
              <strong>
                {current ? String(current.overall).padStart(2, "0") : "✓"}
              </strong>
              <span>
                {current ? (
                  <>
                    Round {current.round}
                    <small>{teamName(current.teamId)}</small>
                  </>
                ) : (
                  <small>All picks recorded</small>
                )}
              </span>
            </div>
          </div>
          <div className="your-turn">
            <span className="eyebrow">YOUR NEXT PICKS</span>
            <div>
              {upcoming.map((p, i) => (
                <span key={p.overall} className={i === 0 ? "next" : ""}>
                  #{p.overall}
                  <small>R{p.round}</small>
                </span>
              ))}
              {!upcoming.length && <span>Done</span>}
            </div>
          </div>
          <div className="picks-away">
            <span className="eyebrow">
              {current?.teamId === league.teamId
                ? "YOUR TURN"
                : "UNTIL YOUR PICK"}
            </span>
            <strong>
              {current?.teamId === league.teamId
                ? "You’re up."
                : upcoming[0] && current
                  ? `${upcoming[0].overall - current.overall} picks`
                  : "—"}
            </strong>
            <small>
              {picks.filter((p) => p.playerId).length} / {picks.length}{" "}
              selections recorded
            </small>
          </div>
          <button
            className="quiet undo"
            onClick={undo}
            disabled={
              !(practice ? saved.practicePicks : saved.manualPicks).length
            }
          >
            <Undo2 size={15} />
            Undo local pick
          </button>
        </section>
        <div className="workspace-grid">
          <div className="primary-column">
            {view === "players" && (
              <>
                <section className="candidates">
                  <div className="section-title">
                    <h2>Next up</h2>
                    <span>Shortlist first, then projected points / game</span>
                  </div>
                  <div className="candidate-grid">
                    {recommendations.map(({ player: p, reason }, i) => (
                      <button
                        className={`candidate ${selectedId === p.id ? "selected" : ""}`}
                        key={p.id}
                        onClick={() => setSelectedId(p.id)}
                      >
                        <div className="candidate-top">
                          <span className="candidate-number">0{i + 1}</span>
                          <span>
                            {p.team} · {p.positions.join("/")}
                          </span>
                          {preference(p.id).target && (
                            <Star size={13} className="star-filled" />
                          )}
                        </div>
                        <strong>{p.name}</strong>
                        <div className="candidate-stat">
                          {number(p.projected.fppg)}
                          <small>PROJ FP/G</small>
                        </div>
                        <div className="candidate-reason">
                          {reason}
                          <ChevronRight size={12} />
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
                <section className="pool panel">
                  <div className="pool-heading">
                    <h2>
                      Player pool <span>{visible.length}</span>
                    </h2>
                    <label className="checkbox">
                      <input
                        type="checkbox"
                        checked={allPlayers}
                        onChange={(e) => setAllPlayers(e.target.checked)}
                      />
                      Include unprojected
                    </label>
                  </div>
                  <div className="metric-key" aria-label="Stat color key">
                    <span className="metric-adp">Draft cost · ADP</span>
                    <span className="metric-games">
                      Games played · projected GP
                    </span>
                    <span className="metric-scoring">
                      Scoring · projected FP/G &amp; total FP
                    </span>
                  </div>
                  <div className="filters">
                    <div className="search">
                      <Search size={16} />
                      <input
                        aria-label="Search players"
                        placeholder="Find a player…"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                      />
                      {query && (
                        <button
                          aria-label="Clear search"
                          onClick={() => setQuery("")}
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>
                    <select
                      aria-label="Position filter"
                      value={position}
                      onChange={(e) => setPosition(e.target.value)}
                    >
                      {["ALL", "PG", "SG", "SF", "PF", "C", "G", "F"].map(
                        (p) => (
                          <option key={p} value={p}>
                            {p === "ALL" ? "All positions" : p}
                          </option>
                        ),
                      )}
                    </select>
                  </div>
                  <div
                    className="pool-tabs"
                    role="group"
                    aria-label="Availability filter"
                  >
                    {[
                      ["available", "Available"],
                      ["targets", "My shortlist"],
                      ["drafted", "Picked"],
                      ["all", "All"],
                    ].map(([id, label]) => (
                      <button
                        key={id}
                        className={filter === id ? "active" : ""}
                        onClick={() => setFilter(id)}
                      >
                        {label}
                        {id === "targets" && <span>{targets.length}</span>}
                      </button>
                    ))}
                    <span className="table-hint">
                      Click a player to research
                    </span>
                  </div>
                  <div className="table-scroll">
                    <table className="player-table">
                      <thead>
                        <tr>
                          <th className="star-col" aria-label="Shortlist" />
                          <th>{sortHead("RK", "rank")}</th>
                          <th>PLAYER</th>
                          <th className="metric-scoring">
                            {sortHead("PROJ FP/G", "fppg")}
                          </th>
                          <th className="metric-adp">
                            {sortHead(
                              "ADP",
                              "adp",
                              "Average draft position. ~140 values are uncertain and sort last.",
                            )}
                          </th>
                          <th className="metric-games">
                            {sortHead(
                              "PROJ GP",
                              "games",
                              "Projected games played",
                            )}
                          </th>
                          <th className="metric-scoring">
                            {sortHead("TOTAL FP", "total")}
                          </th>
                          <th>{sortHead("LAST FP/G", "previous")}</th>
                          <th aria-label="Compare" />
                        </tr>
                      </thead>
                      <tbody>
                        {visible.map((p) => {
                          const pref = preference(p.id),
                            pick = drafted.get(p.id);
                          return (
                            <tr
                              key={p.id}
                              className={`${selectedId === p.id ? "selected" : ""} ${pick ? "taken" : ""} ${pref.avoid ? "avoided" : ""}`}
                            >
                              <td>
                                <button
                                  className={`icon-button star ${pref.target ? "on" : ""}`}
                                  aria-label={`${pref.target ? "Unshortlist" : "Shortlist"} ${p.name}`}
                                  onClick={() =>
                                    changePreference(p.id, {
                                      target: !pref.target,
                                      avoid: false,
                                    })
                                  }
                                >
                                  <Star size={15} />
                                </button>
                              </td>
                              <td className="rank">{p.rank ?? "—"}</td>
                              <td>
                                <button
                                  className="player-name"
                                  onClick={() => setSelectedId(p.id)}
                                >
                                  <strong>
                                    {p.name}
                                    {pref.note && (
                                      <span
                                        className="note-dot"
                                        title="Has your notes"
                                      />
                                    )}
                                    {!!researchIndex.get(p.id)?.length && (
                                      <span
                                        className="guide-count"
                                        title={`Mentioned in ${researchIndex.get(p.id)!.length} guides`}
                                      >
                                        <BookOpen size={11} />
                                        {researchIndex.get(p.id)!.length}
                                      </span>
                                    )}
                                    {!!communityIndex.get(p.id)?.length && (
                                      <span
                                        className="community-count"
                                        title={`Mentioned in ${communityIndex.get(p.id)!.length} community posts`}
                                      >
                                        <MessageCircle size={11} />
                                        {communityIndex.get(p.id)!.length}
                                      </span>
                                    )}
                                  </strong>
                                  <span>
                                    {p.team} <b>·</b>{" "}
                                    {p.positions.join("/") || "—"}
                                    {injuryLabel(p) && (
                                      <em className="injury">
                                        {injuryLabel(p)}
                                      </em>
                                    )}
                                    {pick && (
                                      <em>
                                        Pick {pick.overall}
                                        {pick.local ? " · local" : ""}
                                      </em>
                                    )}
                                    {pref.avoid && (
                                      <em className="injury">Avoid</em>
                                    )}
                                  </span>
                                </button>
                              </td>
                              <td className="points">
                                {number(p.projected.fppg)}
                              </td>
                              <td
                                title={
                                  p.adpUncertain
                                    ? "Low-information value near ESPN’s default. Not used to estimate draft demand."
                                    : "ESPN average draft position"
                                }
                                className={`metric-adp ${p.adpUncertain ? "uncertain" : ""}`}
                              >
                                {p.adp == null
                                  ? "—"
                                  : `${p.adpUncertain ? "~" : ""}${number(p.adp)}`}
                                {p.adpUncertain && <small>uncertain</small>}
                              </td>
                              <td className="metric-games">
                                {number(p.projected.games, 0)}
                              </td>
                              <td className="metric-scoring">
                                {p.projected.total == null
                                  ? "—"
                                  : Math.round(
                                      p.projected.total,
                                    ).toLocaleString()}
                              </td>
                              <td className="dim">{number(p.previous.fppg)}</td>
                              <td>
                                <button
                                  className={`icon-button ${compare.includes(p.id) ? "checked" : ""}`}
                                  aria-label={`${compare.includes(p.id) ? "Remove" : "Compare"} ${p.name}`}
                                  onClick={() => chooseCompare(p.id)}
                                >
                                  {compare.includes(p.id) ? (
                                    <Check size={15} />
                                  ) : (
                                    <Plus size={15} />
                                  )}
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                    {!visible.length && (
                      <div className="empty">
                        <Search size={24} />
                        <h3>No matching players</h3>
                        <p>
                          Try another filter or include players without
                          projections.
                        </p>
                      </div>
                    )}
                  </div>
                  <div className="table-footer">
                    <span>
                      FP/G = fantasy points per game, using your league scoring.
                    </span>
                    <span>~ ADP = uncertain</span>
                  </div>
                </section>
              </>
            )}
            {view === "roster" && (
              <section className="panel roster-panel">
                <div className="section-title">
                  <h2>{myTeam.name}</h2>
                  <span>
                    {roster.length} / {myPicks.length} players
                  </span>
                </div>
                <div className="roster-summary">
                  <div>
                    <strong>
                      {number(
                        fitted.slots.reduce(
                          (sum, s) => sum + (s.player?.projected.fppg ?? 0),
                          0,
                        ),
                      )}
                    </strong>
                    <span>Combined starter FP/G</span>
                  </div>
                  <div>
                    <strong>
                      {fitted.slots.filter((s) => !s.player).length}
                    </strong>
                    <span>Open starting slots</span>
                  </div>
                  <div>
                    <strong>
                      {
                        roster.filter(
                          (p) => !["ACTIVE", "UNKNOWN"].includes(p.injury),
                        ).length
                      }
                    </strong>
                    <span>Injury flags to review</span>
                  </div>
                </div>
                <p className="helper">
                  A position-valid assignment. This sum assumes every starter
                  plays; it is not a weekly forecast.
                </p>
                {[
                  ...fitted.slots.map((s) => ({
                    slot: s.slot,
                    player: s.player,
                  })),
                  ...Array.from(
                    {
                      length: Math.max(
                        league.slots.BE ?? 0,
                        fitted.bench.length,
                      ),
                    },
                    (_, i) => ({ slot: "BE", player: fitted.bench[i] }),
                  ),
                ].map((s, i) => (
                  <button
                    className="roster-row"
                    key={i}
                    disabled={!s.player}
                    onClick={() => setSelectedId(s.player!.id)}
                  >
                    <span className="slot-badge">
                      {s.slot === "UT" ? "UTIL" : s.slot}
                    </span>
                    <div>
                      <strong>{s.player?.name ?? "Open slot"}</strong>
                      <small>
                        {s.player
                          ? `${s.player.team} · ${s.player.positions.join("/")}`
                          : "Available for your next selection"}
                      </small>
                    </div>
                    <span>
                      {s.player ? number(s.player.projected.fppg) : "—"}
                    </span>
                  </button>
                ))}
                <p className="helper">
                  {league.slots.IR ?? 0} IR slot · Injury status does not
                  automatically establish IR eligibility.
                </p>
              </section>
            )}
            {view === "board" && (
              <section className="panel board-panel">
                <div className="section-title">
                  <h2>{practice ? "Practice" : "League"} draft board</h2>
                  <span>
                    {league.draftType.toLowerCase()} · {picks.length} picks
                  </span>
                </div>
                <div className="board-scroll">
                  <div
                    className="draft-board"
                    style={{
                      gridTemplateColumns: `44px repeat(${league.teams.length}, 138px)`,
                    }}
                  >
                    <div />
                    {league.teams.map((t) => (
                      <div
                        key={t.id}
                        className={`board-team ${t.id === league.teamId ? "mine" : ""}`}
                      >
                        {t.name}
                      </div>
                    ))}
                    {Array.from(
                      { length: Math.max(0, ...picks.map((p) => p.round)) },
                      (_, i) => i + 1,
                    ).map((round) => (
                      <BoardRound
                        key={round}
                        round={round}
                        league={league}
                        picks={picks}
                        players={byId}
                        current={current}
                        onSelect={setSelectedId}
                      />
                    ))}
                  </div>
                </div>
              </section>
            )}
            {view === "positions" && (
              <PositionsView
                players={data.players}
                picks={picks}
                league={league}
                practice={practice}
                onPlayer={(id) => {
                  setSelectedId(id);
                  if (window.matchMedia("(max-width: 1250px)").matches)
                    setTimeout(
                      () =>
                        document
                          .querySelector(".player-detail")
                          ?.scrollIntoView({
                            behavior: "smooth",
                            block: "start",
                          }),
                      0,
                    );
                }}
              />
            )}
            {view === "guides" && (
              <ResearchLibraryView
                library={research}
                selectedArticleId={activeGuideId}
                selectedPlayerId={selectedId}
                onArticle={setActiveGuideId}
                onPlayer={(id) => {
                  setSelectedId(id);
                  if (window.matchMedia("(max-width: 1250px)").matches)
                    setTimeout(
                      () =>
                        document
                          .querySelector(".player-detail")
                          ?.scrollIntoView({
                            behavior: "smooth",
                            block: "start",
                          }),
                      0,
                    );
                }}
                onRefresh={refreshResearch}
                refreshing={researchLoading}
                error={researchError}
              />
            )}
            {view === "community" && (
              <CommunityView
                snapshot={community}
                loading={communityLoading}
                error={communityError}
                onRefresh={refreshCommunity}
                selectedPlayerId={selectedId}
                onPlayer={(id) => {
                  setSelectedId(id);
                  setCommunityFocusKey((key) => key + 1);
                  if (window.matchMedia("(max-width: 1250px)").matches)
                    setTimeout(
                      () =>
                        document
                          .querySelector(".player-detail")
                          ?.scrollIntoView({
                            behavior: "smooth",
                            block: "start",
                          }),
                      0,
                    );
                }}
              />
            )}
            <section className="scoring-footnote">
              <span className="eyebrow">YOUR POINTS FORMULA</span>
              <p>
                {Object.entries(league.weights)
                  .map(([stat, w]) => `${w > 0 ? "+" : ""}${w} ${stat}`)
                  .join("  ·  ")}
              </p>
            </section>
          </div>
          <aside className="research-column">
            <section className="panel shortlist">
              <div className="section-title">
                <h2>
                  <Star size={16} />
                  My shortlist
                </h2>
                <span>{targets.length} left</span>
              </div>
              {targets.length ? (
                targets.slice(0, 6).map((p) => (
                  <button
                    key={p.id}
                    className="shortlist-row"
                    onClick={() => setSelectedId(p.id)}
                  >
                    <span className="priority-dot">
                      {preference(p.id).priority}
                    </span>
                    <div>
                      <strong>{p.name}</strong>
                      <small>
                        {preference(p.id).tier || p.positions.join("/")}
                        {preference(p.id).round
                          ? ` · ${preference(p.id).round}`
                          : ""}
                      </small>
                    </div>
                    <span>{number(p.projected.fppg)}</span>
                  </button>
                ))
              ) : (
                <div className="shortlist-empty">
                  <Star size={23} />
                  <p>Your board. Your favorites.</p>
                  <span>Star players to keep your next choices close.</span>
                </div>
              )}
              {targets.length > 6 && (
                <button
                  className="text-link"
                  onClick={() => {
                    setView("players");
                    setFilter("targets");
                  }}
                >
                  View all {targets.length} targets
                  <ChevronRight size={14} />
                </button>
              )}
            </section>
            {selected && (
              <PlayerDetail
                player={selected}
                preference={preference(selected.id)}
                onPreference={(patch) => changePreference(selected.id, patch)}
                pick={drafted.get(selected.id)}
                current={current}
                teamName={teamName}
                onLog={() => openLog(selected)}
                onCompare={() => chooseCompare(selected.id)}
                comparing={compare.includes(selected.id)}
                nextPickNumber={nextAfterCurrent?.overall}
                preseasonThrough={data.preseasonThrough}
                guides={researchIndex.get(selected.id) ?? []}
                onOpenGuide={openGuide}
                researchError={researchError}
                researchLoading={researchLoading}
                community={communityIndex.get(selected.id) ?? []}
                communityError={communityError}
                communityLoading={communityLoading}
                communityFocusKey={communityFocusKey}
                onOpenCommunity={() => setView("community")}
              />
            )}
          </aside>
        </div>
      </main>
      {compare.length > 0 && (
        <div className="compare-bar">
          <span>
            <strong>{compare.length}</strong> selected
          </span>
          <div>
            {compare.map((id) => (
              <button key={id} onClick={() => chooseCompare(id)}>
                {byId.get(id)?.name}
                <X size={12} />
              </button>
            ))}
          </div>
          <button
            className="primary"
            disabled={compare.length < 2}
            onClick={() => setCompareOpen(true)}
          >
            Compare players
            <ArrowUpRight size={15} />
          </button>
          <button
            className="icon-button"
            aria-label="Clear comparison"
            onClick={() => setCompare([])}
          >
            <X size={17} />
          </button>
        </div>
      )}
      {notice && (
        <div className="toast" role="status">
          <span>{notice}</span>
          <button
            className="icon-button"
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
      {briefing && (
        <Modal title="AI briefing" wide onClose={() => setBriefing(null)}>
          <p className="modal-intro">
            Copy this snapshot into your AI conversation, or download it as a
            text file. It includes your notes and shortlist, plus instructions
            to refresh data from this workspace.
          </p>
          <label className="field-label">
            What do you want help with?
            <textarea
              aria-label="Question for the assistant"
              value={briefingQuestion}
              onChange={(e) => setBriefingQuestion(e.target.value)}
              rows={2}
            />
          </label>
          <p className="helper">
            {briefing.practice ? "Rehearsal" : "Real league"} · Snapshot{" "}
            {timestamp(briefing.generatedAt)} ·{" "}
            {Math.ceil(briefingText.length / 1000)}k characters. Refresh the
            snapshot after more picks.
          </p>
          <textarea
            ref={briefingPreview}
            className="briefing-preview"
            aria-label="Briefing text"
            readOnly
            value={briefingText}
            spellCheck={false}
          />
          <div className="briefing-actions">
            <button className="primary" onClick={copyBriefing}>
              <Copy size={15} />
              Copy text
            </button>
            <button className="secondary" onClick={downloadBriefing}>
              <Download size={15} />
              Download .txt
            </button>
            <button
              className="quiet"
              onClick={prepareBriefing}
              disabled={preparingBriefing}
            >
              <RefreshCw
                size={15}
                className={preparingBriefing ? "spin" : ""}
              />
              Refresh snapshot
            </button>
          </div>
        </Modal>
      )}
      {logPlayer && current && (
        <Modal title="Record this pick" onClose={() => setLogPlayer(null)}>
          <p className="modal-intro">
            Pick #{current.overall} · Round {current.round}
          </p>
          <h3 className="log-name">{logPlayer.name}</h3>
          <label className="field-label">
            Selected by
            <select
              aria-label="Drafting team"
              value={logTeam}
              onChange={(e) => setLogTeam(Number(e.target.value))}
            >
              {league.teams.map((t) => (
                <option value={t.id} key={t.id}>
                  {t.name}
                  {t.id === league.teamId ? " (you)" : ""}
                </option>
              ))}
            </select>
          </label>
          <p className="helper">
            This records the selection{" "}
            {practice ? "in your rehearsal" : "locally"}. Make your actual pick
            in ESPN.
          </p>
          <button className="primary full" onClick={log}>
            Record pick #{current.overall}
            <Check size={16} />
          </button>
        </Modal>
      )}
      {compareOpen && (
        <Modal
          title="Compare your options"
          onClose={() => setCompareOpen(false)}
          wide
        >
          <div
            className="comparison-grid"
            style={{
              gridTemplateColumns: `repeat(${compare.length}, minmax(0,1fr))`,
            }}
          >
            {compare.map((id) => {
              const p = byId.get(id)!;
              return (
                <div className="comparison-player" key={id}>
                  <span className="eyebrow">
                    {p.team} · {p.positions.join("/")}
                  </span>
                  <h3>{p.name}</h3>
                  <strong className="big-number">
                    {number(p.projected.fppg)}
                  </strong>
                  <span className="eyebrow">PROJECTED FP / GAME</span>
                  <dl>
                    {[
                      ["Projected games", number(p.projected.games, 0)],
                      ["Projected total", number(p.projected.total, 0)],
                      ["Last season FP/G", number(p.previous.fppg)],
                      ["Last season games", number(p.previous.games, 0)],
                      ["Projected minutes", number(p.projected.minutes)],
                      ["ESPN rank", p.rank ?? "—"],
                      [
                        "ESPN ADP",
                        p.adpUncertain ? "Uncertain" : number(p.adp),
                      ],
                      [
                        "Preseason FP/G",
                        number(p.preseason?.fantasyPointsPerGame),
                      ],
                      ["Preseason games", p.preseason?.gamesPlayed ?? 0],
                      ["Status", injuryLabel(p) || "Active"],
                    ].map(([label, value]) => (
                      <div
                        key={label}
                        className={
                          label === "ESPN ADP"
                            ? "metric-adp"
                            : label === "Projected games"
                              ? "metric-games"
                              : label === "Projected total"
                                ? "metric-scoring"
                                : undefined
                        }
                      >
                        <dt>{label}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                  <p className="compare-notes">
                    {preference(p.id).note || "No personal notes yet."}
                  </p>
                  <button
                    className="secondary full"
                    onClick={() => {
                      setSelectedId(id);
                      setCompareOpen(false);
                    }}
                  >
                    View player
                    <ChevronRight size={15} />
                  </button>
                </div>
              );
            })}
          </div>
        </Modal>
      )}
    </div>
  );
}
function BoardRound({
  round,
  league,
  picks,
  players,
  current,
  onSelect,
}: {
  round: number;
  league: League;
  picks: Pick[];
  players: Map<number, Player>;
  current: Pick | undefined;
  onSelect: (id: number) => void;
}) {
  return (
    <>
      <div className="board-round">R{round}</div>
      {league.teams.map((t) => {
        const cells = picks.filter(
          (p) => p.round === round && p.teamId === t.id,
        );
        return (
          <div
            className={`board-cell ${t.id === league.teamId ? "mine" : ""}`}
            key={t.id}
          >
            {cells.length ? (
              cells.map((p) => (
                <button
                  key={p.overall}
                  className={current?.overall === p.overall ? "on-clock" : ""}
                  disabled={!p.playerId}
                  onClick={() => onSelect(p.playerId!)}
                >
                  <small>
                    #{p.overall}
                    {p.local ? " · local" : ""}
                  </small>
                  <strong>
                    {p.playerId
                      ? (players.get(p.playerId)?.name ??
                        `Player ${p.playerId}`)
                      : current?.overall === p.overall
                        ? "Up next"
                        : "—"}
                  </strong>
                </button>
              ))
            ) : (
              <span className="dim">Traded</span>
            )}
          </div>
        );
      })}
    </>
  );
}
function PlayerDetail({
  player: p,
  preference: pref,
  onPreference,
  pick,
  current,
  teamName,
  onLog,
  onCompare,
  comparing,
  nextPickNumber,
  preseasonThrough,
  guides,
  onOpenGuide,
  researchError,
  researchLoading,
  community,
  communityError,
  communityLoading,
  communityFocusKey,
  onOpenCommunity,
}: {
  player: Player;
  preference: Preference;
  onPreference: (p: Partial<Preference>) => void;
  pick: Pick | undefined;
  current: Pick | undefined;
  teamName: (id: number) => string;
  onLog: () => void;
  onCompare: () => void;
  comparing: boolean;
  nextPickNumber: number | undefined;
  preseasonThrough: string | null;
  guides: PlayerResearch[];
  onOpenGuide: (id: string) => void;
  researchError: string;
  researchLoading: boolean;
  community: PlayerCommunity[];
  communityError: string;
  communityLoading: boolean;
  communityFocusKey: number;
  onOpenCommunity: () => void;
}) {
  const [tab, setTab] = useState<
    "overview" | "stats" | "preseason" | "guides" | "community"
  >("overview");
  useEffect(() => {
    if (communityFocusKey) setTab("community");
  }, [communityFocusKey]);
  return (
    <section className="panel player-detail">
      <div className="detail-heading">
        <span className="eyebrow">PLAYER RESEARCH</span>
        <button
          className={`icon-button star ${pref.target ? "on" : ""}`}
          aria-label={`${pref.target ? "Remove from" : "Add to"} shortlist`}
          onClick={() => onPreference({ target: !pref.target, avoid: false })}
        >
          <Star size={18} />
        </button>
      </div>
      <div className="player-identity">
        <div className="initials">
          {p.name
            .split(" ")
            .map((s) => s[0])
            .slice(0, 2)
            .join("")}
        </div>
        <div>
          <h2>{p.name}</h2>
          <p>
            {p.team} <span>·</span> {p.positions.join("/")}
          </p>
        </div>
      </div>
      {injuryLabel(p) && (
        <div className="injury-notice">
          <ShieldAlert size={13} />
          {injuryLabel(p)} — review latest news
        </div>
      )}
      <div className="detail-metrics">
        <div className="metric-scoring">
          <strong>{number(p.projected.fppg)}</strong>
          <span>PROJ FP/G</span>
        </div>
        <div className="metric-adp">
          <strong>
            {p.adpUncertain ? "~" : ""}
            {number(p.adp)}
          </strong>
          <span>{p.adpUncertain ? "ADP · UNCERTAIN" : "ESPN ADP"}</span>
        </div>
        <div className="metric-games">
          <strong>{number(p.projected.games, 0)}</strong>
          <span>PROJ GAMES</span>
        </div>
      </div>
      <div className="detail-tabs">
        {(
          ["overview", "stats", "preseason", "guides", "community"] as const
        ).map((t) => (
          <button
            key={t}
            className={tab === t ? "active" : ""}
            onClick={() => setTab(t)}
          >
            {t === "overview"
              ? "Overview"
              : t === "stats"
                ? "Stats"
                : t === "guides"
                  ? `Guides (${guides.length})`
                  : t === "community"
                    ? `Community (${community.length})`
                    : "Preseason"}
          </button>
        ))}
      </div>
      {tab === "overview" && (
        <div className="detail-content">
          <div className="insight">
            <Flag size={15} />
            <div>
              <strong>
                {pick
                  ? `Picked #${pick.overall} · ${teamName(pick.teamId)}`
                  : p.adpUncertain
                    ? "Draft demand is uncertain"
                    : nextPickNumber && demand(p) < nextPickNumber
                      ? "May go before your next turn"
                      : "Compare with your next turn"}
              </strong>
              <p>
                {pick
                  ? pick.local
                    ? "Tracked locally; ESPN may reconcile this pick."
                    : "Confirmed by ESPN."
                  : p.adpUncertain
                    ? "This ADP is missing or near ESPN’s default. Use your ranking and remaining alternatives."
                    : nextPickNumber
                      ? `ADP ${number(p.adp)} vs. your next pick #${nextPickNumber}. This is a rough signal, not an availability probability.`
                      : "ADP is a market average, not a prediction of your league’s picks."}
              </p>
            </div>
          </div>
          <div className="overview-guides">
            <h3>
              From the guides <span>{guides.length}</span>
            </h3>
            <PlayerGuides
              entries={guides}
              onOpen={onOpenGuide}
              compact
              error={researchError}
              loading={researchLoading}
            />
            {guides.length > 2 && (
              <button className="text-link" onClick={() => setTab("guides")}>
                All {guides.length} guide mentions <ChevronRight size={13} />
              </button>
            )}
          </div>
          {community.length > 0 && (
            <div className="overview-community">
              <h3>
                Community notes <span>{community.length}</span>
              </h3>
              <PlayerCommunityNotes
                entries={community}
                loading={communityLoading}
                error={communityError}
                onOpen={onOpenCommunity}
                compact
              />
              {community.length > 2 && (
                <button
                  className="text-link"
                  onClick={() => setTab("community")}
                >
                  All {community.length} community mentions{" "}
                  <ChevronRight size={13} />
                </button>
              )}
            </div>
          )}
          {p.outlook ? (
            <p className="outlook">{p.outlook}</p>
          ) : (
            <p className="helper">
              No ESPN season outlook available. Add your own research below.
            </p>
          )}
          <a
            className="text-link"
            href={`https://www.espn.com/nba/player/_/id/${p.id}`}
            target="_blank"
            rel="noreferrer"
          >
            Player news on ESPN
            <ArrowUpRight size={13} />
          </a>
        </div>
      )}
      {tab === "guides" && (
        <div className="detail-content">
          <PlayerGuides
            entries={guides}
            onOpen={onOpenGuide}
            error={researchError}
            loading={researchLoading}
          />
        </div>
      )}
      {tab === "community" && (
        <div className="detail-content">
          <PlayerCommunityNotes
            entries={community}
            loading={communityLoading}
            error={communityError}
            onOpen={onOpenCommunity}
          />
        </div>
      )}
      {tab === "stats" && (
        <div className="detail-content">
          <table className="stat-table">
            <thead>
              <tr>
                <th>PER GAME</th>
                <th>LAST SEASON</th>
                <th>PROJECTED</th>
              </tr>
            </thead>
            <tbody>
              {["PTS", "REB", "AST", "STL", "BLK", "3PM", "TO", "MIN"].map(
                (s) => (
                  <tr key={s}>
                    <th>{s}</th>
                    <td>{number(p.previous.stats[s])}</td>
                    <td>{number(p.projected.stats[s])}</td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      )}
      {tab === "preseason" && (
        <div className="detail-content">
          {p.preseason ? (
            <>
              <div className="preseason-summary">
                <strong>
                  {p.preseason.gamesPlayed} games · {p.preseason.starts} starts
                </strong>
                <span>
                  {number(p.preseason.minutesPerGame)} min / game ·{" "}
                  {number(p.preseason.fantasyPointsPerGame)} FP/G
                </span>
              </div>
              <p className="helper">
                Small sample through {preseasonThrough ?? "the last refresh"}.
                Look for role and minutes, not just scoring.
              </p>
              <table className="stat-table">
                <thead>
                  <tr>
                    <th>GAME</th>
                    <th>MIN</th>
                    <th>FP</th>
                    <th>START</th>
                  </tr>
                </thead>
                <tbody>
                  {p.preseason.games.map((g) => (
                    <tr key={g.eventId}>
                      <td>
                        <a
                          href={`https://www.espn.com/nba/boxscore/_/gameId/${g.eventId}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {new Date(g.date).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                          })}
                        </a>
                      </td>
                      <td>{number(g.minutes, 0)}</td>
                      <td>{number(g.fantasyPoints, 0)}</td>
                      <td>{g.starter ? "Yes" : "No"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p className="helper">
              No matched preseason appearances in this sample. This does not
              mean the player scored zero.
            </p>
          )}
        </div>
      )}
      <div className="notes-section">
        <div className="section-title">
          <h3>Your draft notes</h3>
          <span>Private · saved locally</span>
        </div>
        <div className="note-fields">
          <label>
            Priority
            <select
              aria-label="Shortlist priority"
              value={pref.priority}
              onChange={(e) =>
                onPreference({ priority: Number(e.target.value) })
              }
            >
              {[1, 2, 3, 4, 5].map((i) => (
                <option key={i} value={i}>
                  {i}
                  {i === 1 ? " · Highest" : ""}
                </option>
              ))}
            </select>
          </label>
          <label>
            Tier
            <input
              aria-label="Player tier"
              placeholder="e.g. A"
              value={pref.tier}
              maxLength={30}
              onChange={(e) => onPreference({ tier: e.target.value })}
            />
          </label>
          <label>
            Target
            <input
              aria-label="Target round"
              placeholder="Round 3"
              value={pref.round}
              maxLength={30}
              onChange={(e) => onPreference({ round: e.target.value })}
            />
          </label>
        </div>
        <textarea
          aria-label="Personal player notes"
          placeholder="Why I want him. What worries me. My backup plan…"
          value={pref.note}
          maxLength={10000}
          onChange={(e) => onPreference({ note: e.target.value })}
        />
        <label className="checkbox">
          <input
            type="checkbox"
            checked={pref.avoid}
            onChange={(e) =>
              onPreference({
                avoid: e.target.checked,
                target: e.target.checked ? false : pref.target,
              })
            }
          />
          Avoid in my next-up suggestions
        </label>
      </div>
      <div className="detail-actions">
        <button
          className="primary"
          disabled={!!pick || !current}
          onClick={onLog}
        >
          {pick ? "Already picked" : "Record pick"}
          <Check size={15} />
        </button>
        <button
          className={`secondary ${comparing ? "checked" : ""}`}
          onClick={onCompare}
        >
          {comparing ? <Check size={15} /> : <Plus size={15} />}Compare
        </button>
      </div>
    </section>
  );
}
function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const items = ref.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled), input, select, textarea, a[href]",
        );
        if (!items?.length) return;
        const first = items[0],
          last = items[items.length - 1];
        if (
          e.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === ref.current)
        ) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, [onClose]);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`modal ${wide ? "wide" : ""}`}
      >
        <div className="modal-heading">
          <h2>{title}</h2>
          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
