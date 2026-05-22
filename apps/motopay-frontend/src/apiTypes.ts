/** Formas aproximadas do JSON da API (decimais viram number). */

export type MotoOut = {
  id: number;
  operacao_id: number;
  placa: string;
  modelo: string;
  status: string;
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
  proximo_vencimento: string;
  nivel_escalonamento_cobranca: number;
  dias_atraso_acumulado: number;
  inadimplente: boolean;
  promessa_pagamento_em: string | null;
  promessa_notas: string | null;
  asaas_subscription_id: string | null;
};

export type OperacaoConfig = {
  nome: string;
  multa_fixa_percentual: number;
  juros_diario_percentual: number;
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
  asaas_payment_id: string | null;
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
  | 'ajustes';

export type ContractsFilter = 'todos' | 'ativos' | 'inadimplentes';
