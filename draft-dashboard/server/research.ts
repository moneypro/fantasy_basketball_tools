import { readFile } from "node:fs/promises";
import path from "node:path";
import { validateResearch, type ResearchLibrary } from "../shared/research.js";

export async function readResearch(season: number): Promise<ResearchLibrary> {
  const file = path.join(
    process.env.RESEARCH_DIR ?? "research",
    "library.json",
  );
  try {
    return validateResearch(JSON.parse(await readFile(file, "utf8")), season);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT")
      return { version: 1, season, articles: [] };
    throw new Error(
      "Draftroom could not read the research library. Check the imported guide data.",
    );
  }
}
