// One capture only. Joining can interrupt another draft session for this team.
import { chromium } from "playwright";
import { spawnSync, execFileSync } from "node:child_process";
import { createDecipheriv, createHash, pbkdf2Sync } from "node:crypto";
import { fileURLToPath } from "node:url";
const started = Date.now();
const leagueId = Number(process.env.LEAGUE_ID || 30695);
const season = Number(process.env.SEASON_YEAR || 2027);
let browser;
const deadline = setTimeout(() => {
  console.error(
    "Capture stopped after 55 seconds; the previous snapshot is unchanged.",
  );
  Promise.resolve(browser?.close()).finally(() => process.exit(1));
}, 55000);
const query = String.raw`
import sqlite3,json,os
c=sqlite3.connect('file:' + os.environ.get('ESPN_COOKIE_DB', '/home/hong/remote-browser/config/.config/chromium/Default/Cookies') + '?mode=ro',uri=True)
print(json.dumps([{'domain':h,'name':n,'plain':v,'encrypted':e.hex(),'path':p,'expires':t,'secure':bool(s),'httpOnly':bool(o),'sameSite':ss} for h,n,v,e,p,t,s,o,ss in c.execute("SELECT host_key,name,value,encrypted_value,path,expires_utc,is_secure,is_httponly,samesite FROM cookies WHERE host_key='espn.com' OR host_key LIKE '%.espn.com'")]))
c.close()
`;
const res = spawnSync("python3", ["-c", query], { encoding: "utf8" });
if (res.status) throw new Error("Could not read the ESPN browser session.");
const key = pbkdf2Sync("peanuts", "saltysalt", 1, 16, "sha1");
const cookies = JSON.parse(res.stdout)
  .map((c) => {
    let value = c.plain;
    if (!value && c.encrypted) {
      const e = Buffer.from(c.encrypted, "hex");
      if (e.subarray(0, 3).toString() !== "v10")
        throw new Error("Unsupported cookie encryption.");
      const decipher = createDecipheriv(
        "aes-128-cbc",
        key,
        Buffer.alloc(16, 32),
      );
      let decrypted = Buffer.concat([
        decipher.update(e.subarray(3)),
        decipher.final(),
      ]);
      const hash = createHash("sha256").update(c.domain).digest();
      if (decrypted.subarray(0, 32).equals(hash))
        decrypted = decrypted.subarray(32);
      value = decrypted.toString("utf8");
    }
    const expires = c.expires ? c.expires / 1000000 - 11644473600 : -1;
    return {
      name: c.name,
      value,
      domain: c.domain,
      path: c.path,
      expires,
      secure: c.secure,
      httpOnly: c.httpOnly,
      sameSite: c.sameSite === 2 ? "Strict" : c.sameSite === 1 ? "Lax" : "None",
    };
  })
  .filter((c) => c.expires === -1 || c.expires > Date.now() / 1000);

let raw;
let capturedAt;
try {
  browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
    headless: true,
  });
  const context = await browser.newContext();
  await context.addCookies(cookies);
  const page = await context.newPage();
  await page.route("**/*", (route) =>
    ["image", "media", "font"].includes(route.request().resourceType())
      ? route.abort()
      : route.continue(),
  );
  let resolveCapture;
  const captured = new Promise((resolve) => {
    resolveCapture = resolve;
  });
  page.on("websocket", (ws) => {
    if (new URL(ws.url()).hostname !== "fantasydraft.espn.com") return;
    ws.on("framereceived", (event) => {
      const frame =
        typeof event.payload === "string"
          ? event.payload
          : event.payload.toString();
      if (!raw && frame.startsWith("INIT ")) {
        raw = frame;
        capturedAt = new Date().toISOString();
        void context.close().catch(() => {});
        resolveCapture();
      }
    });
  });
  await page.goto(
    `https://fantasy.espn.com/basketball/league?leagueId=${leagueId}&seasonId=${season}`,
    { waitUntil: "domcontentloaded", timeout: 25000 },
  );
  const join = page.getByRole("link", {
    name: "Join Your Draft!",
    exact: true,
  });
  await join.waitFor({ timeout: 15000 });
  const target = new URL(await join.getAttribute("href"), page.url()).href;
  await Promise.race([
    page
      .goto(target, { waitUntil: "domcontentloaded", timeout: 25000 })
      .then(() => captured)
      .catch((error) => {
        if (!raw) throw error;
      }),
    captured,
  ]);
  if (!raw) await captured;
} catch (error) {
  console.error(
    "Capture failed; previous picks retained. " +
      String(error.message).replace(/https?:\/\/\S+/g, "[URL]"),
  );
  process.exitCode = 1;
} finally {
  await browser?.close();
}
if (raw && !process.exitCode) {
  const decoder = fileURLToPath(
    new URL("./decode-live-draft.py", import.meta.url),
  );
  const decoded = spawnSync("python3", [decoder], {
    input: raw,
    encoding: "utf8",
  });
  if (decoded.status !== 0)
    throw new Error(
      "Draft protocol could not be decoded; previous picks retained.",
    );
  const value = JSON.parse(decoded.stdout);
  if (value.leagueId !== leagueId)
    throw new Error("Capture belongs to a different league.");
  const payload = JSON.stringify({ ...value, season, capturedAt });
  const publish = `const fs=require('fs');const input=fs.readFileSync(0,'utf8');JSON.parse(input);fs.writeFileSync('/app/data/live-draft.tmp',input,{mode:0o644});fs.renameSync('/app/data/live-draft.tmp','/app/data/live-draft.json');`;
  execFileSync(
    "docker",
    [
      "exec",
      "-i",
      process.env.DRAFTROOM_CONTAINER || "draft-dashboard-draftroom-1",
      "node",
      "-e",
      publish,
    ],
    { input: payload, timeout: 5000, stdio: ["pipe", "pipe", "pipe"] },
  );
  console.log(
    JSON.stringify({
      capturedAt,
      picks: value.picks.length,
      elapsedSeconds: (Date.now() - started) / 1000,
      disconnected: true,
      published: true,
    }),
  );
}
clearTimeout(deadline);
