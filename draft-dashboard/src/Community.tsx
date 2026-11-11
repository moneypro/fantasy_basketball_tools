import { useMemo, useState } from "react";
import {
  ArrowUpRight,
  Download,
  MessageCircle,
  RefreshCw,
  Search,
} from "lucide-react";
import {
  communityText,
  communityPolicy,
  ratingLabels,
  type CommunityRating,
  type CommunityPost,
  type CommunitySnapshot,
  type PlayerCommunity,
} from "../shared/community";
import { nameSpans, normalizeName } from "../shared/research";

const when = (date: string) =>
  new Date(date).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
export function CommunityScore({ rating }: { rating: CommunityRating | null }) {
  return (
    <span className={`community-score score-${rating ?? "none"}`}>
      {rating === null
        ? "Context only"
        : `${rating}/5 · ${ratingLabels[rating]}`}
    </span>
  );
}
function Highlight({
  text,
  post,
  onPlayer,
}: {
  text: string;
  post: CommunityPost;
  onPlayer: (id: number) => void;
}) {
  const spans = nameSpans(text, post.mentions);
  let offset = 0;
  return (
    <>
      {spans.map((span) => {
        const prefix = text.slice(offset, span.start);
        offset = span.end;
        return (
          <span key={span.start}>
            {prefix}
            <button
              className="inline-player"
              onClick={() => onPlayer(span.playerId)}
            >
              <mark>{text.slice(span.start, span.end)}</mark>
            </button>
          </span>
        );
      })}
      {text.slice(offset)}
    </>
  );
}
export function PlayerCommunityNotes({
  entries,
  loading,
  error,
  onOpen,
  compact = false,
}: {
  entries: PlayerCommunity[];
  loading: boolean;
  error: string;
  onOpen: () => void;
  compact?: boolean;
}) {
  return (
    <div className="player-community">
      {error && (
        <p className="research-error" role="status">
          {error}
        </p>
      )}
      {!entries.length ? (
        <p className="research-empty">
          {loading
            ? "Loading community notes…"
            : error
              ? "Saved notes could not be loaded."
              : "No reviewed posts mention this player in the recent sample."}
        </p>
      ) : (
        <>
          <p className="research-disclaimer">
            Our reading of recent Reddit posts. Post titles and text only;
            comments and votes are not included.
          </p>
          {(compact ? entries.slice(0, 2) : entries).map(
            ({ post, mention }) => (
              <article className="player-community-card" key={post.id}>
                <CommunityScore rating={mention.rating} />
                <p>{mention.note}</p>
                <a href={post.url} target="_blank" rel="noopener noreferrer">
                  {post.title} <ArrowUpRight size={12} />
                </a>
                <small>
                  r/{post.subreddit} · {when(post.publishedAt)} ·{" "}
                  {post.confidence} confidence
                  {post.basis === "title" ? " · Title only" : ""}
                </small>
              </article>
            ),
          )}
        </>
      )}
      <button className="text-link" onClick={onOpen}>
        Open Community <ArrowUpRight size={13} />
      </button>
    </div>
  );
}
export function CommunityView({
  snapshot,
  loading,
  error,
  onRefresh,
  onPlayer,
  selectedPlayerId,
}: {
  snapshot: CommunitySnapshot;
  loading: boolean;
  error: string;
  onRefresh: () => void;
  onPlayer: (id: number) => void;
  selectedPlayerId: number | null;
}) {
  const [query, setQuery] = useState(""),
    [sub, setSub] = useState("all"),
    [rating, setRating] = useState("all"),
    [scope, setScope] = useState("players");
  const filtered = useMemo(
    () =>
      snapshot.posts.filter(
        (p) =>
          (scope === "all" || p.mentions.some((m) => m.rating !== null)) &&
          (sub === "all" || p.subreddit === sub) &&
          (rating === "all" ||
            p.rating === Number(rating) ||
            p.mentions.some((m) => m.rating === Number(rating))) &&
          normalizeName(
            [
              p.title,
              p.summary,
              ...p.mentions.flatMap((m) => [m.playerName, m.note]),
            ].join(" "),
          ).includes(normalizeName(query)),
      ),
    [snapshot, query, sub, rating, scope],
  );
  const names = new Set(
    snapshot.posts.flatMap((p) => p.mentions.map((m) => m.playerId)),
  );
  const download = () => {
    const url = URL.createObjectURL(
      new Blob([communityText({ ...snapshot, posts: filtered })], {
        type: "text/plain;charset=utf-8",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "draftroom-community.txt";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <section className="panel community-library" aria-label="Community notes">
      <div className="guide-library-heading">
        <div>
          <h2>
            <MessageCircle size={19} /> Community notes
          </h2>
          <p>
            {snapshot.posts.length} reviewed posts · {names.size} players linked
            · {snapshot.collectedCount} sampled
          </p>
        </div>
        <button className="quiet" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={14} className={loading ? "spin" : ""} />
          Reload saved notes
        </button>
      </div>
      <p className="guide-intro">
        Recent r/fantasybball and r/nba posts, with our assessment of the
        fantasy outlook. A post’s rating reflects its content; player ratings
        can differ. This sample does not measure subreddit consensus.
      </p>
      <div className="community-scale" aria-label="Community rating scale">
        {([1, 2, 3, 4, 5] as const).map((r) => (
          <CommunityScore key={r} rating={r} />
        ))}
      </div>
      <details className="community-coverage">
        <summary>Collection coverage and freshness</summary>
        <p>
          Up to {communityPolicy.maxPostsPerFeed} recent posts per subreddit per
          collection. RSS titles and available post text; no comment threads,
          votes, or historical crawl. Notes expire after{" "}
          {communityPolicy.retentionDays} days.
        </p>
        {snapshot.feeds.map((f) => (
          <p key={f.subreddit}>
            <strong>r/{f.subreddit}</strong>:{" "}
            {f.fetchedAt
              ? `last successful check ${when(f.fetchedAt)}, ${f.received} posts in the last feed`
              : "not fetched yet"}
            . {f.message}
            {f.attemptedAt && f.status !== "ok" && f.status !== "not-modified"
              ? ` Attempted ${when(f.attemptedAt)}.`
              : ""}
          </p>
        ))}
        <p>
          Confidence describes how clearly the post supports our interpretation,
          not the accuracy of its claims or a fantasy forecast. Context-only
          names have no player score.
        </p>
        <p>
          {snapshot.pendingCount} posts awaiting review.{" "}
          {snapshot.nextFetchAt
            ? `Next RSS collection allowed after ${when(snapshot.nextFetchAt)}.`
            : ""}{" "}
          Reloading here reads the saved library. New collection and review run
          on request.
        </p>
      </details>
      {error && (
        <p className="research-error" role="alert">
          {error}
        </p>
      )}
      {snapshot.feeds.some(
        (f) => f.status === "blocked" || f.status === "error",
      ) && (
        <p className="research-error community-feed-warning" role="status">
          RSS collection paused after a feed error. The last saved notes remain
          below; see collection coverage.
        </p>
      )}
      <div className="guide-filters">
        <label className="search">
          <Search size={16} />
          <input
            aria-label="Search community notes"
            placeholder="Search posts or players"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <select
          aria-label="Community subreddit"
          value={sub}
          onChange={(e) => setSub(e.target.value)}
        >
          <option value="all">Both communities</option>
          <option value="fantasybball">r/fantasybball</option>
          <option value="nba">r/nba</option>
        </select>
        <select
          aria-label="Community rating"
          value={rating}
          onChange={(e) => setRating(e.target.value)}
        >
          <option value="all">All ratings</option>
          {([1, 2, 3, 4, 5] as const).map((r) => (
            <option value={r} key={r}>
              {r} · {ratingLabels[r]}
            </option>
          ))}
        </select>
        <button
          className="text-link"
          onClick={download}
          disabled={!filtered.length}
        >
          <Download size={14} />
          Plain text
        </button>
      </div>
      {!filtered.length && !error && (
        <p className="research-empty">
          {loading
            ? "Loading saved community notes…"
            : snapshot.posts.length
              ? "No posts match these filters."
              : snapshot.pendingCount
                ? "Collected posts are awaiting review."
                : "No reviewed posts in the recent sample yet."}
        </p>
      )}
      <div className="community-scope">
        <label>
          Show{" "}
          <select
            aria-label="Community scope"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
          >
            <option value="players">Player outlooks</option>
            <option value="all">All reviewed posts</option>
          </select>
        </label>
        <span>{filtered.length} posts shown</span>
      </div>
      <div className="community-posts">
        {filtered.map((post) => (
          <article className="community-post" key={post.id}>
            <div className="community-post-meta">
              <span>
                r/{post.subreddit} · {when(post.publishedAt)}
              </span>
              <CommunityScore rating={post.rating} />
            </div>
            <h3>
              <Highlight text={post.title} post={post} onPlayer={onPlayer} />
            </h3>
            <p>
              <Highlight text={post.summary} post={post} onPlayer={onPlayer} />
            </p>
            <small>
              Our assessment · {post.confidence} confidence ·{" "}
              {post.basis === "title" ? "Title only" : "Title + post text"} ·
              Reviewed {when(post.reviewedAt)}
            </small>
            <ul>
              {post.mentions.map((m) => (
                <li
                  key={m.playerId}
                  className={m.playerId === selectedPlayerId ? "selected" : ""}
                >
                  <div>
                    <button
                      className="inline-player"
                      onClick={() => onPlayer(m.playerId)}
                    >
                      <mark>{m.playerName}</mark>
                    </button>
                    <CommunityScore rating={m.rating} />
                  </div>
                  <p>{m.note}</p>
                </li>
              ))}
            </ul>
            {!post.mentions.length && (
              <p className="community-unlinked">
                General discussion; no individual player linked.
              </p>
            )}
            <a
              className="text-link"
              href={post.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Read Reddit post <ArrowUpRight size={13} />
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}
