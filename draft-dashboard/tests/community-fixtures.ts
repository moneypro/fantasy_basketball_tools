import { emptyCommunity, type CommunityPost } from "../shared/community.js";
export const communityNow = Date.parse("2026-10-15T22:30:00Z");
export const communityPost: CommunityPost = {
  id: "sample1",
  subreddit: "fantasybball",
  title: "Player 9 can win minutes; Player 3 is a teammate",
  url: "https://www.reddit.com/r/fantasybball/comments/sample1/discussion/",
  publishedAt: "2026-10-15T20:00:00Z",
  collectedAt: "2026-10-15T22:00:00Z",
  reviewedAt: "2026-10-15T22:20:00Z",
  contentHash: "a".repeat(64),
  rating: 4,
  confidence: "medium",
  basis: "title-and-body",
  summary:
    "The poster favors Player 9 at a late price. The role still needs confirmation.",
  mentions: [
    {
      playerId: 9,
      playerName: "Player 9",
      rating: 4,
      note: "The poster expects more minutes; conditional upside.",
    },
    {
      playerId: 3,
      playerName: "Player 3",
      rating: null,
      note: "Mentioned only as a teammate.",
    },
  ],
};
export const communityRisk: CommunityPost = {
  ...communityPost,
  id: "sample2",
  subreddit: "nba",
  url: "https://www.reddit.com/r/nba/comments/sample2/rotation/",
  title: "Player 9 has rotation competition",
  summary: "A different post raises a minutes concern.",
  rating: 2,
  confidence: "low",
  basis: "title",
  mentions: [
    {
      playerId: 9,
      playerName: "Player 9",
      rating: 2,
      note: "Title suggests minutes uncertainty; no comments collected.",
    },
  ],
};
export const communityFixture = {
  ...emptyCommunity(2027),
  posts: [communityPost, communityRisk],
  collectedCount: 2,
  nextFetchAt: "2026-10-16T04:00:00Z",
  feeds: emptyCommunity(2027).feeds.map((f) => ({
    ...f,
    status: "ok" as const,
    received: 1,
    fetchedAt: "2026-10-15T22:00:00Z",
    attemptedAt: "2026-10-15T22:00:00Z",
    message: "Recent RSS sample.",
  })),
};
