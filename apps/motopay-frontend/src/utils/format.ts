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

function addDaysIso(iso: string, days: number): string {
  const d = new Date(iso + 'T12:00:00');
  d.setDate(d.getDate() + days);
  return d.toISOString().split('T')[0];
}

export function defaultVencimento(ciclo: 'semanal' | 'mensal', dataInicio: string): string {
  return addDaysIso(dataInicio, ciclo === 'semanal' ? 7 : 30);
}

export function exportCsv(filename: string, headers: string[], rows: string[][]): void {
  const escape = (cell: string) => `"${cell.replace(/"/g, '""')}"`;
  const lines = [headers.map(escape).join(','), ...rows.map((r) => r.map(escape).join(','))];
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
