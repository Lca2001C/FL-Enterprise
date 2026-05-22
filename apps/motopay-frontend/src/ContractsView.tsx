import { useState, useEffect, useMemo, useCallback, type FormEvent } from 'react';
import {
  Plus,
  FileText,
  XCircle,
  Copy,
  QrCode,
  Wallet,
  Check,
  Filter,
  X,
} from 'lucide-react';
import { useAuth } from './AuthContext';
import type { ClienteOut, CobrancaOut, ContratoOut, MotoOut, Paginated } from './apiTypes';
import type { ContractsFilter } from './apiTypes';
import { PAGE_SIZE } from './apiTypes';
import { defaultVencimento, formatBrl, formatDate, todayIso } from './utils/format';
import { parseApiError } from './utils/apiError';
import { fetchAllPaginated, offsetAfterDelete } from './utils/fetchPaginated';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';

type FilterTab = ContractsFilter;

const ContractsView = () => {
  const {
    api,
    contractsFilter,
    setContractsFilter,
    contractsClienteId,
    clearContractsClienteFilter,
  } = useAuth();
  const [contratos, setContratos] = useState<ContratoOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [clientes, setClientes] = useState<ClienteOut[]>([]);
  const [motos, setMotos] = useState<MotoOut[]>([]);
  const [cobrancas, setCobrancas] = useState<CobrancaOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<FilterTab>(contractsFilter);
  const [showModal, setShowModal] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const [form, setForm] = useState({
    cliente_id: '',
    moto_id: '',
    valor_recorrente: '',
    ciclo: 'mensal' as 'semanal' | 'mensal',
    data_inicio: todayIso(),
    proximo_vencimento: defaultVencimento('mensal', todayIso()),
    gerar_pix: true,
  });

  const clienteMap = useMemo(
    () => Object.fromEntries(clientes.map((c) => [c.id, c])),
    [clientes]
  );
  const motoMap = useMemo(() => Object.fromEntries(motos.map((m) => [m.id, m])), [motos]);

  const cobrancaByContrato = useMemo(() => {
    const map: Record<number, CobrancaOut> = {};
    for (const c of cobrancas) {
      if (c.status === 'pendente' || c.status === 'atrasado') {
        if (!map[c.contrato_id] || map[c.contrato_id].id < c.id) {
          map[c.contrato_id] = c;
        }
      }
    }
    return map;
  }, [cobrancas]);

  const motosDisponiveis = motos.filter((m) => m.status === 'disponivel');

  const buildContratoParams = useCallback(
    (pageOffset: number): Record<string, unknown> => {
      const params: Record<string, unknown> = { limit: PAGE_SIZE, offset: pageOffset };
      if (filter === 'ativos') params.status = 'ativo';
      else if (filter === 'inadimplentes') params.inadimplente = true;
      else if (filter === 'com_promessa') params.com_promessa = true;
      if (contractsClienteId != null) params.cliente_id = contractsClienteId;
      return params;
    },
    [filter, contractsClienteId]
  );

  const fetchContratos = useCallback(
    async (pageOffset = 0) => {
      setLoading(true);
      setError('');
      try {
        const r = await api.get<Paginated<ContratoOut>>('/api/v1/contratos', {
          params: buildContratoParams(pageOffset),
        });
        setContratos(r.data.items);
        setTotal(r.data.total);
        setOffset(pageOffset);
      } catch (e) {
        setError(parseApiError(e, 'Erro ao carregar contratos'));
      } finally {
        setLoading(false);
      }
    },
    [api, buildContratoParams]
  );

  const fetchMeta = useCallback(async () => {
    try {
      const [clItems, moItems, cobItems] = await Promise.all([
        fetchAllPaginated<ClienteOut>(api, '/api/v1/clientes'),
        fetchAllPaginated<MotoOut>(api, '/api/v1/motos'),
        fetchAllPaginated<CobrancaOut>(api, '/api/v1/cobrancas'),
      ]);
      setClientes(clItems);
      setMotos(moItems);
      setCobrancas(cobItems);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar dados auxiliares'));
    }
  }, [api]);

  useEffect(() => {
    void fetchContratos(0);
  }, [fetchContratos]);

  useEffect(() => {
    void fetchMeta();
  }, [fetchMeta]);

  useEffect(() => {
    setFilter(contractsFilter);
  }, [contractsFilter]);

  const handleFilterChange = (f: FilterTab) => {
    setFilter(f);
    setContractsFilter(f);
  };

  const handleCicloChange = (ciclo: 'semanal' | 'mensal') => {
    setForm((prev) => ({
      ...prev,
      ciclo,
      proximo_vencimento: defaultVencimento(ciclo, prev.data_inicio),
    }));
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const body = {
        cliente_id: parseInt(form.cliente_id, 10),
        moto_id: parseInt(form.moto_id, 10),
        valor_recorrente: parseFloat(form.valor_recorrente),
        ciclo: form.ciclo,
        status: 'ativo',
        data_inicio: form.data_inicio,
        proximo_vencimento: form.proximo_vencimento,
      };
      const res = await api.post<ContratoOut>('/api/v1/contratos', body);
      if (form.gerar_pix) {
        await api.post('/api/v1/cobrancas/pix', { contrato_id: res.data.id });
      }
      setShowModal(false);
      setForm({
        cliente_id: '',
        moto_id: '',
        valor_recorrente: '',
        ciclo: 'mensal',
        data_inicio: todayIso(),
        proximo_vencimento: defaultVencimento('mensal', todayIso()),
        gerar_pix: true,
      });
      await fetchContratos(offset);
      await fetchMeta();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao criar contrato'));
    }
  };

  const handleEncerrar = async (id: number) => {
    if (!confirm('Encerrar este contrato? A moto não será liberada automaticamente.')) return;
    setActionLoading(id);
    setError('');
    const wasLast = contratos.length === 1;
    try {
      await api.patch(`/api/v1/contratos/${id}`, { status: 'finalizado' });
      await fetchContratos(offsetAfterDelete(offset, PAGE_SIZE, wasLast));
      await fetchMeta();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao encerrar contrato'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleGerarPix = async (contratoId: number) => {
    setActionLoading(contratoId);
    setError('');
    try {
      await api.post('/api/v1/cobrancas/pix', { contrato_id: contratoId });
      await fetchContratos(offset);
      await fetchMeta();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao gerar Pix'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleAssinaturaAsaas = async (contratoId: number) => {
    setActionLoading(contratoId);
    setError('');
    try {
      await api.post('/api/v1/cobrancas/assinatura-asaas', { contrato_id: contratoId });
      await fetchContratos(offset);
      await fetchMeta();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao criar assinatura Asaas'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleAssinaturaMp = async (contratoId: number) => {
    setActionLoading(contratoId);
    setError('');
    try {
      await api.post('/api/v1/cobrancas/assinatura-mercadopago', { contrato_id: contratoId });
      await fetchContratos(offset);
      await fetchMeta();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao criar assinatura Mercado Pago'));
    } finally {
      setActionLoading(null);
    }
  };

  const copyPix = async (contratoId: number, pix: string) => {
    await navigator.clipboard.writeText(pix);
    setCopiedId(contratoId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Contratos</h2>
          <p className="text-muted">{total} locações cadastradas</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={20} /> Nova locação
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <AdminScopeBanner />

      {contractsClienteId != null && (
        <div className="cliente-filter-chip glass">
          <span>Filtrando cliente #{contractsClienteId}</span>
          <button
            type="button"
            className="icon-btn"
            title="Limpar filtro de cliente"
            onClick={clearContractsClienteFilter}
          >
            <X size={14} />
          </button>
        </div>
      )}

      <div className="filter-tabs glass" data-tour="contracts-filters">
        <Filter size={16} />
        {(['todos', 'ativos', 'inadimplentes', 'com_promessa'] as FilterTab[]).map((f) => (
          <button
            key={f}
            type="button"
            className={`tab ${filter === f ? 'active' : ''}`}
            onClick={() => handleFilterChange(f)}
          >
            {f === 'todos'
              ? 'Todos'
              : f === 'ativos'
                ? 'Ativos'
                : f === 'inadimplentes'
                  ? 'Inadimplentes'
                  : 'Com promessa'}
          </button>
        ))}
      </div>

      <div className="glass table-container">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando contratos...</p>
        ) : contratos.length === 0 ? (
          <EmptyState
            icon={<FileText size={40} />}
            title="Nenhum contrato encontrado"
            description={
              filter === 'inadimplentes'
                ? 'Não há contratos inadimplentes no momento.'
                : 'Cadastre uma nova locação para vincular cliente e moto.'
            }
            action={
              filter !== 'inadimplentes' ? (
                <button className="btn-primary" onClick={() => setShowModal(true)}>
                  <Plus size={18} /> Nova locação
                </button>
              ) : undefined
            }
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Moto</th>
                <th>Valor</th>
                <th>Ciclo</th>
                <th>Próx. vencimento</th>
                <th>Promessa</th>
                <th>Assinatura</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {contratos.map((ct) => {
                const cl = clienteMap[ct.cliente_id];
                const mo = motoMap[ct.moto_id];
                const cob = cobrancaByContrato[ct.id];
                const busy = actionLoading === ct.id;
                return (
                  <tr key={ct.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{cl?.nome ?? `#${ct.cliente_id}`}</div>
                      {ct.inadimplente && (
                        <span className="badge-danger">
                          {ct.dias_atraso_acumulado} dia(s) atraso
                        </span>
                      )}
                    </td>
                    <td>
                      <div>{mo?.placa ?? `#${ct.moto_id}`}</div>
                      <div className="text-muted" style={{ fontSize: '0.8rem' }}>
                        {mo?.modelo ?? '—'}
                      </div>
                    </td>
                    <td>{formatBrl(ct.valor_recorrente)}</td>
                    <td>{ct.ciclo}</td>
                    <td>{formatDate(ct.proximo_vencimento)}</td>
                    <td>
                      {ct.promessa_pagamento_em ? (
                        <div style={{ fontSize: '0.8rem' }}>
                          <div>{formatDate(ct.promessa_pagamento_em)}</div>
                          {ct.promessa_notas && (
                            <div className="text-muted">{ct.promessa_notas}</div>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td>
                      <div className="sub-badges">
                        {ct.asaas_subscription_id && (
                          <span className="sub-badge asaas">Asaas</span>
                        )}
                        {ct.mercadopago_subscription_id && (
                          <span className="sub-badge mp">MP</span>
                        )}
                        {!ct.asaas_subscription_id && !ct.mercadopago_subscription_id && (
                          <span className="text-muted">—</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`status-badge ${ct.status}`}>{ct.status.toUpperCase()}</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="actions">
                        {cob?.pix_copia_cola && (
                          <button
                            type="button"
                            className="action-btn-pix"
                            disabled={busy}
                            onClick={() => void copyPix(ct.id, cob.pix_copia_cola!)}
                          >
                            {copiedId === ct.id ? <Check size={14} /> : <Copy size={14} />}
                            {copiedId === ct.id ? 'Copiado' : 'Pix'}
                          </button>
                        )}
                        {ct.status === 'ativo' && (
                          <>
                            <button
                              type="button"
                              className="icon-btn"
                              title="Gerar cobrança Pix para este contrato"
                              disabled={busy}
                              onClick={() => void handleGerarPix(ct.id)}
                            >
                              <QrCode size={16} />
                            </button>
                            <button
                              type="button"
                              className="icon-btn"
                              title="Criar assinatura recorrente no Asaas"
                              disabled={busy}
                              onClick={() => void handleAssinaturaAsaas(ct.id)}
                            >
                              <FileText size={16} />
                            </button>
                            <button
                              type="button"
                              className="icon-btn"
                              title="Criar assinatura recorrente no Mercado Pago"
                              disabled={busy}
                              onClick={() => void handleAssinaturaMp(ct.id)}
                            >
                              <Wallet size={16} />
                            </button>
                            <button
                              type="button"
                              className="icon-btn danger"
                              title="Encerrar contrato de locação"
                              disabled={busy}
                              onClick={() => void handleEncerrar(ct.id)}
                            >
                              <XCircle size={16} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {total > PAGE_SIZE && (
        <div className="pagination glass">
          <button
            type="button"
            className="btn-secondary"
            disabled={offset === 0 || loading}
            onClick={() => void fetchContratos(Math.max(0, offset - PAGE_SIZE))}
          >
            Anterior
          </button>
          <span className="text-muted">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
          </span>
          <button
            type="button"
            className="btn-secondary"
            disabled={offset + PAGE_SIZE >= total || loading}
            onClick={() => void fetchContratos(offset + PAGE_SIZE)}
          >
            Próxima
          </button>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>Nova locação</h3>
            <form onSubmit={(e) => void handleCreate(e)}>
              <div className="input-group">
                <label className="input-label">Cliente</label>
                <select
                  className="input-field"
                  value={form.cliente_id}
                  onChange={(e) => setForm({ ...form, cliente_id: e.target.value })}
                  required
                >
                  <option value="">Selecione...</option>
                  {clientes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nome} — {c.cpf}
                    </option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Moto disponível</label>
                <select
                  className="input-field"
                  value={form.moto_id}
                  onChange={(e) => setForm({ ...form, moto_id: e.target.value })}
                  required
                >
                  <option value="">Selecione...</option>
                  {motosDisponiveis.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.placa} — {m.modelo}
                    </option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Valor recorrente (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  className="input-field"
                  value={form.valor_recorrente}
                  onChange={(e) => setForm({ ...form, valor_recorrente: e.target.value })}
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Ciclo</label>
                <select
                  className="input-field"
                  value={form.ciclo}
                  onChange={(e) =>
                    handleCicloChange(e.target.value as 'semanal' | 'mensal')
                  }
                >
                  <option value="mensal">Mensal</option>
                  <option value="semanal">Semanal</option>
                </select>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="input-group">
                  <label className="input-label">Início</label>
                  <input
                    type="date"
                    className="input-field"
                    value={form.data_inicio}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        data_inicio: e.target.value,
                        proximo_vencimento: defaultVencimento(form.ciclo, e.target.value),
                      })
                    }
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Próximo vencimento</label>
                  <input
                    type="date"
                    className="input-field"
                    value={form.proximo_vencimento}
                    onChange={(e) => setForm({ ...form, proximo_vencimento: e.target.value })}
                    required
                  />
                </div>
              </div>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={form.gerar_pix}
                  onChange={(e) => setForm({ ...form, gerar_pix: e.target.checked })}
                />
                Gerar Pix após criar
              </label>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Criar locação
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style jsx>{`
        .view-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          flex-wrap: wrap;
          gap: 16px;
        }
        .filter-tabs {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          margin-bottom: 20px;
          border-radius: 12px;
          flex-wrap: wrap;
        }
        .cliente-filter-chip {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 8px 14px;
          margin-bottom: 16px;
          border-radius: 999px;
          font-size: 0.85rem;
          color: var(--primary);
        }
        .tab {
          background: none;
          border: 1px solid var(--glass-border);
          color: var(--text-muted);
          padding: 6px 14px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.85rem;
        }
        .tab.active {
          background: var(--primary-glow);
          color: var(--primary);
          border-color: var(--primary);
        }
        .table-container {
          overflow-x: auto;
        }
        .custom-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 800px;
        }
        .custom-table th {
          text-align: left;
          padding: 15px 20px;
          color: var(--text-muted);
          font-size: 0.85rem;
          border-bottom: 1px solid var(--glass-border);
        }
        .custom-table td {
          padding: 15px 20px;
          border-bottom: 1px solid var(--glass-border);
          font-size: 0.9rem;
        }
        .status-badge {
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.7rem;
          font-weight: 700;
        }
        .status-badge.ativo {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent);
        }
        .status-badge.finalizado,
        .status-badge.cancelado {
          background: rgba(148, 163, 184, 0.1);
          color: var(--text-muted);
        }
        .badge-danger {
          display: inline-block;
          margin-top: 4px;
          font-size: 0.7rem;
          color: var(--danger);
          font-weight: 600;
        }
        .sub-badges {
          display: flex;
          gap: 4px;
          flex-wrap: wrap;
        }
        .sub-badge {
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 0.7rem;
          font-weight: 700;
        }
        .sub-badge.asaas {
          background: rgba(99, 102, 241, 0.1);
          color: var(--primary);
        }
        .sub-badge.mp {
          background: rgba(245, 158, 11, 0.1);
          color: var(--warning);
        }
        .actions {
          display: flex;
          justify-content: flex-end;
          gap: 4px;
          flex-wrap: wrap;
        }
        .action-btn-pix {
          background: var(--primary-glow);
          color: var(--primary);
          border: 1px solid var(--primary);
          padding: 4px 10px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.75rem;
          font-weight: 600;
          display: inline-flex;
          align-items: center;
          gap: 5px;
        }
        .icon-btn {
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 5px;
        }
        .icon-btn:hover {
          color: var(--primary);
        }
        .icon-btn.danger:hover {
          color: var(--danger);
        }
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.8);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          backdrop-filter: blur(4px);
          padding: 16px;
        }
        .modal-content {
          width: 100%;
          max-width: 480px;
          padding: 30px;
          max-height: 90vh;
          overflow-y: auto;
        }
        .modal-actions {
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          margin-top: 20px;
        }
        .btn-secondary {
          background: var(--secondary);
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 8px;
          cursor: pointer;
        }
        .pagination {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          margin-top: 16px;
          border-radius: 12px;
        }
        .checkbox-row {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 12px;
          font-size: 0.9rem;
          cursor: pointer;
        }
      `}</style>
    </div>
  );
};

export default ContractsView;
