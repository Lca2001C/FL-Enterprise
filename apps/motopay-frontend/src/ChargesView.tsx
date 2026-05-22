import { useState, useEffect, useMemo, type FormEvent } from 'react';
import { Plus, Copy, CheckCircle, Clock, AlertTriangle, Check, Filter } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { CobrancaOut, ContratoOut } from './apiTypes';
import { formatBrl, formatDate } from './utils/format';
import { parseApiError } from './utils/apiError';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';

type StatusFilter = 'todos' | 'pendente' | 'atrasado' | 'recebido';

const ChargesView = () => {
  const { api } = useAuth();
  const [cobrancas, setCobrancas] = useState<CobrancaOut[]>([]);
  const [contratos, setContratos] = useState<ContratoOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [contratoId, setContratoId] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('todos');
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const contratosAtivos = contratos.filter((c) => c.status === 'ativo');

  const filtered = useMemo(() => {
    if (statusFilter === 'todos') return cobrancas;
    return cobrancas.filter((c) => c.status === statusFilter);
  }, [cobrancas, statusFilter]);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [cobRes, ctRes] = await Promise.all([
        api.get<CobrancaOut[]>('/api/v1/cobrancas'),
        api.get<ContratoOut[]>('/api/v1/contratos'),
      ]);
      setCobrancas(cobRes.data);
      setContratos(ctRes.data);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar cobranças'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, [api]);

  const handleCreateCharge = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await api.post('/api/v1/cobrancas/pix', { contrato_id: parseInt(contratoId, 10) });
      setShowModal(false);
      setContratoId('');
      await fetchData();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao gerar cobrança'));
    }
  };

  const copyPix = async (id: number, text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const displayValor = (cob: CobrancaOut) =>
    cob.dias_atraso > 0 ? cob.valor_total : cob.valor;

  const canCopyPix = (cob: CobrancaOut) =>
    cob.pix_copia_cola && (cob.status === 'pendente' || cob.status === 'atrasado');

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Gestão de Cobranças</h2>
          <p className="text-muted">Acompanhamento de pagamentos e faturamento</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={20} /> Gerar Cobrança
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      <div className="filter-tabs glass">
        <Filter size={16} />
        {(['todos', 'pendente', 'atrasado', 'recebido'] as StatusFilter[]).map((s) => (
          <button
            key={s}
            type="button"
            className={`tab ${statusFilter === s ? 'active' : ''}`}
            onClick={() => setStatusFilter(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="glass table-container">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando cobranças...</p>
        ) : filtered.length === 0 ? (
          <EmptyState
            title="Nenhuma cobrança encontrada"
            description="Gere uma cobrança Pix para um contrato ativo."
            action={
              <button className="btn-primary" onClick={() => setShowModal(true)}>
                <Plus size={18} /> Gerar Cobrança
              </button>
            }
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Vencimento</th>
                <th>Valor</th>
                <th>Status</th>
                <th>Contrato</th>
                <th>Atraso / Multa</th>
                <th style={{ textAlign: 'right' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((cob) => (
                <tr key={cob.id}>
                  <td>
                    <span className="text-muted">#{cob.id}</span>
                  </td>
                  <td>{formatDate(cob.vencimento)}</td>
                  <td style={{ fontWeight: 700 }}>{formatBrl(displayValor(cob))}</td>
                  <td>
                    <span className={`status-badge ${cob.status}`}>
                      {cob.status === 'recebido' ? (
                        <CheckCircle size={12} />
                      ) : cob.status === 'pendente' ? (
                        <Clock size={12} />
                      ) : (
                        <AlertTriangle size={12} />
                      )}
                      {cob.status.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <div className="contrato-tag">Contrato #{cob.contrato_id}</div>
                  </td>
                  <td>
                    {cob.dias_atraso > 0 ? (
                      <div style={{ fontSize: '0.8rem', color: 'var(--danger)' }}>
                        <div style={{ fontWeight: 700 }}>{cob.dias_atraso} dias</div>
                        <div>
                          Multa {formatBrl(cob.multa)} · Juros {formatBrl(cob.juros)}
                        </div>
                        <div>Total {formatBrl(cob.valor_total)}</div>
                      </div>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {canCopyPix(cob) && (
                      <button
                        type="button"
                        className="action-btn-pix"
                        onClick={() => void copyPix(cob.id, cob.pix_copia_cola!)}
                      >
                        {copiedId === cob.id ? <Check size={14} /> : <Copy size={14} />}
                        {copiedId === cob.id ? 'Copiado' : 'PIX'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>Gerar Cobrança Pix</h3>
            <p className="text-muted" style={{ fontSize: '0.8rem', marginBottom: '20px' }}>
              Cria uma cobrança Pix no Asaas para o contrato selecionado.
            </p>
            <form onSubmit={(e) => void handleCreateCharge(e)}>
              <div className="input-group">
                <label className="input-label">Contrato</label>
                <select
                  className="input-field"
                  value={contratoId}
                  onChange={(e) => setContratoId(e.target.value)}
                  required
                >
                  <option value="">Selecione...</option>
                  {contratosAtivos.map((ct) => (
                    <option key={ct.id} value={ct.id}>
                      #{ct.id} — {formatBrl(ct.valor_recorrente)} / {ct.ciclo}
                    </option>
                  ))}
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Gerar Pix
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
          min-width: 720px;
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
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.7rem;
          font-weight: 700;
          width: fit-content;
        }
        .status-badge.recebido {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent);
        }
        .status-badge.pendente {
          background: rgba(245, 158, 11, 0.1);
          color: var(--warning);
        }
        .status-badge.atrasado {
          background: rgba(239, 68, 68, 0.1);
          color: var(--danger);
        }
        .contrato-tag {
          background: rgba(255, 255, 255, 0.05);
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 0.8rem;
          border: 1px solid var(--glass-border);
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
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.8);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 16px;
        }
        .modal-content {
          width: 100%;
          max-width: 420px;
          padding: 30px;
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
      `}</style>
    </div>
  );
};

export default ChargesView;
