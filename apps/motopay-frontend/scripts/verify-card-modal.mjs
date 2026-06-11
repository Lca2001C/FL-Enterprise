import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const logPath = resolve(dirname(fileURLToPath(import.meta.url)), '../../../debug-496b4b.log');
const logs = [];
const log = (entry) => logs.push({ ...entry, timestamp: Date.now(), sessionId: '496b4b' });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on('dialog', (dialog) => void dialog.dismiss());

try {
  await page.addInitScript(() => {
    localStorage.setItem('operacao_scope_id', '3');
  });
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.fill('input[type="email"]', 'admin@motopay.local');
  await page.fill('input[type="password"]', 'adminadmin');
  await page.click('button[type="submit"]');
  await page.waitForSelector('[data-tour="nav-clientes"]', { timeout: 30000 });
  await page.locator('[data-tour="nav-clientes"]').click();
  await page.waitForSelector('.custom-table tbody tr', { timeout: 30000 });

  await page.locator('button.icon-btn[title="Cartões Mercado Pago"]').first().click();
  await page.waitForSelector('.modal--payment', { timeout: 10000 });
  await page.waitForFunction(
    () => !document.querySelector('.modal--payment')?.textContent?.includes('Carregando'),
    { timeout: 15000 }
  );

  const addBtn = page.getByRole('button', { name: /adicionar cartão/i });
  if (await addBtn.count()) {
    await addBtn.click();
    await page.waitForSelector('.mp-secure-fields-form', { timeout: 15000 });
    await page.waitForTimeout(2000);

    const formOpen = await page.evaluate(() => ({
      overlayLocked: document.querySelector('.modal-overlay')?.classList.contains('modal-overlay--locked'),
      modalInDom: !!document.querySelector('.modal--payment'),
    }));
    log({
      location: 'verify-card-modal',
      message: 'form open',
      runId: 'card-v1',
      hypothesisId: 'H1',
      data: formOpen,
    });

    await page.locator('#mp-cardholder').fill('APRO');
    await page.waitForTimeout(500);

    const afterFill = await page.evaluate(() => ({
      modalInDom: !!document.querySelector('.modal--payment'),
      formInDom: !!document.querySelector('.mp-secure-fields-form'),
      overlayLocked: document.querySelector('.modal-overlay')?.classList.contains('modal-overlay--locked'),
    }));
    log({
      location: 'verify-card-modal',
      message: 'after cardholder fill',
      runId: 'card-v1',
      hypothesisId: 'H2',
      data: afterFill,
    });

    const overlayBox = await page.locator('.modal-overlay').boundingBox();
    if (overlayBox) {
      await page.mouse.click(overlayBox.x + 8, overlayBox.y + 8);
      await page.waitForTimeout(300);
    }
    const afterOverlayClick = await page.evaluate(() => ({
      modalInDom: !!document.querySelector('.modal--payment'),
      overlayLocked: document.querySelector('.modal-overlay')?.classList.contains('modal-overlay--locked'),
    }));
    log({
      location: 'verify-card-modal',
      message: 'after overlay corner click',
      runId: 'card-v1',
      hypothesisId: 'H1',
      data: afterOverlayClick,
    });

    const fecharVisible = await page.getByRole('button', { name: /^fechar$/i }).count();
    log({
      location: 'verify-card-modal',
      message: 'fechar button while form open',
      runId: 'card-v1',
      hypothesisId: 'H4',
      data: { fecharVisible, modalInDom: afterOverlayClick.modalInDom },
    });
  } else {
    log({
      location: 'verify-card-modal',
      message: 'no add button',
      runId: 'card-v1',
      hypothesisId: 'H3',
      data: { text: await page.locator('.modal--payment').innerText() },
    });
  }
} catch (err) {
  log({
    location: 'verify-card-modal',
    message: 'error',
    runId: 'card-v1',
    hypothesisId: 'H9',
    data: { error: String(err) },
  });
} finally {
  await browser.close();
  writeFileSync(logPath, logs.map((l) => JSON.stringify(l)).join('\n') + '\n');
  console.log('wrote', logs.length, 'lines');
}
