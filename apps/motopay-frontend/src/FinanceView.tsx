import { useState, useEffect, useMemo, type FormEvent } from 'react';
import { ArrowUpCircle, ArrowDownCircle, FileText, Plus } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { FinanceiroOut, MotoOut, Paginated } from './apiTypes';
import { PAGE_SIZE } from './apiTypes';
import { formatBrl, formatDate, todayIso } from './utils/format';
import { parseApiError } from './utils/apiError';
import { fetchAllPaginated } from './utils/fetchPaginated';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';
import FinanceStatementModal, { computeTotals } from './components/FinanceStatementModal';

const FinanceView = () => {
  const { api } = useAuth();
  const [entries, setEntries] = useState<FinanceiroOut[]>([]);
  const [allEntries, setAllEntries] = useState<FinanceiroOut[]>([]);
  const [motos, setMotos] = useState<MotoOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showStatement, setShowStatement] = useState(false);
  const [form, setForm] = useState({
    tipo: 'despesa' as 'receita' | 'despesa',
    valor: '',
    descricao: '',
    data: todayIso(),
    moto_id: '',
  });

  const allTotals = useMemo(() => computeTotals(allEntries), [allEntries]);

  const fetchFinance = async (pageOffset = offset) => {
    setLoading(true);
    setError('');
    try {
      const [finRes, motoItems, allItems] = await Promise.all([
        api.get<Paginated<FinanceiroOut>>('/api/v1/financeiro', {
          params: { limit: PAGE_SIZE, offset: pageOffset },
        }),
        fetchAllPaginated<MotoOut>(api, '/api/v1/motos'),
        fetchAllPaginated<FinanceiroOut>(api, '/api/v1/financeiro'),
      ]);
      setEntries(finRes.data.items);
      setAllEntries(allItems);
      setTotal(finRes.data.total);
      setOffset(pageOffset);
      setMotos(motoItems);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar financeiro'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchFinance();
  }, [api]);

  const openStatement = () => {
    if (allEntries.length === 0) return;
    setShowStatement(true);
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await api.post('/api/v1/financeiro', {
        tipo: form.tipo,
        valor: parseFloat(form.valor),
        descricao: form.descricao,
        data: form.data,
        moto_id: form.moto_id ? parseInt(form.moto_id, 10) : null,
      });
      setShowModal(false);
      setForm({ tipo: 'despesa', valor: '', descricao: '', data: todayIso(), moto_id: '' });
      await fetchFinance();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao registrar lançamento'));
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Movimentação Financeira</h2>
          <p className="text-muted">Histórico de entradas e saídas</p>
        </div>
        <div className="header-actions" data-tour="finance-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => void openStatement()}
            disabled={total === 0}
          >
            <FileText size={20} /> Ver extrato
          </button>
          <button type="button" className="btn-primary" onClick={() => setShowModal(true)}>
            <Plus size={20} /> Novo lançamento
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <AdminScopeBanner />

      {!loading && allEntries.length > 0 && (
        <div className="summary-grid glass">
          <div className="summary-card receita">
            <span>Receitas</span>
            <strong>{formatBrl(allTotals.receitas)}</strong>
          </div>
          <div className="summary-card despesa">
            <span>Despesas</span>
            <strong>{formatBrl(allTotals.despesas)}</strong>
          </div>
          <div className="summary-card saldo">
            <span>Saldo</span>
            <strong>{formatBrl(allTotals.saldo)}</strong>
          </div>
        </div>
      )}

      <div className="glass table-container">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando extrato...</p>
        ) : entries.length === 0 ? (
          <EmptyState
            title="Nenhum lançamento"
            description="Registre despesas de manutenção ou receitas manuais."
            action={
              <button className="btn-primary" onClick={() => setShowModal(true)}>
                <Plus size={18} /> Novo lançamento
              </button>
            }
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Descrição</th>
                <th>Tipo</th>
                <th>Valor</th>
                <th>Moto</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td>{formatDate(e.data)}</td>
                  <td style={{ maxWidth: '300px' }}>{e.descricao}</td>
                  <td>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        color: e.tipo === 'receita' ? 'var(--accent)' : 'var(--danger)',
                      }}
                    >
                      {e.tipo === 'receita' ? (
                        <ArrowUpCircle size={16} />
                      ) : (
                        <ArrowDownCircle size={16} />
                      )}
                      {e.tipo.toUpperCase()}
                    </div>
                  </td>
                  <td style={{ fontWeight: 700 }}>{formatBrl(e.valor)}</td>
                  <td className="text-muted">{e.moto_id ? `#${e.moto_id}` : '—'}</td>
                </tr>
              ))}
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
            onClick={() => void fetchFinance(Math.max(0, offset - PAGE_SIZE))}
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
            onClick={() => void fetchFinance(offset + PAGE_SIZE)}
          >
            Próxima
          </button>
        </div>
      )}

      {showStatement && (
        <FinanceStatementModal
          entries={allEntries}
          motos={motos}
          onClose={() => setShowStatement(false)}
        />
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>Novo lançamento</h3>
            <form onSubmit={(e) => void handleCreate(e)}>
              <div className="input-group">
                <label className="input-label">Tipo</label>
                <select
                  className="input-field"
                  value={form.tipo}
                  onChange={(e) =>
                    setForm({ ...form, tipo: e.target.value as 'receita' | 'despesa' })
                  }
                >
                  <option value="despesa">Despesa</option>
                  <option value="receita">Receita</option>
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Valor (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  className="input-field"
                  value={form.valor}
                  onChange={(e) => setForm({ ...form, valor: e.target.value })}
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Descrição</label>
                <input
                  className="input-field"
                  value={form.descricao}
                  onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Data</label>
                <input
                  type="date"
                  className="input-field"
                  value={form.data}
                  onChange={(e) => setForm({ ...form, data: e.target.value })}
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Moto (opcional)</label>
                <select
                  className="input-field"
                  value={form.moto_id}
                  onChange={(e) => setForm({ ...form, moto_id: e.target.value })}
                >
                  <option value="">Nenhuma</option>
                  {motos.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.placa} — {m.modelo}
                    </option>
                  ))}
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Salvar
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
        .header-actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }
        .summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 12px;
          margin-bottom: 16px;
          padding: 16px;
          border-radius: 12px;
        }
        .summary-card {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .summary-card span {
          font-size: 0.75rem;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .summary-card strong {
          font-size: 1.1rem;
        }
        .summary-card.receita strong {
          color: var(--accent);
        }
        .summary-card.despesa strong {
          color: var(--danger);
        }
        .summary-card.saldo strong,
        .summary-card.total strong {
          color: var(--primary);
        }
        .table-container {
          overflow-x: auto;
        }
        .custom-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 600px;
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
        .btn-secondary {
          background: var(--secondary);
          color: white;
          border: none;
          padding: 10px 16px;
          border-radius: 8px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }
        .btn-secondary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .pagination {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          margin-top: 16px;
          border-radius: 12px;
        }
      `}</style>
    </div>
  );
};

export default FinanceView;
