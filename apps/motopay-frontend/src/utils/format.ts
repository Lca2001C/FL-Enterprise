export function formatBrl(value: number | string | null | undefined): string {
  const n = Number(value ?? 0);
  return `R$ ${n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * Converte uma string de data em um Date no fuso LOCAL.
 *
 * `new Date("2026-06-19")` é interpretado como meia-noite UTC e, em fusos
 * negativos (ex.: America/Sao_Paulo, UTC-3), renderiza como o dia anterior
 * (18/06). Para datas no formato YYYY-MM-DD construímos a data com os
 * componentes locais, evitando esse deslocamento de um dia.
 */
export function parseLocalDate(value: string | Date): Date {
  if (value instanceof Date) return value;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
  if (m) {
    return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  }
  return new Date(value);
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return '—';
  const d = parseLocalDate(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('pt-BR');
}

/** Formata um Date como YYYY-MM-DD usando os componentes LOCAIS (sem UTC). */
export function toLocalIso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function roleLabel(tipo: string | null | undefined): string {
  switch (tipo) {
    case 'admin':
      return 'Administrador';
    case 'dono':
      return 'Dono da operação';
    default:
      return tipo ?? 'Usuário';
  }
}

export function todayIso(): string {
  // Data de HOJE no fuso local (não UTC) — evita "pular" para amanhã à noite.
  return toLocalIso(new Date());
}

export function addDaysIso(iso: string, days: number): string {
  const d = parseLocalDate(iso);
  d.setDate(d.getDate() + days);
  return toLocalIso(d);
}

export type VigenciaPreset = 'indeterminado' | '1m' | '3m' | '6m' | '1a' | 'custom';
export type VencimentoPreset = 'ciclo' | '7d' | '15d' | '30d' | 'custom';

export function contractEndFromPreset(dataInicio: string, preset: VigenciaPreset): string {
  switch (preset) {
    case 'indeterminado':
      return '';
    case '1m':
      return addDaysIso(dataInicio, 30);
    case '3m':
      return addDaysIso(dataInicio, 90);
    case '6m':
      return addDaysIso(dataInicio, 180);
    case '1a':
      return addDaysIso(dataInicio, 365);
    case 'custom':
      return '';
  }
}

export function paymentDueFromPreset(
  dataInicio: string,
  ciclo: 'semanal' | 'mensal',
  preset: VencimentoPreset
): string {
  switch (preset) {
    case 'ciclo':
      return defaultVencimento(ciclo, dataInicio);
    case '7d':
      return addDaysIso(dataInicio, 7);
    case '15d':
      return addDaysIso(dataInicio, 15);
    case '30d':
      return addDaysIso(dataInicio, 30);
    case 'custom':
      return defaultVencimento(ciclo, dataInicio);
  }
}

export function defaultVencimento(ciclo: 'semanal' | 'mensal', dataInicio: string): string {
  return addDaysIso(dataInicio, ciclo === 'semanal' ? 7 : 30);
}
