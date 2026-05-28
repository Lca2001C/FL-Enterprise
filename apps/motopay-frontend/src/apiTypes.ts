/** Formas aproximadas do JSON da API (decimais viram number). */

export type Paginated<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type UserOut = {
  id: number;
  email: string;
  tipo: 'admin' | 'dono';
  operacao_id: number | null;
};

export type UserAdminOut = UserOut & {
  created_at: string;
  operacao_nome: string | null;
};

export type OperacaoOut = {
  id: number;
  nome: string;
  created_at: string;
  multa_fixa_percentual: number;
  juros_diario_percentual: number;
  telegram_templates: Record<string, string>;
};

export type MotoOut = {
  id: number;
  operacao_id: number;
  placa: string;
  modelo: string;
  status: string;
  km: number;
  tem_imagem?: boolean;
  cliente_nome?: string | null;
};

export type ClienteOut = {
  id: number;
  operacao_id: number;
  nome: string;
  cpf: string;
  telefone: string;
  telegram_id: string | null;
  score: number;
  moto_placa?: string | null;
  moto_modelo?: string | null;
};

export type ContratoOut = {
  id: number;
  operacao_id: number;
  cliente_id: number;
  moto_id: number;
  valor_recorrente: number;
  ciclo: string;
  status: string;
  data_inicio: string;
  data_fim_vigencia: string | null;
  proximo_vencimento: string;
  nivel_escalonamento_cobranca: number;
  dias_atraso_acumulado: number;
  inadimplente: boolean;
  promessa_pagamento_em: string | null;
  promessa_notas: string | null;
  mercadopago_subscription_id: string | null;
};

export type TelegramBotMenuButton = {
  label: string;
  command: string;
  response?: string | null;
};

export const BOT_MENU_BUILTIN_COMMANDS = [
  { value: 'menu', label: 'Menu principal (/menu)' },
  { value: 'status', label: 'Status' },
  { value: 'pix', label: 'Pix' },
  { value: 'ajuda', label: 'Ajuda' },
  { value: 'promessa', label: 'Promessa (uso)' },
] as const;

export function isBuiltinBotMenuCommand(command: string): boolean {
  return BOT_MENU_BUILTIN_COMMANDS.some((opt) => opt.value === command);
}

export type OperacaoConfig = {
  nome: string;
  multa_fixa_percentual: number;
  juros_diario_percentual: number;
  telegram_templates: Record<string, string>;
  telegram_custom_messages: TelegramCustomMessage[];
  telegram_bot_menu_buttons: TelegramBotMenuButton[];
  telegram_owner_notify_id: string | null;
  telegram_owner_notify_enabled: boolean;
  mercadopago_access_token?: string;
};

export type TelegramCustomMessage = {
  id: string;
  label: string;
  trigger: string;
  body: string;
  enabled: boolean;
  replace_default: boolean;
};

export type CustomMessageTriggerMeta = {
  trigger: string;
  label: string;
  description: string;
  placeholders: string[];
};

export type TelegramTemplateMeta = {
  key: string;
  label: string;
  description: string;
  placeholders: string[];
  group: 'notificacoes' | 'bot';
  default: string;
};

export type TelegramTemplatePreviewOut = {
  text: string;
};

export type FinanceiroOut = {
  id: number;
  operacao_id: number;
  tipo: string;
  valor: number;
  descricao: string;
  data: string;
  moto_id: number | null;
  contrato_id: number | null;
};

export type CobrancaOut = {
  id: number;
  operacao_id: number;
  contrato_id: number;
  valor: number;
  vencimento: string;
  mercadopago_payment_id: string | null;
  payment_gateway: 'mercadopago';
  pix_copia_cola: string | null;
  status: string;
  dias_atraso: number;
  multa: number;
  juros: number;
  valor_total: number;
};

export type AnalyticsSummary = {
  receita_total: number;
  despesa_total: number;
  lucro_liquido: number;
  motos_ativas: number;
  clientes_inadimplentes: number;
  total_cobrancas: number;
  cobrancas_pendentes: number;
  cobrancas_atrasadas: number;
};

export type RecentActivityItem = {
  id: number;
  tipo: string;
  descricao: string;
  data: string;
  valor: number;
};

export type MotoAnalyticsRow = {
  moto_id: number;
  placa: string;
  modelo: string;
  receita: number;
  despesa: number;
  lucro_liquido: number;
  roi: number | null;
  prejuizo: boolean;
};

export type AppTab =
  | 'dashboard'
  | 'motos'
  | 'clientes'
  | 'contratos'
  | 'financeiro'
  | 'metricas'
  | 'cobrancas'
  | 'ajustes'
  | 'admin-operacoes'
  | 'admin-usuarios'
  | 'admin-ops'
  | 'conta';

export type ContractsFilter = 'todos' | 'ativos' | 'inadimplentes' | 'com_promessa';

export type CelerySummary = {
  workers_online: number;
  active_tasks: number;
  queue_backlog: Record<string, number>;
  queue_active: Record<string, number>;
  dlq_size: number;
  stuck_tasks: Array<{
    worker: string;
    task_id: string;
    task_name: string;
    seconds_running: number;
  }>;
  bot_online: boolean;
  workers: Array<{
    name: string;
    pool?: string;
    concurrency?: number;
    active_tasks: number;
  }>;
};

export const PAGE_SIZE = 50;
