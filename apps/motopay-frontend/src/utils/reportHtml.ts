/**
 * Builders de HTML para relatórios impressos (Extrato financeiro e Relatório
 * de manutenções). Geram um documento COMPLETO e auto-contido, renderizado em
 * um iframe isolado por printHtml.ts — nada do CSS do app vaza para o PDF.
 *
 * Por que não window.print() na própria página: o truque de esconder o app
 * com `visibility: hidden` + posicionar o extrato com `position: absolute`
 * quebra a paginação (páginas 2+ saem com texto sobreposto e cabeçalhos
 * duplicados), exatamente o defeito reportado no PDF em produção.
 */
import { formatBrl, formatDate } from './format';

export function escapeHtml(value: string | null | undefined): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const REPORT_CSS = `
  * { box-sizing: border-box; }
  @page { size: A4; margin: 14mm 12mm; }
  html, body {
    margin: 0;
    padding: 0;
    background: #fff;
    color: #0f172a;
    font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
    font-size: 12px;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  h1 { font-size: 20px; margin: 0 0 2px; }
  .subtitle { color: #64748b; margin: 0 0 16px; font-size: 11px; }
  .cards { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .card {
    flex: 1 1 120px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 12px;
    background: #f8fafc;
    page-break-inside: avoid;
    break-inside: avoid;
  }
  .card .label {
    display: block;
    font-size: 9px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #64748b;
    margin-bottom: 4px;
  }
  .card .value { font-size: 14px; font-weight: 700; }
  .card.receita .value { color: #047857; }
  .card.despesa .value { color: #b91c1c; }
  .card.saldo .value { color: #92600a; }
  table { width: 100%; border-collapse: collapse; }
  thead { display: table-header-group; }
  tr { page-break-inside: avoid; break-inside: avoid; }
  th {
    text-align: left;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: #475569;
    border-bottom: 2px solid #94a3b8;
    padding: 6px 8px;
    background: #f1f5f9;
  }
  td {
    padding: 6px 8px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
    word-break: break-word;
  }
  td.num { white-space: nowrap; font-weight: 600; }
  .badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.03em;
  }
  .badge.receita { background: #d1fae5; color: #047857; }
  .badge.despesa { background: #fee2e2; color: #b91c1c; }
  .badge.preventiva { background: #dbeafe; color: #1d4ed8; }
  .badge.corretiva { background: #ffedd5; color: #c2410c; }
  .section-title {
    font-size: 13px;
    font-weight: 700;
    margin: 18px 0 8px;
    page-break-after: avoid;
    break-after: avoid;
  }
  .muted { color: #64748b; }
`;

function documentShell(title: string, body: string): string {
  return [
    '<!DOCTYPE html>',
    '<html lang="pt-BR">',
    '<head>',
    '<meta charset="utf-8" />',
    `<title>${escapeHtml(title)}</title>`,
    `<style>${REPORT_CSS}</style>`,
    '</head>',
    `<body>${body}</body>`,
    '</html>',
  ].join('');
}

export type StatementRow = {
  data: string;
  descricao: string;
  tipo: string;
  valor: number | string;
  moto: string | null;
};

export type StatementTotals = {
  receitas: number;
  despesas: number;
  saldo: number;
  manutencao: number;
};

