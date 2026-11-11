import { test, expect } from "@playwright/test";
import { fixture } from "./fixtures.js";
import { emptyPreference, emptyState } from "../shared/draft.js";
import { readFile } from "node:fs/promises";
import { library } from "./research-fixtures.js";
import { emptyCommunity } from "../shared/community.js";
test.beforeEach(async ({ page }) => {
  await page.route("**/api/bootstrap", (r) => r.fulfill({ json: fixture }));
  await page.route("**/api/community", (r) =>
    r.fulfill({ json: emptyCommunity(2027) }),
  );
  await page.route("**/api/research", (r) => r.fulfill({ json: library }));
  await page.route("**/api/draft", (r) =>
    r.fulfill({
      json: {
        league: fixture.league,
        meta: { source: "live", fetchedAt: new Date().toISOString() },
      },
    }),
  );
  await page.route("**/api/refresh", (r) => r.fulfill({ json: fixture }));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Make your next pick count." }),
  ).toBeVisible();
});
test("shortlist and notes survive reload and comparisons work", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Shortlist Player 3", exact: true })
    .click();
  await page.locator(".player-name").filter({ hasText: "Player 3" }).click();
  await page
    .getByRole("textbox", { name: "Personal player notes" })
    .fill("Target in round 3. Check minutes.");
  await page.getByRole("textbox", { name: "Player tier" }).fill("B");
  await page.reload();
  await page.locator(".shortlist-row").filter({ hasText: "Player 3" }).click();
  await expect(
    page.getByRole("textbox", { name: "Personal player notes" }),
  ).toHaveValue("Target in round 3. Check minutes.");
  await expect(page.getByRole("textbox", { name: "Player tier" })).toHaveValue(
    "B",
  );
  await page
    .getByRole("button", { name: "Compare Player 3", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Compare Player 4", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Compare players", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("dialog").getByText("Projected games"),
  ).toHaveCount(2);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
test("manual pick, undo, roster, and rehearsal remain separate", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Record pick", exact: true }).click();
  await page.getByLabel("Drafting team").selectOption("2");
  await page.getByRole("button", { name: "Record pick #1" }).click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: /My roster/ })
    .click();
  await expect(
    page.locator(".roster-row").filter({ hasText: "Player 9" }),
  ).toHaveCount(1);
  await page.getByRole("button", { name: "Rehearsal mode" }).click();
  await expect(
    page.locator(".roster-row").filter({ hasText: "Player 9" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Advance to my turn" }).click();
  await expect(page.locator(".picks-away")).toContainText("You’re up.");
  await page.getByRole("button", { name: "Exit rehearsal" }).click();
  await expect(
    page.locator(".roster-row").filter({ hasText: "Player 9" }),
  ).toHaveCount(1);
  await page.getByRole("button", { name: "Undo local pick" }).click();
  await expect(
    page.locator(".roster-row").filter({ hasText: "Player 9" }),
  ).toHaveCount(0);
});
test("offline sync and mobile viewport keep the dashboard usable", async ({
  page,
}) => {
  await page.route("**/api/draft", (r) => r.abort());
  await expect(page.locator(".connection")).toContainText("Saved draft data", {
    timeout: 12000,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("textbox", { name: "Search players" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("textbox", { name: "Search players" }).fill("Player 4");
  await expect(page.locator(".player-table tbody tr")).toHaveCount(1);
});

test("backup restores research and rejects the wrong season without losing notes", async ({
  page,
}) => {
  const backup = emptyState(fixture.league);
  backup.preferences["9"] = {
    ...emptyPreference(),
    target: true,
    note: "Saved before draft night.",
    tier: "A",
  };
  page.on("dialog", (d) => d.accept());
  await page.locator("input[type=file]").setInputFiles({
    name: "backup.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(backup)),
  });
  await expect(
    page.getByRole("textbox", { name: "Personal player notes" }),
  ).toHaveValue("Saved before draft night.");
  await page.locator("input[type=file]").setInputFiles({
    name: "wrong-season.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({ ...backup, season: 2026 })),
  });
  await expect(page.getByRole("status")).toContainText(
    "another league, team, or season",
  );
  await expect(
    page.getByRole("textbox", { name: "Personal player notes" }),
  ).toHaveValue("Saved before draft night.");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("draftroom-2027-team-2.json");
});

test("AI briefing exports notes and the question, and labels an offline snapshot", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Personal player notes" })
    .fill("Watch preseason minutes.");
  await page.getByRole("button", { name: "AI briefing", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "AI briefing" });
  await expect(dialog).toBeVisible();
  await dialog
    .getByRole("textbox", { name: "Question for the assistant" })
    .fill("Who fits my next pick?");
  const preview = dialog.getByRole("textbox", { name: "Briefing text" });
  await expect(preview).toHaveValue(/Watch preseason minutes/);
  await expect(preview).toHaveValue(/Who fits my next pick\?/);
  const downloadPromise = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "Download .txt" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(
    "draftroom-2027-team-2-briefing.txt",
  );
  const text = await readFile((await download.path())!, "utf8");
  expect(text).toBe(await preview.inputValue());
  expect(text).toContain("GET /api/draft");
  await page.route("**/api/draft", (r) => r.abort());
  await dialog.getByRole("button", { name: "Refresh snapshot" }).click();
  await expect(preview).toHaveValue(/STALE OR UNVERIFIED/);
  await expect(preview).toHaveValue(/Watch preseason minutes/);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
