import type { Bootstrap, DraftResponse, League } from "../shared/types";
import { sameLeague } from "../shared/bootstrap";

// IndexedDB works on the LAN's HTTP address and keeps this larger cache
// separate from the localStorage quota used for personal notes and picks.
const database = "draftroom-snapshots-v1";
const store = "snapshots";
const validLeague = (league: League | undefined): league is League =>
  !!league &&
  Number.isInteger(league.id) &&
  Number.isInteger(league.season) &&
  Number.isInteger(league.teamId) &&
  typeof league.name === "string" &&
  typeof league.draftType === "string" &&
  !!league.slots &&
  !!league.weights &&
  Array.isArray(league.teams) &&
  league.teams.every(
    (t) => t && Number.isInteger(t.id) && typeof t.name === "string",
  ) &&
  league.teams.some((t) => t.id === league.teamId) &&
  Array.isArray(league.picks) &&
  league.picks.every(
    (p) =>
      p &&
      Number.isInteger(p.overall) &&
      Number.isInteger(p.round) &&
      Number.isInteger(p.teamId),
  );
function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(database, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(store);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error("Snapshot storage is busy."));
  });
}

export async function readSnapshot(): Promise<Bootstrap | null> {
  try {
    const db = await openDatabase();
    const result = await new Promise<Bootstrap | null>((resolve, reject) => {
      const tx = db.transaction(store, "readonly");
      const data = tx.objectStore(store).get("bootstrap");
      const draft = tx.objectStore(store).get("draft");
      tx.oncomplete = () => {
        db.close();
        const saved = data.result as Bootstrap | undefined;
        if (
          !validLeague(saved?.league) ||
          !saved ||
          !Array.isArray(saved.players) ||
          !Array.isArray(saved.league.teams) ||
          !Array.isArray(saved.league.picks) ||
          !saved.league.slots ||
          !saved.league.weights ||
          !saved.playerMeta?.fetchedAt ||
          !saved.meta?.fetchedAt ||
          !saved.players.every(
            (p) =>
              p &&
              p.id &&
              typeof p.name === "string" &&
              typeof p.team === "string" &&
              typeof p.injury === "string" &&
              typeof p.outlook === "string" &&
              Array.isArray(p.slots) &&
              Array.isArray(p.positions) &&
              p.projected &&
              p.previous,
          )
        ) {
          resolve(null);
          return;
        }
        const latest = draft.result as DraftResponse | undefined;
        const state =
          validLeague(latest?.league) &&
          latest &&
          latest.meta &&
          Array.isArray(latest.league.picks) &&
          sameLeague(saved.league, latest.league) &&
          Date.parse(latest.meta.fetchedAt) >= Date.parse(saved.meta.fetchedAt)
            ? latest
            : saved;
        resolve({
          ...saved,
          league: state.league,
          meta: {
            ...state.meta,
            source: "cache",
            error: "Saved on this browser; live picks have not been verified.",
          },
          playerMeta: { ...saved.playerMeta, source: "cache" },
        });
      };
      tx.onabort = tx.onerror = () => {
        db.close();
        reject(tx.error);
      };
    });
    return result;
  } catch {
    // Private browsing, denied storage or a bad cache must not block startup.
    return null;
  }
}

async function save(key: string, value: Bootstrap | DraftResponse) {
  try {
    const db = await openDatabase();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(store, "readwrite");
      tx.objectStore(store).put(value, key);
      tx.oncomplete = () => {
        db.close();
        resolve();
      };
      tx.onabort = tx.onerror = () => {
        db.close();
        reject(tx.error);
      };
    });
  } catch {
    // Caching is optional and never replaces personal research storage.
  }
}
export const saveSnapshot = (data: Bootstrap) => save("bootstrap", data);
export const saveDraftSnapshot = (data: DraftResponse) => save("draft", data);