export function buildFinanceStatementHtml(
  rows: StatementRow[],
  totals: StatementTotals,
  generatedAt: string
): string {
  const linhas = rows
    .map(
      (r) => `<tr>
        <td class="num" style="font-weight:400">${escapeHtml(formatDate(r.data))}</td>
        <td>${escapeHtml(r.descricao)}</td>
        <td><span class="badge ${r.tipo === 'receita' ? 'receita' : 'despesa'}">${
          r.tipo === 'receita' ? 'RECEITA' : 'DESPESA'
        }</span></td>
        <td class="num">${escapeHtml(formatBrl(r.valor))}</td>
        <td>${escapeHtml(r.moto || '—')}</td>
      </tr>`
    )
    .join('');

  const body = `
    <h1>MotoPay — Extrato financeiro</h1>
    <p class="subtitle">Gerado em ${escapeHtml(formatDate(generatedAt))} · ${rows.length} lançamento(s)</p>
    <div class="cards">
      <div class="card receita"><span class="label">Receitas</span><span class="value">${escapeHtml(formatBrl(totals.receitas))}</span></div>
      <div class="card despesa"><span class="label">Despesas</span><span class="value">${escapeHtml(formatBrl(totals.despesas))}</span></div>
      <div class="card saldo"><span class="label">Saldo</span><span class="value">${escapeHtml(formatBrl(totals.saldo))}</span></div>
      <div class="card despesa"><span class="label">Total manutenção</span><span class="value">${escapeHtml(formatBrl(totals.manutencao))}</span></div>
    </div>
    <table>
      <thead>
        <tr><th>Data</th><th>Descrição</th><th>Tipo</th><th>Valor</th><th>Moto</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
  return documentShell('MotoPay — Extrato financeiro', body);
}

export type ManutencaoReportRow = {
  moto: string;
  tipo: string;
  descricao: string;
  causa: string;
  valor: number | string;
  data: string;
  km: number | null;
};

export type ManutencaoReportTotals = {
  totalGeral: number;
  quantidade: number;
  totalPreventiva: number;
  totalCorretiva: number;
  porMoto: Array<{ moto: string; total: number; quantidade: number }>;
};

export const MANUTENCAO_TIPO_LABELS: Record<string, string> = {
  preventiva: 'Preventiva',
  corretiva: 'Corretiva',
};

export const MANUTENCAO_CAUSA_LABELS: Record<string, string> = {
  prevencao: 'Prevenção',
  desgaste: 'Desgaste',
  mau_uso: 'Mau uso',
  outro: 'Outro',
};

export function formatKm(km: number | null | undefined): string {
  if (km == null) return '—';
  return `${km.toLocaleString('pt-BR')} km`;
}

export function buildManutencaoReportHtml(
  rows: ManutencaoReportRow[],
  totals: ManutencaoReportTotals,
  generatedAt: string
): string {
  const linhas = rows
    .map(
      (r) => `<tr>
        <td>${escapeHtml(r.moto)}</td>
        <td><span class="badge ${r.tipo === 'preventiva' ? 'preventiva' : 'corretiva'}">${escapeHtml(
          MANUTENCAO_TIPO_LABELS[r.tipo] ?? r.tipo
        )}</span></td>
        <td>${escapeHtml(r.descricao)}</td>
        <td>${escapeHtml(MANUTENCAO_CAUSA_LABELS[r.causa] ?? r.causa)}</td>
        <td class="num">${escapeHtml(formatBrl(r.valor))}</td>
        <td class="num" style="font-weight:400">${escapeHtml(formatDate(r.data))}</td>
        <td class="num" style="font-weight:400">${escapeHtml(formatKm(r.km))}</td>
      </tr>`
    )
    .join('');

  const porMoto = totals.porMoto
    .map(
      (m) => `<tr>
        <td>${escapeHtml(m.moto)}</td>
        <td class="num" style="font-weight:400">${m.quantidade}</td>
        <td class="num">${escapeHtml(formatBrl(m.total))}</td>
      </tr>`
    )
    .join('');

  const body = `
    <h1>Relatório de Manutenções</h1>
    <p class="subtitle">Gerado em ${escapeHtml(formatDate(generatedAt))} · ${totals.quantidade} manutenção(ões)</p>
    <div class="cards">
      <div class="card despesa"><span class="label">Total gasto</span><span class="value">${escapeHtml(formatBrl(totals.totalGeral))}</span></div>
      <div class="card"><span class="label">Preventivas</span><span class="value">${escapeHtml(formatBrl(totals.totalPreventiva))}</span></div>
      <div class="card"><span class="label">Corretivas</span><span class="value">${escapeHtml(formatBrl(totals.totalCorretiva))}</span></div>
      <div class="card"><span class="label">Registros</span><span class="value">${totals.quantidade}</span></div>
    </div>
    ${
      porMoto
        ? `<p class="section-title">Total por moto</p>
    <table>
      <thead><tr><th>Veículo</th><th>Serviços</th><th>Total</th></tr></thead>
      <tbody>${porMoto}</tbody>
    </table>`
        : ''
    }
    <p class="section-title">Serviços de manutenção</p>
    <table>
      <thead>
        <tr><th>Veículo</th><th>Tipo</th><th>Manutenção</th><th>Causa</th><th>Valor</th><th>Data do serviço</th><th>Km</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
  return documentShell('Relatório de Manutenções', body);
}
