export function formatBrl(value: number | string | null | undefined): string {
  const n = Number(value ?? 0);
  return `R$ ${n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return '—';
  const d = typeof value === 'string' ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('pt-BR');
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
  return new Date().toISOString().split('T')[0];
}

export function addDaysIso(iso: string, days: number): string {
  const d = new Date(iso + 'T12:00:00');
  d.setDate(d.getDate() + days);
  return d.toISOString().split('T')[0];
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
