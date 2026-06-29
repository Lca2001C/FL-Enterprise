import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const logPath = resolve(dirname(fileURLToPath(import.meta.url)), '../../../.cursor/debug-496b4b.log');
const logs = [];
const log = (entry) => logs.push({ ...entry, timestamp: Date.now(), sessionId: '496b4b' });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const consoleWarnings = [];

page.on('console', (msg) => {
  if (msg.type() === 'warning' || msg.type() === 'error') {
    const text = msg.text();
    if (/entityType|Bricks Payment/i.test(text)) {
      consoleWarnings.push(text);
    }
  }
});

try {
  await page.addInitScript(() => {
    localStorage.setItem('operacao_scope_id', '3');
  });
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.fill('input[type="email"]', 'admin@motopay.local');
  await page.fill('input[type="password"]', 'adminadmin');
  await page.click('button[type="submit"]');
  await page.waitForSelector('[data-tour="nav-cobrancas"]', { timeout: 30000 });
  await page.locator('[data-tour="nav-cobrancas"]').click();
  await page.waitForSelector('.custom-table tbody tr', { timeout: 30000 });

  const payBtn = page.getByRole('button', { name: /^pagar$/i }).first();
  if (!(await payBtn.count())) {
    log({
      location: 'verify-payment-brick',
      message: 'no pay button',
      runId: 'brick-v1',
      hypothesisId: 'H-entity',
      data: {},
    });
  } else {
    await payBtn.click();
    await page.waitForSelector('.modal--payment', { timeout: 15000 });
    await page.getByRole('button', { name: /crédito/i }).click();
    await page.waitForTimeout(4000);

    const brickState = await page.evaluate(() => ({
      brickContainer: !!document.querySelector('.mp-brick-container'),
      paymentIframe: !!document.querySelector('.mp-brick-container iframe'),
      build: window.__MOTOPAY_BUILD__ ?? 'unknown',
    }));
    log({
      location: 'verify-payment-brick',
      message: 'credit brick mounted',
      runId: 'brick-v1',
      hypothesisId: 'H-entity',
      data: { ...brickState, entityTypeWarnings: consoleWarnings },
    });
  }
} catch (err) {
  log({
    location: 'verify-payment-brick',
    message: 'error',
    runId: 'brick-v1',
    hypothesisId: 'H-entity',
    data: { error: String(err), entityTypeWarnings: consoleWarnings },
  });
} finally {
  await browser.close();
  writeFileSync(logPath, logs.map((l) => JSON.stringify(l)).join('\n') + '\n', { flag: 'a' });
  console.log('appended', logs.length, 'lines; entityType warnings:', consoleWarnings.length);
}
