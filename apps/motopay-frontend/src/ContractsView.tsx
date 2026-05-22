import { useState, useEffect, useMemo, type FormEvent } from 'react';
import {
  Plus,
  FileText,
  XCircle,
  Copy,
  CreditCard,
  Check,
  Filter,
} from 'lucide-react';
import { useAuth } from './AuthContext';
import type { ClienteOut, CobrancaOut, ContratoOut, MotoOut } from './apiTypes';
import { defaultVencimento, formatBrl, formatDate, todayIso } from './utils/format';
import { parseApiError } from './utils/apiError';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';

type FilterTab = 'todos' | 'ativos' | 'inadimplentes';

const ContractsView = () => {
  const { api, contractsFilter, setContractsFilter } = useAuth();
  const [contratos, setContratos] = useState<ContratoOut[]>([]);
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

  const filtered = useMemo(() => {
    if (filter === 'ativos') return contratos.filter((c) => c.status === 'ativo');
    if (filter === 'inadimplentes') return contratos.filter((c) => c.inadimplente);
    return contratos;
  }, [contratos, filter]);

  const fetchAll = async () => {
    setLoading(true);
    setError('');
    try {
      const [ctRes, clRes, moRes, cobRes] = await Promise.all([
        api.get<ContratoOut[]>('/api/v1/contratos'),
        api.get<ClienteOut[]>('/api/v1/clientes'),
        api.get<MotoOut[]>('/api/v1/motos'),
        api.get<CobrancaOut[]>('/api/v1/cobrancas'),
      ]);
      setContratos(ctRes.data);
      setClientes(clRes.data);
      setMotos(moRes.data);
      setCobrancas(cobRes.data);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar contratos'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchAll();
  }, [api]);

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
      await fetchAll();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao criar contrato'));
    }
  };

  const handleEncerrar = async (id: number) => {
    if (!confirm('Encerrar este contrato? A moto não será liberada automaticamente.')) return;
    setActionLoading(id);
    setError('');
    try {
      await api.patch(`/api/v1/contratos/${id}`, { status: 'finalizado' });
      await fetchAll();
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
      await fetchAll();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao gerar Pix'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleAssinatura = async (contratoId: number) => {
    setActionLoading(contratoId);
    setError('');
    try {
      await api.post('/api/v1/cobrancas/assinatura-asaas', { contrato_id: contratoId });
      alert('Assinatura Asaas criada com sucesso.');
      await fetchAll();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao criar assinatura'));
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
          <p className="text-muted">{contratos.length} locações cadastradas</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={20} /> Nova locação
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      <div className="filter-tabs glass">
        <Filter size={16} />
        {(['todos', 'ativos', 'inadimplentes'] as FilterTab[]).map((f) => (
          <button
            key={f}
            type="button"
            className={`tab ${filter === f ? 'active' : ''}`}
            onClick={() => handleFilterChange(f)}
          >
            {f === 'todos' ? 'Todos' : f === 'ativos' ? 'Ativos' : 'Inadimplentes'}
          </button>
        ))}
      </div>

      <div className="glass table-container">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando contratos...</p>
        ) : filtered.length === 0 ? (
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
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((ct) => {
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
                              title="Gerar Pix"
                              disabled={busy}
                              onClick={() => void handleGerarPix(ct.id)}
                            >
                              <CreditCard size={16} />
                            </button>
                            <button
                              type="button"
                              className="icon-btn"
                              title="Assinatura Asaas"
                              disabled={busy}
                              onClick={() => void handleAssinatura(ct.id)}
                            >
                              <FileText size={16} />
                            </button>
                            <button
                              type="button"
                              className="icon-btn danger"
                              title="Encerrar"
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
