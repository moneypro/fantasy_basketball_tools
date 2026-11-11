import { expect, test } from "@playwright/test";
import { fixture, player } from "./fixtures.js";
import { emptyCommunity } from "../shared/community.js";
import { emptyState } from "../shared/draft.js";

test("positions follow picks, flex eligibility, undo, rehearsal, and mobile navigation", async ({
  page,
}) => {
  const data = structuredClone(fixture);
  data.players = [
    player(1, ["C", "PF/C", "F/C", "UT"]),
    player(2, ["SG", "SF", "G", "F", "SG/SF", "G/F", "F/C", "UT"]),
    player(150, ["PG", "G", "G/F", "UT"]),
    player(151, ["PF", "F", "G/F", "PF/C", "F/C", "UT"]),
  ];
  data.league.picks[0].playerId = 1;
  const saved = emptyState(data.league);
  saved.manualPicks = [{ ...data.league.picks[1], playerId: 2, local: true }];
  await page.addInitScript(
    ({ key, saved }) => localStorage.setItem(key, JSON.stringify(saved)),
    { key: "draftroom:v1:123:2027:2", saved },
  );
  await page.route("**/api/bootstrap", (r) => r.fulfill({ json: data }));
  await page.route("**/api/refresh", (r) => r.fulfill({ json: data }));
  await page.route("**/api/draft", (r) =>
    r.fulfill({ json: { league: data.league, meta: data.meta } }),
  );
  await page.route("**/api/research", (r) =>
    r.fulfill({ json: { version: 1, season: 2027, articles: [] } }),
  );
  await page.route("**/api/community", (r) =>
    r.fulfill({ json: emptyCommunity(2027) }),
  );
  await page.goto("/");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Positions", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "ESPN top 150 remaining" }),
  ).toBeVisible();
  await expect(page.locator(".position-pool")).toContainText(
    "1 / 3 players left",
  );
  await expect(page.locator(".position-totals button")).toHaveCount(7);
  await expect(
    page.getByRole("button", {
      name: "C: 0 of 1 top 150 players left",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: "F: 0 of 1 top 150 players left",
      exact: true,
    }),
  ).toBeVisible();
  for (const position of ["SG", "SF", "F", "G"])
    await expect(
      page.getByRole("button", {
        name: `My Team, ${position}: 1 candidates`,
        exact: true,
      }),
    ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: "First Team, F: 0 candidates",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "My Team, G: 1 candidates", exact: true })
    .click();
  await page
    .getByLabel("My Team G candidates", { exact: true })
    .getByRole("button", { name: /Player 2/ })
    .click();
  await expect(page.locator(".player-detail .player-identity")).toContainText(
    "Player 2",
  );

  await page.getByRole("button", { name: "Rehearsal mode" }).click();
  await expect(page.locator(".position-pool")).toContainText(
    "3 / 3 players left",
  );
  await expect(
    page.getByRole("heading", { name: "Practice position coverage" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "My Team, G: 0 candidates", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Exit rehearsal" }).click();
  await expect(page.locator(".position-pool")).toContainText(
    "1 / 3 players left",
  );
  await page.getByRole("button", { name: "Undo local pick" }).click();
  await expect(page.locator(".position-pool")).toContainText(
    "2 / 3 players left",
  );
  await expect(
    page.getByRole("button", { name: "My Team, G: 0 candidates", exact: true }),
  ).toBeVisible();

  // An incoming ESPN pick changes both availability and team coverage.
  data.league.picks[1].playerId = 150;
  await expect(
    page.getByRole("button", {
      name: "PG: 0 of 1 top 150 players left",
      exact: true,
    }),
  ).toBeVisible({ timeout: 12000 });
  await expect(
    page.getByRole("button", {
      name: "My Team, PG: 1 candidates",
      exact: true,
    }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("button", {
      name: "F: 1 of 1 top 150 players left",
      exact: true,
    })
    .click();
  await expect(
    page.getByLabel("Available F candidates", { exact: true }),
  ).toContainText("Player 2");
  await expect(
    page.getByLabel("Available F candidates", { exact: true }),
  ).not.toContainText("Player 151");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const coverage = page.getByRole("region", { name: "Team position coverage" });
  await coverage.evaluate((el) => {
    el.scrollLeft = el.scrollWidth;
  });
  await page
    .getByRole("button", { name: "My Team, G: 1 candidates", exact: true })
    .click();
  await expect(
    page.getByLabel("My Team G candidates", { exact: true }),
  ).toContainText("Player 150");
});
