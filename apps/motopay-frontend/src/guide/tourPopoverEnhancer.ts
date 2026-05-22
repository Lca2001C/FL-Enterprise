import type { PopoverDOM, State } from 'driver.js';
import type { OwnerTourStep } from './ownerTourSteps';

const STEP_PILLS: Record<string, string> = {
  welcome: 'Boas-vindas',
  nav: 'Navegação',
  scope: 'Escopo',
  stats: 'Indicadores',
  alerts: 'Alertas',
  fleet: 'Frota',
  clients: 'Clientes',
  contracts: 'Contratos',
  charges: 'Cobranças',
  finance: 'Financeiro',
  metrics: 'Métricas',
  settings: 'Ajustes',
  automation: 'Automação',
  bot: 'Telegram',
};

export function enhanceTourPopover(
  popover: PopoverDOM,
  state: State,
  metas: OwnerTourStep[]
): void {
  const idx = state.activeIndex ?? 0;
  const meta = metas[idx];
  if (!meta) return;

  const total = metas.length;
  const pct = ((idx + 1) / total) * 100;

  let chrome = popover.wrapper.querySelector('.motopay-tour-chrome') as HTMLElement | null;
  if (!chrome) {
    chrome = document.createElement('div');
    chrome.className = 'motopay-tour-chrome';
    chrome.innerHTML = `
      <div class="motopay-tour-progress-track" aria-hidden="true">
        <div class="motopay-tour-progress-fill"></div>
      </div>
      <div class="motopay-tour-meta">
        <span class="motopay-tour-step-pill"></span>
        <span class="motopay-tour-step-counter"></span>
      </div>
    `;
    popover.wrapper.insertBefore(chrome, popover.title);
  }

  const fill = popover.wrapper.querySelector('.motopay-tour-progress-fill') as HTMLElement | null;
  const pill = popover.wrapper.querySelector('.motopay-tour-step-pill');
  const counter = popover.wrapper.querySelector('.motopay-tour-step-counter');

  if (fill) fill.style.width = `${pct}%`;
  if (pill) pill.textContent = STEP_PILLS[meta.id] ?? meta.title;
  if (counter) counter.textContent = `${idx + 1} / ${total}`;

  popover.wrapper.dataset.tourStep = meta.id;
}
