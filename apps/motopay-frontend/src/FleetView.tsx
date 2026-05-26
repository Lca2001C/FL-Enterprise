import { useState, useEffect, useCallback, type FormEvent } from 'react';
import { Plus, Search, Trash2, Edit2 } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { MotoOut, Paginated } from './apiTypes';
import { PAGE_SIZE } from './apiTypes';
import { parseApiError } from './utils/apiError';
import { offsetAfterDelete } from './utils/fetchPaginated';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';

const STATUS_OPTIONS = ['disponivel', 'alugada', 'manutencao', 'inativa'] as const;

const FleetView = () => {
  const { api } = useAuth();
  const [motos, setMotos] = useState<MotoOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('todos');
  const [showModal, setShowModal] = useState(false);
  const [editMoto, setEditMoto] = useState<MotoOut | null>(null);
  const [formData, setFormData] = useState({ placa: '', modelo: '', status: 'disponivel', km: 0 });
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const fetchMotos = useCallback(
    async (pageOffset = 0) => {
      setLoading(true);
      setError('');
      try {
        const params: Record<string, unknown> = { limit: PAGE_SIZE, offset: pageOffset };
        if (statusFilter !== 'todos') params.status = statusFilter;
        if (debouncedSearch.trim()) params.q = debouncedSearch.trim();
        const r = await api.get<Paginated<MotoOut>>('/api/v1/motos', { params });
        setMotos(r.data.items);
        setTotal(r.data.total);
        setOffset(pageOffset);
      } catch (e) {
        setError(parseApiError(e, 'Erro ao carregar frota'));
      } finally {
        setLoading(false);
      }
    },
    [api, statusFilter, debouncedSearch]
  );

  useEffect(() => {
    void fetchMotos(0);
  }, [fetchMotos]);

  const openCreate = () => {
    setEditMoto(null);
    setFormData({ placa: '', modelo: '', status: 'disponivel', km: 0 });
    setShowModal(true);
  };

  const openEdit = (moto: MotoOut) => {
    setEditMoto(moto);
    setFormData({ placa: moto.placa, modelo: moto.modelo, status: moto.status, km: moto.km });
    setShowModal(true);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      if (editMoto) {
        await api.patch(`/api/v1/motos/${editMoto.id}`, {
          placa: formData.placa,
          modelo: formData.modelo,
          status: formData.status,
          km: formData.km,
        });
      } else {
        await api.post('/api/v1/motos', formData);
      }
      setShowModal(false);
      await fetchMotos(offset);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao salvar moto'));
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Deseja realmente excluir esta moto?')) return;
    setError('');
    const wasLast = motos.length === 1;
    try {
      await api.delete(`/api/v1/motos/${id}`);
      await fetchMotos(offsetAfterDelete(offset, PAGE_SIZE, wasLast));
    } catch (err) {
      setError(parseApiError(err, 'Erro ao excluir moto'));
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Gestão de Frota</h2>
          <p className="text-muted">Total de {total} veículos cadastrados</p>
        </div>
        <button className="btn-primary" onClick={openCreate} data-tour="fleet-add">
          <Plus size={20} /> Nova Moto
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <AdminScopeBanner />

      <div className="table-actions glass">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Buscar por placa ou modelo..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="input-field filter-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="todos">Todos os status</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div className="glass table-container">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando frota...</p>
        ) : motos.length === 0 ? (
          <EmptyState
            title="Nenhuma moto encontrada"
            description="Cadastre veículos para iniciar locações."
            action={
              <button className="btn-primary" onClick={openCreate}>
                <Plus size={18} /> Nova Moto
              </button>
            }
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>Placa</th>
                <th>Modelo</th>
                <th>KM</th>
                <th>Status</th>
                <th>Motorista</th>
                <th style={{ textAlign: 'right' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {motos.map((moto) => (
                <tr key={moto.id}>
                  <td className="font-mono">{moto.placa}</td>
                  <td>{moto.modelo}</td>
                  <td>{moto.km.toLocaleString('pt-BR')}</td>
                  <td>
                    <span className={`status-badge ${moto.status}`}>
                      {moto.status.toUpperCase()}
                    </span>
                  </td>
                  <td className={moto.cliente_nome ? 'text-primary' : 'text-muted'}>
                    {moto.cliente_nome || '—'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button type="button" className="icon-btn" onClick={() => openEdit(moto)}>
                      <Edit2 size={16} />
                    </button>
                    <button
                      type="button"
                      className="icon-btn danger"
                      onClick={() => void handleDelete(moto.id)}
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
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
            onClick={() => void fetchMotos(Math.max(0, offset - PAGE_SIZE))}
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
            onClick={() => void fetchMotos(offset + PAGE_SIZE)}
          >
            Próxima
          </button>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>{editMoto ? 'Editar Moto' : 'Cadastrar Nova Moto'}</h3>
            <form onSubmit={(e) => void handleSubmit(e)}>
              <div className="input-group">
                <label className="input-label">Placa</label>
                <input
                  className="input-field"
                  value={formData.placa}
                  onChange={(e) =>
                    setFormData({ ...formData, placa: e.target.value.toUpperCase() })
                  }
                  placeholder="ABC-1234"
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Modelo</label>
                <input
                  className="input-field"
                  value={formData.modelo}
                  onChange={(e) => setFormData({ ...formData, modelo: e.target.value })}
                  placeholder="Honda CG 160"
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">KM</label>
                <input
                  className="input-field"
                  type="number"
                  min={0}
                  step={1}
                  value={formData.km}
                  onChange={(e) => setFormData({ ...formData, km: Number(e.target.value) })}
                  placeholder="0"
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Status</label>
                <select
                  className="input-field"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                >
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </option>
                  ))}
                </select>
                {formData.status === 'manutencao' && (
                  <small className="text-muted">
                    Ao salvar, o locatário ativo será notificado via Telegram.
                  </small>
                )}
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
        .table-actions {
          padding: 15px;
          display: flex;
          gap: 15px;
          margin-bottom: 20px;
          border-radius: 12px;
          flex-wrap: wrap;
        }
        .search-box {
          flex: 1;
          min-width: 200px;
          display: flex;
          align-items: center;
          gap: 10px;
          background: rgba(0, 0, 0, 0.2);
          padding: 0 15px;
          border-radius: 8px;
          border: 1px solid var(--glass-border);
        }
        .search-box input {
          background: none;
          border: none;
          color: white;
          width: 100%;
          padding: 10px 0;
          outline: none;
        }
        .filter-select {
          min-width: 160px;
          padding: 8px 12px;
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
        .font-mono {
          font-family: monospace;
          font-weight: 600;
          letter-spacing: 1px;
        }
        .status-badge {
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.7rem;
          font-weight: 700;
        }
        .status-badge.disponivel {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent);
        }
        .status-badge.alugada {
          background: rgba(99, 102, 241, 0.1);
          color: var(--primary);
        }
        .status-badge.manutencao {
          background: rgba(245, 158, 11, 0.1);
          color: var(--warning);
        }
        .status-badge.inativa {
          background: rgba(239, 68, 68, 0.1);
          color: var(--danger);
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
      `}</style>
    </div>
  );
};

export default FleetView;
