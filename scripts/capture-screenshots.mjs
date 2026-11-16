import { chromium } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, "..", "docs", "images");
const base = "http://127.0.0.1:5173";

const ACCOUNTS = {
  receiver: { email: "receiver@example.com", password: "receiver123" },
  supervisor: { email: "supervisor@example.com", password: "supervisor123" },
};

async function signIn(page, role) {
  const account = ACCOUNTS[role];
  await page.goto(base);
  await page.locator('input[type="email"]').fill(account.email);
  await page.locator('input[type="password"]').fill(account.password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForSelector("main.dashboard", { timeout: 15000 });
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

await signIn(page, "receiver");
await page.waitForTimeout(800);
await page.screenshot({ path: path.join(outDir, "receiver-shelf.png") });

await page.getByRole("button", { name: /log out/i }).click();
await signIn(page, "supervisor");
await page.getByLabel(/order id/i).fill("2");
await page.getByRole("button", { name: /^refresh$/i }).click();
await page.waitForSelector(".status-pill--paid", { timeout: 10000 });
await page.waitForTimeout(400);
await page.screenshot({ path: path.join(outDir, "supervisor-paid.png"), fullPage: true });

await page.locator(".order-record").screenshot({
  path: path.join(outDir, "pgadmin-orders.png"),
});

await browser.close();
console.log("Screenshots written to", outDir);