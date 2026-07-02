import { describe, expect, it } from 'vitest';
import {
  buildFinanceStatementHtml,
  buildManutencaoReportHtml,
  escapeHtml,
  formatKm,
} from './reportHtml';

describe('escapeHtml', () => {
  it('escapa caracteres perigosos', () => {
    expect(escapeHtml('<script>alert("x")</script>')).toBe(
      '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;'
    );
    expect(escapeHtml("d'agua & cia")).toBe('d&#39;agua &amp; cia');
  });

  it('trata null/undefined como vazio', () => {
    expect(escapeHtml(null)).toBe('');
    expect(escapeHtml(undefined)).toBe('');
  });
});

describe('formatKm', () => {
  it('formata km com separador pt-BR', () => {
    expect(formatKm(24215)).toBe('24.215 km');
  });
  it('retorna travessão sem km', () => {
    expect(formatKm(null)).toBe('—');
    expect(formatKm(undefined)).toBe('—');
  });
});

describe('buildFinanceStatementHtml', () => {
  const rows = [
    { data: '2026-07-02', descricao: 'aluguel', tipo: 'receita', valor: 500, moto: 'TYR7E25 — CG 160' },
    { data: '2026-07-01', descricao: 'financiamento', tipo: 'despesa', valor: 635.37, moto: null },
  ];
  const totals = { receitas: 500, despesas: 635.37, saldo: -135.37, manutencao: 0 };

  it('gera documento completo com título e cards', () => {
    const html = buildFinanceStatementHtml(rows, totals, '2026-07-02');
    expect(html).toContain('<!DOCTYPE html>');
    expect(html).toContain('MotoPay — Extrato financeiro');
    expect(html).toContain('Gerado em 02/07/2026');
    expect(html).toContain('Total manutenção');
    expect(html).toContain('500,00');
    expect(html).toContain('635,37');
  });

  it('formata datas em DD/MM/AAAA e mostra moto ou travessão', () => {
    const html = buildFinanceStatementHtml(rows, totals, '2026-07-02');
    expect(html).toContain('02/07/2026');
    expect(html).toContain('01/07/2026');
    expect(html).toContain('TYR7E25 — CG 160');
    expect(html).toContain('<td>—</td>');
  });

  it('repete o cabeçalho por página via thead (table-header-group)', () => {
    const html = buildFinanceStatementHtml(rows, totals, '2026-07-02');
    expect(html).toContain('thead { display: table-header-group; }');
    expect(html).toContain('page-break-inside: avoid');
    expect((html.match(/<thead>/g) || []).length).toBe(1);
  });

  it('escapa HTML vindo de descrições', () => {
    const html = buildFinanceStatementHtml(
      [{ data: '2026-01-01', descricao: '<img onerror=1>', tipo: 'despesa', valor: 1, moto: null }],
      totals,
      '2026-07-02'
    );
    expect(html).not.toContain('<img onerror=1>');
    expect(html).toContain('&lt;img onerror=1&gt;');
  });

  it('suporta muitas linhas sem duplicar estrutura', () => {
    const many = Array.from({ length: 500 }, (_, i) => ({
      data: '2026-06-15',
      descricao: `lançamento ${i}`,
      tipo: i % 2 ? 'receita' : 'despesa',
      valor: 10,
      moto: null,
    }));
    const html = buildFinanceStatementHtml(many, totals, '2026-07-02');
    expect((html.match(/<tr>/g) || []).length).toBe(501); // 500 linhas + thead
    expect((html.match(/<table>/g) || []).length).toBe(1);
  });
});

describe('buildManutencaoReportHtml', () => {
  const rows = [
    {
      moto: 'SYH5J66 — CG 160',
      tipo: 'preventiva',
      descricao: 'Trocar óleo de motor',
      causa: 'prevencao',
      valor: 40,
      data: '2026-06-15',
      km: 24215,
    },
    {
      moto: 'SYH5J66 — CG 160',
      tipo: 'corretiva',
      descricao: 'Pneu traseiro',
      causa: 'desgaste',
      valor: 223,
      data: '2026-01-22',
      km: null,
    },
  ];
  const totals = {
    totalGeral: 263,
    quantidade: 2,
    totalPreventiva: 40,
    totalCorretiva: 223,
    porMoto: [{ moto: 'SYH5J66 — CG 160', total: 263, quantidade: 2 }],
  };

  it('gera relatório com título, totais e tabela', () => {
    const html = buildManutencaoReportHtml(rows, totals, '2026-07-02');
    expect(html).toContain('Relatório de Manutenções');
    expect(html).toContain('Gerado em 02/07/2026');
    expect(html).toContain('Total por moto');
    expect(html).toContain('Preventiva');
    expect(html).toContain('Corretiva');
    expect(html).toContain('Desgaste');
    expect(html).toContain('24.215 km');
    expect(html).toContain('263,00');
  });

  it('traduz causa mau_uso e mostra travessão sem km', () => {
    const html = buildManutencaoReportHtml(
      [{ ...rows[0], causa: 'mau_uso', km: null }],
      totals,
      '2026-07-02'
    );
    expect(html).toContain('Mau uso');
    expect(html).toContain('—');
  });
});
