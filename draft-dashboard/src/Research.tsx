import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  BookOpen,
  Download,
  RefreshCw,
  Search,
} from "lucide-react";
import {
  formatLabels,
  nameSpans,
  researchTags,
  researchText,
  tagLabels,
  type PlayerResearch,
  type ResearchArticle,
  type ResearchLibrary,
  type ResearchMention,
  type ResearchTag,
} from "../shared/research";

function download(name: string, text: string) {
  const url = URL.createObjectURL(
    new Blob([text], { type: "text/plain;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function ResearchTags({ tags }: { tags: ResearchTag[] }) {
  return (
    <span className="research-tags">
      {[...new Set(tags)].map((tag) => (
        <span key={tag} className={`research-tag tag-${tag}`}>
          {tagLabels[tag]}
        </span>
      ))}
    </span>
  );
}
function HighlightedText({
  text,
  mentions,
  onSelect,
}: {
  text: string;
  mentions: ResearchMention[];
  onSelect: (id: number) => void;
}) {
  const spans = nameSpans(text, mentions);
  let previous = 0;
  return (
    <>
      {spans.map((span) => {
        const prefix = text.slice(previous, span.start);
        previous = span.end;
        return (
          <span key={`${span.start}-${span.playerId}`}>
            {prefix}
            <button
              className="inline-player"
              onClick={() => onSelect(span.playerId)}
            >
              <mark>{text.slice(span.start, span.end)}</mark>
            </button>
          </span>
        );
      })}
      {text.slice(previous)}
    </>
  );
}
export function PlayerGuides({
  entries,
  onOpen,
  compact = false,
  error = "",
  loading = false,
}: {
  entries: PlayerResearch[];
  onOpen: (id: string) => void;
  compact?: boolean;
  error?: string;
  loading?: boolean;
}) {
  const sorted = [...entries].sort(
    (a, b) =>
      Number(a.mentions.every((m) => m.tags.includes("mention"))) -
      Number(b.mentions.every((m) => m.tags.includes("mention"))),
  );
  if (error && !entries.length)
    return (
      <p className="research-empty" role="status">
        {error}
      </p>
    );
  if (loading && !entries.length)
    return <p className="research-empty">Loading guide notes…</p>;
  if (!entries.length)
    return (
      <p className="research-empty">
        No imported guide mentions this player yet.
      </p>
    );
  return (
    <div className="player-guides">
      {error && (
        <p className="research-error" role="status">
          {error}
        </p>
      )}
      <p className="research-disclaimer">
        Source opinions as of publication. Draft cost and scoring format matter.
      </p>
      {(compact ? sorted.slice(0, 2) : sorted).map(({ article, mentions }) => (
        <article className="player-guide" key={article.id}>
          <button
            className="guide-title-link"
            onClick={() => onOpen(article.id)}
          >
            {article.title}
          </button>
          <p className="guide-meta">
            {article.authors.join(", ")} · {article.publishedAt} ·{" "}
            {formatLabels[article.format]}
          </p>
          {mentions.map((m, i) => (
            <div className="player-guide-note" key={i}>
              <ResearchTags tags={m.tags} />
              <p>
                {m.note || "Mentioned for context; no recommendation assigned."}
              </p>
              <small>
                {m.section}
                {m.analyst ? ` · ${m.analyst}` : ""}
              </small>
            </div>
          ))}
          <a
            className="text-link"
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Read original <ArrowUpRight size={13} />
          </a>
        </article>
      ))}
    </div>
  );
}

export function ResearchLibraryView({
  library,
  selectedArticleId,
  selectedPlayerId,
  onArticle,
  onPlayer,
  onRefresh,
  refreshing,
  error,
}: {
  library: ResearchLibrary;
  selectedArticleId: string | null;
  selectedPlayerId: number | null;
  onArticle: (id: string) => void;
  onPlayer: (id: number) => void;
  onRefresh: () => void;
  refreshing: boolean;
  error: string;
}) {
  const [query, setQuery] = useState("");
  const [tag, setTag] = useState<ResearchTag | "all">("all");
  useEffect(() => {
    setQuery("");
    setTag("all");
  }, [selectedArticleId]);
  const filtered = useMemo(
    () =>
      library.articles.filter((a) => {
        const haystack = [
          a.title,
          a.summary,
          ...a.authors,
          ...a.mentions.flatMap((m) => [
            m.playerName,
            m.note,
            m.section,
            m.analyst ?? "",
          ]),
        ]
          .join(" ")
          .toLowerCase();
        return (
          haystack.includes(query.trim().toLowerCase()) &&
          (tag === "all" || a.mentions.some((m) => m.tags.includes(tag)))
        );
      }),
    [library, query, tag],
  );
  // A player-source link always opens that source, even if a previous search excluded it.
  const selected =
    filtered.find((a) => a.id === selectedArticleId) ?? filtered[0];
  const names = new Set(
    library.articles.flatMap((a) => a.mentions.map((m) => m.playerId)),
  );
  return (
    <section className="panel guide-library" aria-label="Research guides">
      <div className="guide-library-heading">
        <div>
          <h2>
            <BookOpen size={19} /> Research guides
          </h2>
          <p>
            {library.articles.length} guides · {names.size} players linked
          </p>
        </div>
        <button className="quiet" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw size={14} className={refreshing ? "spin" : ""} />
          Refresh guides
        </button>
      </div>
      <p className="guide-intro">
        Concise plain-text research notes. Select a highlighted name to see that
        player’s stats and all guide comments. Open the original for the full
        article.
      </p>
      {error && (
        <p className="research-error" role="alert">
          {error}
        </p>
      )}
      <div className="guide-filters">
        <label className="search">
          <Search size={16} />
          <input
            aria-label="Search research guides"
            placeholder="Search guides, authors, or players"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <select
          aria-label="Filter guide opinions"
          value={tag}
          onChange={(e) => setTag(e.target.value as ResearchTag | "all")}
        >
          <option value="all">All opinions</option>
          {researchTags.map((t) => (
            <option value={t} key={t}>
              {tagLabels[t]}
            </option>
          ))}
        </select>
      </div>
      <div className="guide-list" aria-label="Guide list">
        {filtered.map((a) => (
          <button
            key={a.id}
            className={`guide-list-item ${selected?.id === a.id ? "active" : ""}`}
            aria-pressed={selected?.id === a.id}
            onClick={() => onArticle(a.id)}
          >
            <strong>{a.title}</strong>
            <span>
              {a.authors.join(", ")} · {a.publishedAt} ·{" "}
              {new Set(a.mentions.map((m) => m.playerId)).size} players
            </span>
          </button>
        ))}
      </div>
      {!filtered.length && !error && (
        <p className="research-empty">
          {refreshing
            ? "Loading guides…"
            : library.articles.length
              ? "No guides match this search."
              : "No guides have been imported yet."}
        </p>
      )}
      {selected && (
        <GuideReader
          article={selected}
          selectedPlayerId={selectedPlayerId}
          onPlayer={onPlayer}
        />
      )}
    </section>
  );
}

function GuideReader({
  article,
  selectedPlayerId,
  onPlayer,
}: {
  article: ResearchArticle;
  selectedPlayerId: number | null;
  onPlayer: (id: number) => void;
}) {
  const recommendations = article.mentions.filter(
    (m) => !m.tags.includes("mention"),
  );
  const context = article.mentions.filter((m) => m.tags.includes("mention"));
  const sections = [...new Set(recommendations.map((m) => m.section))];
  const note = (m: ResearchMention, i: number) => (
    <li
      key={`${m.playerId}-${i}`}
      className={`guide-mention ${selectedPlayerId === m.playerId ? "selected" : ""}`}
    >
      <div>
        <button className="inline-player" onClick={() => onPlayer(m.playerId)}>
          <mark>{m.playerName}</mark>
        </button>
        <ResearchTags tags={m.tags} />
      </div>
      {m.note && (
        <p>
          <HighlightedText
            text={m.note}
            mentions={article.mentions}
            onSelect={onPlayer}
          />
        </p>
      )}
      {m.analyst && <small>{m.analyst}</small>}
    </li>
  );
  return (
    <article className="guide-reader" aria-label={article.title}>
      <div className="guide-reader-heading">
        <span className="eyebrow">READING NOTES</span>
        <button
          onClick={() => download(`${article.id}.txt`, researchText(article))}
        >
          <Download size={14} />
          Plain text
        </button>
      </div>
      <h2>{article.title}</h2>
      <p className="guide-meta">
        {article.publisher} · {article.authors.join(", ")} · Published{" "}
        {article.publishedAt}
      </p>
      <p className="guide-meta">
        {formatLabels[article.format]} · {article.season - 1}–
        {String(article.season).slice(-2)} · Reviewed{" "}
        {article.reviewedAt.slice(0, 10)}
      </p>
      <a
        className="text-link"
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
      >
        Read original article <ArrowUpRight size={14} />
      </a>
      <p className="guide-summary">
        <HighlightedText
          text={article.summary}
          mentions={article.mentions}
          onSelect={onPlayer}
        />
      </p>
      {sections.map((section) => (
        <section className="guide-section" key={section}>
          <h3>{section}</h3>
          <ul>
            {recommendations.filter((m) => m.section === section).map(note)}
          </ul>
        </section>
      ))}
      {!!context.length && (
        <details
          className="guide-context"
          open={context.some((m) => m.playerId === selectedPlayerId)}
        >
          <summary>
            Other players mentioned (
            {new Set(context.map((m) => m.playerId)).size})
          </summary>
          <p>
            Comparisons, teammates, or background references. These names alone
            do not imply a draft recommendation.
          </p>
          <ul>{context.map(note)}</ul>
        </details>
      )}
    </article>
  );
}
