import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const logPath = resolve(dirname(fileURLToPath(import.meta.url)), '../../../debug-496b4b.log');
const logs = [];
const log = (e) => logs.push({ ...e, timestamp: Date.now(), sessionId: '496b4b' });

async function runScenario(name, setup) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  if (setup) await context.addInitScript(setup);
  const page = await context.newPage();

  const badUrls = [];
  page.on('request', (req) => {
    const url = req.url();
    if (url.includes('/auth/me') || url.includes('/alerts')) {
      log({
        location: 'verify-network',
        message: 'request',
        data: { scenario: name, url },
        runId: 'full-verify',
        hypothesisId: 'H1',
      });
      if (/^https?:\/\/localhost\/(alerts|api)/.test(url)) {
        badUrls.push(url);
      }
    }
  });
  page.on('response', (res) => {
    const url = res.url();
    if (url.includes('/auth/me') || url.includes('/alerts')) {
      log({
        location: 'verify-network',
        message: 'response',
        data: { scenario: name, url, status: res.status() },
        runId: 'full-verify',
        hypothesisId: 'H1-H4',
      });
    }
  });

  try {
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(2000);
    const beforeLogin = await page.evaluate(() => ({
      href: location.href,
      apiBase: localStorage.getItem('apiBase'),
      bundle: [...document.querySelectorAll('script[src*="/assets/"]')].map((s) => s.getAttribute('src')),
    }));
    log({
      location: 'verify-network',
      message: 'page state',
      data: { scenario: name, ...beforeLogin, badUrls },
      runId: 'full-verify',
      hypothesisId: 'H2-H3',
    });

    if (name !== 'stale-token-only') {
      await page.fill('input[type="email"]', 'admin@motopay.local');
      await page.fill('input[type="password"]', 'adminadmin');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(5000);
    }

    const after = await page.evaluate(() => ({
      href: location.href,
      apiBase: localStorage.getItem('apiBase'),
      hasToken: !!localStorage.getItem('token'),
      bundle: [...document.querySelectorAll('script[src*="/assets/"]')].map((s) => s.getAttribute('src')),
    }));
    log({
      location: 'verify-network',
      message: 'final state',
      data: { scenario: name, ...after, badUrls },
      runId: 'full-verify',
      hypothesisId: 'H2-H4',
    });
  } catch (err) {
    log({
      location: 'verify-network',
      message: 'error',
      data: { scenario: name, error: String(err) },
      runId: 'full-verify',
      hypothesisId: 'H9',
    });
  } finally {
    await browser.close();
  }
}

await runScenario('clean-login', null);
await runScenario('stale-token-bad-apibase', () => {
  localStorage.setItem('token', 'stale-invalid-token');
  localStorage.setItem('refresh_token', 'stale-invalid-refresh');
  localStorage.setItem('apiBase', 'http://localhost');
  localStorage.setItem('operacao_scope_id', '3');
});
await runScenario('stale-token-only', () => {
  localStorage.setItem('token', 'stale-invalid-token');
  localStorage.setItem('refresh_token', 'stale-invalid-refresh');
  localStorage.setItem('apiBase', 'http://localhost');
});

writeFileSync(logPath, logs.map((l) => JSON.stringify(l)).join('\n') + '\n');
const bad = logs.filter((l) => l.data?.badUrls?.length);
console.log('entries', logs.length, 'bad-scenarios', bad.length);
