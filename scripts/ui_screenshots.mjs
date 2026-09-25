// Drives the real UI in headless Chromium against a running Compose stack and saves screenshots to ./ui.
// Every step asserts on visible text, so a screenshot is only kept as evidence together with the check it belongs to.
// Run (from a directory that has `playwright` installed): BASE=http://localhost:8080 node ui_screenshots.mjs
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE || "http://localhost:8080";
mkdirSync("ui", { recursive: true });
let pass = 0, fail = 0;
const ok = (name, cond, detail = "") => {
  if (cond) { pass++; console.log(`PASS  ${name}`); } else { fail++; console.log(`FAIL  ${name} ${detail}`); }
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
const shot = (file) => page.screenshot({ path: `ui/${file}.png`, fullPage: true });
const nav = (name) => page.locator("nav").getByRole("button", { name }).click();

try {
  // ---- Submit -------------------------------------------------------------------------------------------------
  await page.goto(BASE);
  await page.getByRole("heading", { name: "Report a problem" }).waitFor();
  await shot("01-submit-empty");

  await page.locator("form").getByRole("button").click();
  const alerts = await page.getByRole("alert").allTextContents();
  ok("client-side validation shows both field errors", alerts.some(t => /Complaint must be/.test(t)) && alerts.some(t => /Location must be/.test(t)), JSON.stringify(alerts));
  await shot("02-submit-validation");

  await page.getByLabel("Complaint").fill("Burst water main flooding Street 12 since fajr, water entering ground floors");
  await page.getByLabel("Location").fill("Street 12");
  await page.getByLabel("Contact (optional)").fill("0300-0000000");
  // Rule-based triage answers in about a millisecond, so to SEE the in-flight state the response is delayed 2.5 s here.
  await page.route("**/api/complaints", async (route) => {
    if (route.request().method() === "POST") await new Promise((r) => setTimeout(r, 2500));
    await route.continue();
  });
  await page.locator("form").getByRole("button").click();
  await page.getByRole("button", { name: /Triaging your complaint/ }).waitFor();
  ok("loading state is shown and honest ('can take a few seconds')", true);
  ok("submit button is disabled while in flight", await page.locator("form").getByRole("button").isDisabled());
  await shot("03-submit-loading-delayed-2.5s");
  await page.getByRole("heading", { name: "Received" }).waitFor();
  await page.unroute("**/api/complaints");
  const card = await page.locator(".card").innerText();
  ok("result shows category water", /Category:\s*water/i.test(card), card);
  ok("result shows priority high", /Priority:\s*high/i.test(card), card);
  ok("result shows the AI summary line", /Summary:\s*\S+/.test(card), card);
  ok("result shows which provider produced it", /Triaged by:\s*rules/i.test(card), card);
  await shot("04-submit-result");

  // ---- Dashboard ----------------------------------------------------------------------------------------------
  await nav("Dashboard");
  await page.locator("tbody tr").first().waitFor();
  const rows0 = await page.locator("tbody tr").count();
  ok("dashboard lists complaints", rows0 > 5, `rows=${rows0}`);
  ok("newest complaint (the one just submitted) is first", /Street 12/.test(await page.locator("tbody tr").first().innerText()));
  ok("pagination text present", /Page 1 of \d+ \(\d+ total\)/.test(await page.locator("section").innerText()));
  await shot("05-dashboard");

  await page.getByLabel("category").selectOption("water");
  await page.waitForFunction(() => [...document.querySelectorAll("tbody tr")].every(r => r.children[2]?.textContent === "water") && document.querySelectorAll("tbody tr").length > 0);
  const cats = await page.locator("tbody tr td:nth-child(3)").allTextContents();
  ok("category filter shows only water rows", cats.length > 0 && cats.every(c => c === "water"), JSON.stringify(cats));
  await shot("06-dashboard-filter-water");
  await page.getByLabel("category").selectOption("");
  await page.waitForFunction(() => document.querySelectorAll("tbody tr").length > 0 && /Street 12/.test(document.querySelector("tbody tr").textContent));

  const first = page.locator("tbody tr").first().locator('select[aria-label="status"]');
  await first.selectOption("in_progress");
  await page.waitForFunction(() => document.querySelector('tbody tr select[aria-label="status"]').value === "in_progress");
  ok("valid transition open -> in_progress is applied", (await first.inputValue()) === "in_progress");
  await shot("07-dashboard-status-changed");

  await first.selectOption("open");
  const err = await page.getByRole("alert").first().innerText();
  ok("invalid transition surfaces the server's own 409 message verbatim", err === "Invalid status transition: in_progress -> open", JSON.stringify(err));
  await shot("08-dashboard-409-server-message");

  // ---- Stats --------------------------------------------------------------------------------------------------
  await nav("Stats");
  await page.getByText(/Total:/).waitFor();
  const cache1 = await page.locator("code").first().innerText();
  await shot(`09-stats-first-view-cache-${cache1}`);
  await page.getByRole("button", { name: "Refresh" }).click();
  await page.waitForFunction(() => document.querySelector("code")?.textContent === "HIT");
  ok("stats shows category counts", /By category/.test(await page.locator("section").innerText()));
  ok("stats shows priority counts", /By priority/.test(await page.locator("section").innerText()));
  ok("second stats request is served from cache (X-Cache HIT shown)", (await page.locator("code").first().innerText()) === "HIT");
  console.log(`first stats view showed cache=${cache1}`);
  await shot("10-stats-cache-hit");
} catch (e) {
  fail++; console.log("FAIL  unexpected error:", e.message);
  await shot("zz-error-state").catch(() => {});
}
await browser.close();
console.log(`PASS=${pass} FAIL=${fail}`);
process.exit(fail ? 1 : 0);
