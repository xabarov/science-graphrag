/**
 * Headless UI smoke: HashRouter pages + drawer links + graph canvas clicks.
 * Requires dev stack (e.g. docker compose) and Chromium: `npx playwright install chromium`.
 *
 * @example PW_BASE_URL=http://127.0.0.1:8787/ui npm run pw-smoke
 */
import { chromium } from "playwright";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const BASE = (process.env.PW_BASE_URL || "http://127.0.0.1:8787/ui").replace(/\/$/, "");

function hash(path) {
  return `${BASE}/#${path.startsWith("/") ? path : `/${path}`}`;
}

async function goto(page, path, label) {
  const url = hash(path);
  process.stdout.write(`→ ${label}: ${url}\n`);
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await sleep(800);
  const u = page.url();
  process.stdout.write(`  url: ${u}\n`);
  if (!u.includes(`#${path.startsWith("/") ? path : `/${path}`}`)) {
    throw new Error(`Hash navigation mismatch for ${path}: ${u}`);
  }
}

async function safeClick(page, locator, name) {
  const el = locator.first();
  const n = await el.count();
  if (n === 0) {
    process.stdout.write(`  (skip ${name}: not found)\n`);
    return false;
  }
  await el.click({ timeout: 15_000 });
  process.stdout.write(`  clicked: ${name}\n`);
  await sleep(400);
  return true;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(45_000);

  try {
    await goto(page, "/workspaces", "workspaces");

    await safeClick(page, page.getByRole("link", { name: /^Graph$/i }), "drawer Graph");
    await sleep(800);

    await goto(page, "/graph", "graph direct");
    const canvas = page.locator("canvas").first();
    if ((await canvas.count()) > 0) {
      const box = await canvas.boundingBox();
      if (box) {
        await page.mouse.click(box.x + box.width * 0.35, box.y + box.height * 0.45);
        process.stdout.write("  canvas click (35%, 45%)\n");
        await sleep(300);
        await page.mouse.click(box.x + box.width * 0.55, box.y + box.height * 0.5);
        process.stdout.write("  canvas click (55%, 50%)\n");
        await sleep(300);
      }
    } else {
      process.stdout.write("  (no canvas — empty graph or not canvas mode)\n");
    }

    await goto(page, "/home", "home");

    await safeClick(page, page.getByRole("link", { name: /^Workspaces$/i }), "drawer Workspaces");
    await goto(page, "/reader", "reader");

    await goto(page, "/admin/benchmarks", "admin benchmarks");
    await goto(page, "/admin/settings", "admin settings");

    await safeClick(page, page.getByRole("link", { name: /^Benchmarks$/i }), "drawer Benchmarks");
    await sleep(500);

    await safeClick(page, page.getByRole("link", { name: /^Chat$/i }), "drawer Chat");
    await sleep(400);

    await goto(page, "/graph", "graph again");
    process.stdout.write("OK: smoke navigation finished\n");
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
