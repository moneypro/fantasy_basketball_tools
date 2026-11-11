import type { ResearchArticle, ResearchLibrary } from "../shared/research.js";

export const guide: ResearchArticle = {
  id: "test-guide",
  season: 2027,
  title: "Price-sensitive draft advice",
  url: "https://example.com/guide",
  publisher: "Test analyst",
  authors: ["Alex Analyst"],
  publishedAt: "2026-10-01",
  reviewedAt: "2026-10-15T00:00:00Z",
  format: "points",
  summary: "Player 9 is a target; Player 3 is discussed only as a teammate.",
  mentions: [
    {
      playerId: 9,
      playerName: "Player 9",
      tags: ["target"],
      note: "Useful at a late price.",
      section: "Targets",
    },
    {
      playerId: 3,
      playerName: "Player 3",
      tags: ["mention"],
      note: "",
      section: "Context",
    },
  ],
};
export const library: ResearchLibrary = {
  version: 1,
  season: 2027,
  articles: [guide],
};

export const opposingGuide: ResearchArticle = {
  ...guide,
  id: "second-guide",
  title: "An opposing view",
  url: "https://example.com/second-guide",
  authors: ["Sam Skeptic"],
  summary: "Player 9 carries risk at an early price.",
  mentions: [
    {
      playerId: 9,
      playerName: "Player 9",
      tags: ["avoid"],
      note: "Avoid paying an early-round price.",
      section: "Do not draft",
      analyst: "Sam Skeptic",
    },
  ],
};
export const opposingLibrary: ResearchLibrary = {
  ...library,
  articles: [guide, opposingGuide],
};
