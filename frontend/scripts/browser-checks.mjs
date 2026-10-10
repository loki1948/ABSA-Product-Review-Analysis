// Browser checks against the running application, with real input events:
// keyboard-only use of the Analyzer, CSV upload through the file picker, the
// CSV download, phone-width layout on every page, and the screenshots in
// docs/screenshots.
//
// Needs the backend (with models) on :8000, `npm run dev` on :5173 and Chrome.
//   npm install --no-save puppeteer-core
//   node scripts/browser-checks.mjs
// Set CHROME_PATH if Chrome is not in its default Windows location. Reviews
// analysed by this script are saved to the history of the running backend.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const BASE = process.env.APP_URL ?? "http://localhost:5173";
const SHOTS = path.join(ROOT, "docs", "screenshots");
const DOWNLOADS = fs.mkdtempSync(path.join(os.tmpdir(), "absa-downloads-"));
const CSV = path.join(ROOT, "data", "samples", "demo_reviews.csv");
const CHROME = process.env.CHROME_PATH ?? "C:/Program Files/Google/Chrome/Application/chrome.exe";
fs.mkdirSync(SHOTS, { recursive: true });

const results = {};
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--no-first-run", "--disable-extensions"],
});
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
const client = await page.createCDPSession();
await client.send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: DOWNLOADS });

const shot = (name) => page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
const text = (selector) => page.$$eval(selector, (found) => found[0].innerText).catch(() => null);
const clickButton = async (label) => {
  const handle = await page.evaluateHandle(
    (l) => [...document.querySelectorAll("button")].find((b) => b.textContent.trim().startsWith(l)), label);
  await handle.asElement().click();
};
const waitIdle = () => page.waitForNetworkIdle({ idleTime: 600, timeout: 60000 });

// ---- 1. Desktop: keyboard-only run through the Analyzer -------------------
await page.setViewport({ width: 1366, height: 900 });
await page.goto(`${BASE}/analyze`, { waitUntil: "networkidle0" });
await page.focus("#review");
await page.keyboard.type("The screen is gorgeous and the keyboard feels great, but the battery life is terrible.");
await page.keyboard.down("Control"); await page.keyboard.press("Enter"); await page.keyboard.up("Control");
await page.waitForSelector("mark", { timeout: 60000 });
results.keyboardCtrlEnter = await page.$$eval("mark", (ms) => ms.map((m) => m.title));
await shot("analyzer-result");
// Tab order from the text area: Analyze button, then the save checkbox.
await page.focus("#review");
await page.keyboard.press("Tab");
results.tab1 = await page.evaluate(() => document.activeElement.textContent.trim());
await page.keyboard.press("Tab");
results.tab2 = await page.evaluate(() => document.activeElement.type);
await page.keyboard.press("Space");
results.saveToggledByKeyboard = await page.evaluate(() => document.activeElement.checked === false);
await page.keyboard.press("Space");
// Submit with the keyboard from the button.
await page.focus("#review"); await page.keyboard.press("Tab"); await page.keyboard.press("Enter");
await waitIdle();
results.submitWithEnterOnButton = (await page.$$("mark")).length;

// ---- 2. Batch: real file picker upload and real CSV download ---------------
await page.goto(`${BASE}/batch`, { waitUntil: "networkidle0" });
await shot("batch-empty");
const input = await page.$("#batch-file");
await input.uploadFile(CSV);
await page.waitForFunction(() => document.querySelector("#batch-text").value.length > 50);
results.batchButton = await page.evaluate(
  () => [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Analyze")).textContent.trim());
await clickButton("Analyze");
await page.waitForFunction(
  () => /Analysed \d+ of \d+ reviews\.$/.test(document.querySelector('section > [role=status] p')?.textContent ?? ""),
  { timeout: 120000 });
results.batchStatus = await text("section > [role=status] p");
results.batchRows = (await page.$$("table tbody tr")).length;
await shot("batch-results");
await clickButton("Download results");
await new Promise((r) => setTimeout(r, 1500));
const files = fs.readdirSync(DOWNLOADS);
results.downloadedFile = files[0] ?? null;
if (files[0]) {
  const csv = fs.readFileSync(path.join(DOWNLOADS, files[0]), "utf8");
  const lines = csv.trim().split(/\r\n/);
  results.downloadHeader = lines[0];
  results.downloadDataRows = lines.length - 1;
  results.downloadFirstRow = lines[1];
}

// ---- 3. History and Dashboard screenshots ---------------------------------
await page.goto(`${BASE}/history`, { waitUntil: "networkidle0" });
await page.click('button[aria-label^="View"]');
await shot("history");
await page.goto(`${BASE}/dashboard`, { waitUntil: "networkidle0" });
await new Promise((r) => setTimeout(r, 800));
await shot("dashboard");
await page.goto(`${BASE}/`, { waitUntil: "networkidle0" });
await shot("home");

// ---- 4. Phone width (390 px): no sideways scrolling, nothing cut off -------
await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
results.phone = {};
for (const [name, url] of [["home", "/"], ["analyzer", "/analyze"], ["batch", "/batch"], ["history", "/history"], ["dashboard", "/dashboard"]]) {
  await page.goto(`${BASE}${url}`, { waitUntil: "networkidle0" });
  if (name === "analyzer") {
    await clickButton("Restaurant review");
    await clickButton("Analyze Review");
    await page.waitForSelector("mark", { timeout: 60000 });
  }
  await new Promise((r) => setTimeout(r, 500));
  results.phone[name] = await page.evaluate(() => ({
    innerWidth,
    pageScrollsSideways: document.documentElement.scrollWidth > innerWidth + 1,
    cutOff: [...document.querySelectorAll("main *, header *")]
      .filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 1 && !e.closest(".overflow-x-auto"); })
      .slice(0, 4).map((e) => `${e.tagName.toLowerCase()}:${(e.textContent || "").trim().slice(0, 30)}`),
    smallTapTargets: [...document.querySelectorAll("main button, main a, header a")]
      .filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height < 24; })
      .map((e) => `${e.textContent.trim().slice(0, 20)} (${Math.round(e.getBoundingClientRect().height)}px)`).slice(0, 6),
  }));
  await shot(`phone-${name}`);
}

results.browserErrors = errors.slice(0, 8);
await browser.close();
console.log(JSON.stringify(results, null, 1));
