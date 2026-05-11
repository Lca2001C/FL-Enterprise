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
  valor_total: number;
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
