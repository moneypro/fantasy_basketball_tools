import { expect, test, type Page } from "@playwright/test";
import { fixture } from "./fixtures.js";
import { emptyCommunity } from "../shared/community.js";

async function routes(page: Page) {
  await page.route("**/api/bootstrap", (r) => r.fulfill({ json: fixture }));
  await page.route("**/api/draft", (r) =>
    r.fulfill({ json: { league: fixture.league, meta: fixture.meta } }),
  );
  await page.route("**/api/refresh", (r) => r.fulfill({ json: fixture }));
  await page.route("**/api/research", (r) =>
    r.fulfill({ json: { version: 1, season: 2027, articles: [] } }),
  );
  await page.route("**/api/community", (r) =>
    r.fulfill({ json: emptyCommunity(2027) }),
  );
}
async function snapshotSaved(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          new Promise<boolean>((resolve) => {
            const open = indexedDB.open("draftroom-snapshots-v1", 1);
            open.onsuccess = () => {
              const db = open.result;
              if (!db.objectStoreNames.contains("snapshots")) {
                db.close();
                resolve(false);
                return;
              }
              const tx = db.transaction("snapshots", "readonly");
              const value = tx.objectStore("snapshots").get("bootstrap");
              tx.oncomplete = () => {
                db.close();
                resolve(!!value.result);
              };
            };
          }),
      ),
    )
    .toBe(true);
}

test("saved data opens while bootstrap stalls, then fresh data arrives without losing notes", async ({
  page,
}) => {
  await routes(page);
  let refreshes = 0;
  await page.route("**/api/refresh", (r) => {
    refreshes++;
    return r.fulfill({ json: fixture });
  });
  await page.goto("/");
  await page
    .getByLabel("Personal player notes")
    .fill("Keep this note during a slow connection.");
  await snapshotSaved(page);
  expect(refreshes).toBe(0);
  let release!: () => void;
  const delay = new Promise<void>((resolve) => {
    release = resolve;
  });
  const updated = structuredClone(fixture);
  updated.players[8].name = "Updated Player Nine";
  updated.playerMeta.fetchedAt = new Date(Date.now() + 1000).toISOString();
  await page.route("**/api/bootstrap", async (r) => {
    await delay;
    await r.fulfill({ json: updated });
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Make your next pick count." }),
  ).toBeVisible({ timeout: 2000 });
  await expect(page.locator(".data-notice")).toContainText(
    "saved data while reconnecting",
  );
  await expect(page.getByLabel("Personal player notes")).toHaveValue(
    "Keep this note during a slow connection.",
  );
  await expect(page.locator(".player-detail .player-identity")).toContainText(
    "Player 9",
  );
  expect(refreshes).toBe(0);
  release();
  await expect(page.locator(".player-detail .player-identity")).toContainText(
    "Updated Player Nine",
  );
  await expect(page.getByLabel("Personal player notes")).toHaveValue(
    "Keep this note during a slow connection.",
  );
});

test("a failed connection keeps the saved draft and allows an in-place retry", async ({
  page,
}) => {
  await routes(page);
  const drafted = structuredClone(fixture);
  drafted.league.picks[0].playerId = 1;
  drafted.meta.fetchedAt = new Date(Date.now() + 1000).toISOString();
  await page.route("**/api/draft", (r) =>
    r.fulfill({ json: { league: drafted.league, meta: drafted.meta } }),
  );
  await page.goto("/");
  await snapshotSaved(page);
  await expect(page.locator(".picks-away")).toContainText("1 / 8");
  // Let the lightweight draft snapshot persist, without downloading players again.
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          new Promise<number>((resolve) => {
            const open = indexedDB.open("draftroom-snapshots-v1", 1);
            open.onsuccess = () => {
              const db = open.result;
              const tx = db.transaction("snapshots", "readonly");
              const req = tx.objectStore("snapshots").get("draft");
              tx.oncomplete = () => {
                db.close();
                resolve(req.result?.league.picks[0].playerId ?? 0);
              };
            };
          }),
      ),
    )
    .toBe(1);
  await page.route("**/api/bootstrap", (r) => r.abort());
  await page.route("**/api/draft", (r) => r.abort());
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Retry connection" }),
  ).toBeVisible();
  await expect(page.locator(".picks-away")).toContainText("1 / 8");
  await expect(page.locator(".connection")).toContainText("Saved draft data");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Positions", exact: true })
    .click();
  await expect(page.locator(".position-pool")).toContainText(
    "19 / 20 players left",
  );
  await page.route("**/api/bootstrap", (r) => r.fulfill({ json: drafted }));
  await page.getByRole("button", { name: "Retry connection" }).click();
  await expect(
    page.getByRole("button", { name: "Retry connection" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "ESPN top 150 remaining" }),
  ).toBeVisible();
});

test("first visit times out promptly and can retry without reloading the page", async ({
  page,
}) => {
  await routes(page);
  await page.addInitScript(() => {
    // Keep the real cancellation behavior while accelerating this one deadline.
    const timeout = AbortSignal.timeout.bind(AbortSignal);
    AbortSignal.timeout = (ms) => timeout(ms === 60000 ? 500 : ms);
  });
  await page.route("**/api/bootstrap", () => {});
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Couldn’t open Draftroom" }),
  ).toBeVisible({ timeout: 2500 });
  await expect(page.getByText(/The connection is too slow/)).toBeVisible();
  await page.route("**/api/bootstrap", (r) => r.fulfill({ json: fixture }));
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Make your next pick count." }),
  ).toBeVisible();
});

test("a denied browser cache still opens from the server", async ({ page }) => {
  await routes(page);
  await page.addInitScript(() => {
    Object.defineProperty(window, "indexedDB", {
      get: () => {
        throw new Error("Storage denied");
      },
    });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Make your next pick count." }),
  ).toBeVisible();
});
