import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { fixture } from "./fixtures.js";
import { library as guides } from "./research-fixtures.js";
import { communityFixture, communityPost } from "./community-fixtures.js";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/bootstrap", (r) => r.fulfill({ json: fixture }));
  await page.route("**/api/refresh", (r) => r.fulfill({ json: fixture }));
  await page.route("**/api/draft", (r) =>
    r.fulfill({ json: { league: fixture.league, meta: fixture.meta } }),
  );
  await page.route("**/api/research", (r) => r.fulfill({ json: guides }));
  await page.route("**/api/community", (r) =>
    r.fulfill({ json: communityFixture }),
  );
  await page.goto("/");
  await expect(
    page
      .getByRole("navigation")
      .getByRole("button", { name: "Community 2", exact: true }),
  ).toBeVisible();
});

test("community stays separate and draft-board players show attributed per-player scores", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Record pick", exact: true }).click();
  await page
    .getByRole("button", { name: "Record pick #1", exact: true })
    .click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Draft board", exact: true })
    .click();
  await page
    .locator(".draft-board")
    .getByRole("button", { name: /Player 9/ })
    .click();
  const detail = page.locator(".player-detail");
  await detail
    .getByRole("button", { name: "Community (2)", exact: true })
    .click();
  await expect(detail.locator(".community-score")).toHaveText([
    "4/5 · Slightly favorable",
    "2/5 · Slightly unfavorable",
  ]);
  await expect(detail.locator(".player-community-card").first()).toContainText(
    "r/fantasybball",
  );
  await expect(
    detail.locator(".player-community-card a").first(),
  ).toHaveAttribute("href", communityPost.url);
  await expect(detail.locator(".player-guide")).toHaveCount(0);
  await detail.getByRole("button", { name: "Guides (1)", exact: true }).click();
  await expect(
    detail.getByText("Useful at a late price.", { exact: true }),
  ).toBeVisible();
  await expect(detail.locator(".player-community-card")).toHaveCount(0);
  const saved = await page.evaluate(() =>
    Object.values(localStorage)
      .map((x) => JSON.parse(x))
      .find((x) => x.preferences),
  );
  expect(saved.preferences).toEqual({});
});

test("community names select players, context is unscored, and filters and text export work", async ({
  page,
}) => {
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Community 2", exact: true })
    .click();
  const library = page.locator(".community-library");
  await expect(library.locator(".community-post")).toHaveCount(2);
  await library
    .locator(".community-post")
    .first()
    .locator("li")
    .getByRole("button", { name: "Player 3", exact: true })
    .click();
  await expect(page.locator(".player-detail h2")).toHaveText("Player 3");
  await expect(page.locator(".player-detail .community-score")).toHaveText(
    "Context only",
  );
  await page.getByLabel("Community subreddit").selectOption("nba");
  await expect(library.locator(".community-post")).toHaveCount(1);
  await page.getByLabel("Community rating", { exact: true }).selectOption("4");
  await expect(library.locator(".community-post")).toHaveCount(0);
  await page.getByLabel("Community subreddit").selectOption("all");
  await expect(library.locator(".community-post")).toHaveCount(1);
  const event = page.waitForEvent("download");
  await library
    .getByRole("button", { name: "Plain text", exact: true })
    .click();
  const download = await event;
  const text = await readFile((await download.path())!, "utf8");
  expect(text).toContain(communityPost.url);
  expect(text).toContain("Player 3: Context only");
  expect(text).not.toContain("sample2");
  await library
    .getByRole("textbox", { name: "Search community notes" })
    .fill("missing player");
  await expect(library.locator(".community-post")).toHaveCount(0);
});

test("reloading notes uses the local API only, keeps cached notes on failure and exposes coverage", async ({
  page,
}) => {
  const reddit: string[] = [];
  page.on("request", (r) => {
    if (new URL(r.url()).hostname.endsWith("reddit.com")) reddit.push(r.url());
  });
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Community 2", exact: true })
    .click();
  const library = page.locator(".community-library");
  await library
    .getByText("Collection coverage and freshness", { exact: true })
    .click();
  await expect(library.locator(".community-coverage")).toContainText(
    "no comment threads",
  );
  await library
    .getByRole("button", { name: "Reload saved notes", exact: true })
    .click();
  await expect(library.locator(".community-post")).toHaveCount(2);
  expect(reddit).toEqual([]);
  await page.route("**/api/community", (r) => r.abort());
  await library
    .getByRole("button", { name: "Reload saved notes", exact: true })
    .click();
  await expect(library.getByRole("alert")).toContainText(
    "Community updates are unavailable",
  );
  await expect(library.locator(".community-post")).toHaveCount(2);
  const paused = structuredClone(communityFixture);
  paused.feeds[0].status = "blocked" as (typeof paused.feeds)[0]["status"];
  paused.feeds[0].message = "Reddit returned HTTP 429; collection stopped.";
  await page.route("**/api/community", (r) => r.fulfill({ json: paused }));
  await library
    .getByRole("button", { name: "Reload saved notes", exact: true })
    .click();
  await expect(library.locator(".community-feed-warning")).toContainText(
    "collection paused",
  );
  expect(reddit).toEqual([]);
});

test("phone navigation and community name links remain usable without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Community", exact: true })
    .click();
  await page
    .locator(".community-post")
    .first()
    .locator("li")
    .getByRole("button", { name: "Player 3", exact: true })
    .click();
  await expect(page.locator(".player-detail h2")).toHaveText("Player 3");
  await expect(page.locator(".player-detail")).toBeInViewport();
  await expect(page.locator(".player-detail .community-score")).toHaveText(
    "Context only",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
