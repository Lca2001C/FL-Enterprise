import { useState, useEffect, type FormEvent } from 'react';
import { ArrowUpCircle, ArrowDownCircle, Download, Plus } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { FinanceiroOut, MotoOut } from './apiTypes';
import { exportCsv, formatBrl, formatDate, todayIso } from './utils/format';
import { parseApiError } from './utils/apiError';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';

const FinanceView = () => {
  const { api } = useAuth();
  const [entries, setEntries] = useState<FinanceiroOut[]>([]);
  const [motos, setMotos] = useState<MotoOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    tipo: 'despesa' as 'receita' | 'despesa',
    valor: '',
    descricao: '',
    data: todayIso(),
    moto_id: '',
  });

  const fetchFinance = async () => {
    setLoading(true);
    setError('');
    try {
      const [finRes, motoRes] = await Promise.all([
        api.get<FinanceiroOut[]>('/api/v1/financeiro'),
        api.get<MotoOut[]>('/api/v1/motos'),
      ]);
      setEntries(finRes.data);
      setMotos(motoRes.data);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar financeiro'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchFinance();
  }, [api]);

  const handleExport = () => {
    const rows = entries.map((e) => [
      formatDate(e.data),
      e.descricao,
      e.tipo,
      String(e.valor),
      e.moto_id ? String(e.moto_id) : '',
    ]);
    exportCsv('extrato-motopay.csv', ['Data', 'Descrição', 'Tipo', 'Valor', 'Moto ID'], rows);
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
        <div className="header-actions">
          <button type="button" className="btn-secondary" onClick={handleExport} disabled={entries.length === 0}>
            <Download size={20} /> Exportar CSV
          </button>
          <button type="button" className="btn-primary" onClick={() => setShowModal(true)}>
            <Plus size={20} /> Novo lançamento
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

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
      `}</style>
    </div>
  );
};

export default FinanceView;
