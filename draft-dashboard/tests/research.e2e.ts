import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { fixture } from "./fixtures.js";
import { guide, opposingLibrary } from "./research-fixtures.js";
import { emptyCommunity } from "../shared/community.js";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/bootstrap", (r) => r.fulfill({ json: fixture }));
  await page.route("**/api/community", (r) =>
    r.fulfill({ json: emptyCommunity(2027) }),
  );
  await page.route("**/api/refresh", (r) => r.fulfill({ json: fixture }));
  await page.route("**/api/draft", (r) =>
    r.fulfill({ json: { league: fixture.league, meta: fixture.meta } }),
  );
  await page.route("**/api/research", (r) =>
    r.fulfill({ json: opposingLibrary }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("navigation").getByRole("button", { name: "Guides 2" }),
  ).toBeVisible();
});

test("draft board player opens attributed conflicting opinions without setting personal flags", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Record pick", exact: true }).click();
  await page.getByRole("button", { name: "Record pick #1" }).click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Draft board" })
    .click();
  await page
    .locator(".draft-board")
    .getByRole("button", { name: /Player 9/ })
    .click();
  const detail = page.locator(".player-detail");
  await detail.getByRole("button", { name: "Guides (2)", exact: true }).click();
  await expect(
    detail.getByText("Useful at a late price.", { exact: true }),
  ).toBeVisible();
  await expect(
    detail.getByText("Avoid paying an early-round price.", { exact: true }),
  ).toBeVisible();
  await expect(detail.locator(".tag-target")).toHaveText("Draft target");
  await expect(detail.locator(".tag-avoid")).toHaveText("Do not draft");
  await expect(detail.getByText("Targets", { exact: true })).toBeVisible();
  await expect(page.locator(".shortlist-row")).toHaveCount(0);
  const saved = await page.evaluate(() =>
    Object.values(localStorage)
      .map((value) => JSON.parse(value))
      .find((value) => value.preferences),
  );
  expect(saved.preferences).toEqual({});
  await detail.getByRole("button", { name: guide.title, exact: true }).click();
  await expect(
    page.locator(".guide-reader").getByRole("heading", { name: guide.title }),
  ).toBeVisible();
});

test("plain text guide links every named player and distinguishes context", async ({
  page,
}) => {
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Guides 2" })
    .click();
  const reader = page.locator(".guide-reader");
  await expect(
    reader.getByRole("link", { name: "Read original article" }),
  ).toHaveAttribute("href", guide.url);
  await reader
    .locator(".guide-summary")
    .getByRole("button", { name: "Player 3", exact: true })
    .click();
  await expect(page.locator(".player-detail h2")).toHaveText("Player 3");
  await expect(page.locator(".player-detail .tag-mention")).toHaveText(
    "Context only",
  );
  await expect(
    page
      .locator(".player-detail")
      .getByText("Mentioned for context; no recommendation assigned."),
  ).toBeVisible();
  await expect(reader.locator(".guide-context")).toHaveAttribute("open", "");
  const downloaded = page.waitForEvent("download");
  await reader.getByRole("button", { name: "Plain text", exact: true }).click();
  const download = await downloaded;
  expect(download.suggestedFilename()).toBe("test-guide.txt");
  const text = await readFile((await download.path())!, "utf8");
  expect(text).toContain(guide.url);
  expect(text).toContain("Player 9 — Draft target");
  expect(text).toContain("Player 3 — Context only");
  expect(text).not.toContain("<mark>");
  await page
    .getByRole("textbox", { name: "Search research guides" })
    .fill("Sam Skeptic");
  await expect(page.locator(".guide-list-item")).toHaveCount(1);
  await expect(
    reader.getByRole("heading", { name: "An opposing view" }),
  ).toBeVisible();
  await page.getByRole("textbox", { name: "Search research guides" }).fill("");
  await page.getByLabel("Filter guide opinions").selectOption("mention");
  await expect(page.locator(".guide-list-item")).toHaveCount(1);
  await expect(
    reader.getByRole("heading", { name: guide.title }),
  ).toBeVisible();
});

test("refresh replaces source notes and shows retained notes when the library is unavailable", async ({
  page,
}) => {
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Guides 2" })
    .click();
  const updated = structuredClone(opposingLibrary);
  updated.articles[0].mentions[0].note = "Revised after new rotation news.";
  updated.articles[0].mentions[0].tags = ["watch"];
  await page.route("**/api/research", (r) => r.fulfill({ json: updated }));
  await page
    .getByRole("button", { name: "Refresh guides", exact: true })
    .click();
  await expect(page.locator(".guide-reader")).toContainText(
    "Revised after new rotation news.",
  );
  await expect(page.locator(".guide-reader .tag-target")).toHaveCount(0);
  await expect(page.locator(".guide-list-item")).toHaveCount(2);
  await page.route("**/api/research", (r) => r.abort());
  await page
    .getByRole("button", { name: "Refresh guides", exact: true })
    .click();
  await expect(page.locator(".guide-library").getByRole("alert")).toContainText(
    "Guide updates are unavailable",
  );
  await expect(page.locator(".guide-reader")).toContainText(
    "Revised after new rotation news.",
  );
  await page.reload();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Guides 0" })
    .click();
  await expect(page.locator(".guide-library").getByRole("alert")).toContainText(
    "Guide updates are unavailable",
  );
  await page.route("**/api/research", (r) => r.fulfill({ json: updated }));
  await page
    .getByRole("button", { name: "Refresh guides", exact: true })
    .click();
  await expect(page.locator(".guide-library").getByRole("alert")).toHaveCount(
    0,
  );
  await expect(page.locator(".guide-list-item")).toHaveCount(2);
});

test("guide reading and selecting names work on a narrow phone", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("navigation")
    .getByRole("button", { name: /^Guides/ })
    .click();
  await page
    .locator(".guide-reader .guide-summary")
    .getByRole("button", { name: "Player 3", exact: true })
    .click();
  await expect(page.locator(".player-detail h2")).toHaveText("Player 3");
  await expect(page.locator(".player-detail")).toBeInViewport();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
