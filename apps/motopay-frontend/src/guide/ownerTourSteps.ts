import type { AppTab } from '../apiTypes';

export const OWNER_TOUR_DONE_KEY = 'motopay_owner_tour_v1_done';
export const OWNER_TOUR_BANNER_DISMISSED_KEY = 'motopay_owner_tour_banner_dismissed';

export type OwnerRole = 'admin' | 'dono';

export type OwnerTourStep = {
  id: string;
  tab?: AppTab;
  tourId?: string;
  title: string;
  description: string;
  roles?: OwnerRole[];
  skipRoles?: OwnerRole[];
};

const ALL_STEPS: OwnerTourStep[] = [
  {
    id: 'welcome',
    tab: 'dashboard',
    title: 'Bem-vindo ao MotoPay',
    description:
      'Este painel centraliza frota, clientes, contratos e cobranças da sua operação. Vamos percorrer as áreas principais em poucos minutos.',
  },
  {
    id: 'nav',
    tab: 'dashboard',
    tourId: 'nav-menu',
    title: 'Menu lateral',
    description:
      'Use o menu para alternar entre visão geral, frota, clientes, contratos, financeiro, métricas e cobranças.',
  },
  {
    id: 'scope',
    tab: 'dashboard',
    tourId: 'scope-select',
    title: 'Escopo da operação',
    description:
      'Como administrador, selecione aqui qual operação deseja visualizar ou editar antes de gerenciar dados.',
    roles: ['admin'],
  },
  {
    id: 'stats',
    tab: 'dashboard',
    tourId: 'stats-grid',
    title: 'Indicadores principais',
    description:
      'Receita bruta, lucro líquido, cobranças em atraso e clientes inadimplentes aparecem aqui em tempo real.',
  },
  {
    id: 'alerts',
    tab: 'dashboard',
    tourId: 'dashboard-alerts',
    title: 'Atenção operacional',
    description:
      'Acompanhe inadimplentes e o checklist de primeiros passos. Contratos em atraso exigem ação ou promessa de pagamento.',
  },
  {
    id: 'fleet',
    tab: 'motos',
    tourId: 'fleet-add',
    title: 'Gestão de frota',
    description:
      'Cadastre motos com placa, modelo e status antes de criar contratos. Motos disponíveis podem ser vinculadas a clientes.',
  },
  {
    id: 'clients',
    tab: 'clientes',
    tourId: 'clients-table',
    title: 'Clientes e Telegram',
    description:
      'Informe CPF, telefone e Telegram ID de cada motorista. O Telegram ID é obrigatório para lembretes, Pix e confirmações automáticas.',
  },
  {
    id: 'contracts',
    tab: 'contratos',
    tourId: 'contracts-filters',
    title: 'Contratos de locação',
    description:
      'Vincule cliente e moto, defina valor recorrente e vencimento. Filtre inadimplentes ou contratos com promessa de pagamento.',
  },
  {
    id: 'charges',
    tab: 'cobrancas',
    tourId: 'charges-list',
    title: 'Cobranças Pix',
    description:
      'Veja status pendente, atrasado ou recebido. Cada cobrança mostra gateway (Asaas ou Mercado Pago) e valor atualizado com multa/juros.',
  },
  {
    id: 'finance',
    tab: 'financeiro',
    tourId: 'finance-actions',
    title: 'Financeiro',
    description:
      'Registre despesas de manutenção e receitas manuais. Isso alimenta o lucro líquido exibido no dashboard.',
  },
  {
    id: 'metrics',
    tab: 'metricas',
    tourId: 'metrics-ranking',
    title: 'Métricas por moto',
    description:
      'Compare receita, despesa, lucro e ROI de cada veículo no período selecionado para decidir onde investir ou desmobilizar.',
  },
  {
    id: 'settings',
    tab: 'ajustes',
    tourId: 'settings-billing',
    title: 'Ajustes da operação',
    description:
      'Configure multa fixa, juros diários e textos do Telegram enviados pelo bot e pelas notificações automáticas.',
  },
  {
    id: 'automation',
    tab: 'dashboard',
    title: 'Automação de cobrança',
    description:
      'O sistema envia lembrete no dia anterior (D-1), verifica no vencimento (D-0) e, após atraso, gera novo Pix diário com multa/juros via Telegram. Promessa de pagamento pausa cobranças. O score do cliente (+5 ao pagar, penalidade no atraso) só altera o tom das mensagens — não muda valores.',
  },
  {
    id: 'bot',
    tab: 'dashboard',
    title: 'Comandos do bot Telegram',
    description:
      'Seus clientes podem usar /pix (código de pagamento), /status (situação do contrato), /promessa (combinar nova data) e /ajuda. Tour concluído — explore o painel quando quiser!',
  },
];

export function getOwnerTourSteps(role: string | null | undefined): OwnerTourStep[] {
  const r = (role ?? '') as OwnerRole;
  return ALL_STEPS.filter((step) => {
    if (step.roles && !step.roles.includes(r)) return false;
    if (step.skipRoles?.includes(r)) return false;
    return true;
  });
}

export function isOwnerTourEligible(role: string | null | undefined): boolean {
  return role === 'dono' || role === 'admin';
}

function hasOwnerTourCompleted(): boolean {
  return localStorage.getItem(OWNER_TOUR_DONE_KEY) === '1';
}

export function markOwnerTourCompleted(): void {
  localStorage.setItem(OWNER_TOUR_DONE_KEY, '1');
}

export function clearOwnerTourCompleted(): void {
  localStorage.removeItem(OWNER_TOUR_DONE_KEY);
}

function hasOwnerTourBannerDismissed(): boolean {
  return localStorage.getItem(OWNER_TOUR_BANNER_DISMISSED_KEY) === '1';
}

export function dismissOwnerTourBanner(): void {
  localStorage.setItem(OWNER_TOUR_BANNER_DISMISSED_KEY, '1');
}

export function clearOwnerTourBannerDismissed(): void {
  localStorage.removeItem(OWNER_TOUR_BANNER_DISMISSED_KEY);
}

export function shouldShowOwnerTourBanner(
  activeTab: string,
  loading: boolean,
  eligible: boolean
): boolean {
  return (
    eligible &&
    activeTab === 'dashboard' &&
    !loading &&
    !hasOwnerTourCompleted() &&
    !hasOwnerTourBannerDismissed()
  );
}
