import { load } from "cheerio";
import { nameSpans } from "../shared/research.js";
import type { Player } from "../shared/types.js";

/** Fetching is separate from publishing. Evidence stays in a local review file. */
export function extractArticle(
  html: string,
  url: string,
  players: Pick<Player, "id" | "name">[],
) {
  const $ = load(html);
  const metadata = $("script[type='application/ld+json']")
    .toArray()
    .flatMap((el) => {
      try {
        const data = JSON.parse($(el).text());
        return Array.isArray(data) ? data : (data["@graph"] ?? [data]);
      } catch {
        return [];
      }
    })
    .find((data) => /Article$/.test(String(data["@type"])));
  const title =
    $("meta[property='og:title']").attr("content") ?? $("h1").first().text();
  const publishedAt =
    metadata?.datePublished ??
    $("meta[property='article:published_time']").attr("content") ??
    $("meta[name='DC.date.issued']").attr("content") ??
    $("meta[name='pubdate']").attr("content") ??
    $("time").first().attr("datetime");
  const structuredAuthors = [metadata?.author]
    .flat()
    .filter(Boolean)
    .map((a) => (typeof a === "string" ? a : a.name))
    .filter((a): a is string => typeof a === "string");
  const scopedAuthors = $(".article-meta .author, article .byline__name")
    .map((_, el) => {
      const author = $(el).clone();
      author.find(".timestamp, time").remove();
      return author.text().trim();
    })
    .get();
  const authors = [
    ...new Set(
      structuredAuthors.length
        ? structuredAuthors
        : scopedAuthors.length
          ? scopedAuthors
          : [$("meta[name='author']").attr("content")].filter(
              (v): v is string => !!v,
            ),
    ),
  ];
  const root = $(".article-body").first().length
    ? $(".article-body").first()
    : $("article").first();
  if (!root.length)
    throw new Error(
      "No article body found. Supply an accessible HTML file or review this source in the signed-in browser.",
    );
  root
    .find(
      "script, style, aside, nav, figure, .inline, .article-meta, .author-bio, .social, .article-tools, .ad-slot, .ad-banner",
    )
    .remove();
  const pool = new Map(players.map((p) => [p.id, p]));
  const names = players.map((p) => ({
    playerId: p.id,
    playerName: p.name,
    aliases: [p.name.replace(/\s+(Jr\.?|Sr\.?|II|III|IV)$/i, "")],
  }));
  const unresolved: { name: string; id: number; reason: string }[] = [];
  let section = "Introduction";
  const blocks = root
    .find("h2, h3, h4, p, li")
    .toArray()
    .flatMap((el) => {
      if ($(el).parents("p, li").length) return [];
      const text = $(el).text().replace(/\s+/g, " ").trim();
      if (!text || /^(Close|Email|Print|Share|Sign up today!)$/.test(text))
        return [];
      const heading = /^h[234]$/.test(el.tagName);
      if (heading) section = text;
      const matches = new Map<
        number,
        {
          playerId: number;
          playerName: string;
          matchedAs: string;
          method: string;
        }
      >();
      $(el)
        .find("a[href]")
        .each((_, a) => {
          let href: URL;
          try {
            href = new URL($(a).attr("href")!, url);
          } catch {
            return;
          }
          const id = /\/nba\/player\/(?:stats\/)?_\/id\/(\d+)/.exec(
            href.pathname,
          )?.[1];
          if (!/(^|\.)espn\.com$/.test(href.hostname) || !id) return;
          const player = pool.get(Number(id));
          if (player)
            matches.set(player.id, {
              playerId: player.id,
              playerName: player.name,
              matchedAs: $(a).text().trim(),
              method: "ESPN player link",
            });
          else
            unresolved.push({
              name: $(a).text().trim(),
              id: Number(id),
              reason: "ESPN-linked player is absent from this season's pool",
            });
        });
      for (const span of nameSpans(text, names)) {
        const player = pool.get(span.playerId)!;
        if (!matches.has(player.id))
          matches.set(player.id, {
            playerId: player.id,
            playerName: player.name,
            matchedAs: text.slice(span.start, span.end),
            method: "Exact full name",
          });
      }
      return [
        {
          kind: heading ? "heading" : "paragraph",
          section,
          text,
          players: [...matches.values()],
        },
      ];
    });
  if (blocks.map((b) => b.text).join(" ").length < 250)
    throw new Error(
      "The article text is missing or incomplete. Review access before importing.",
    );
  const candidates = [
    ...new Map(
      blocks.flatMap((b) => b.players).map((p) => [p.playerId, p]),
    ).values(),
  ];
  return {
    title: title.trim(),
    url,
    authors,
    publishedAt: publishedAt?.slice(0, 10) ?? null,
    fetchedAt: new Date().toISOString(),
    blocks,
    candidates,
    unresolved: [...new Map(unresolved.map((p) => [p.id, p])).values()],
  };
}
