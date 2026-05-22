import { useState, useEffect, useCallback, type FormEvent } from 'react';
import { Plus, Search, Star, Phone, Trash2, Bike, FileText } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { ClienteOut, Paginated } from './apiTypes';
import { PAGE_SIZE } from './apiTypes';
import { parseApiError } from './utils/apiError';
import { offsetAfterDelete } from './utils/fetchPaginated';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';

const ClientsView = () => {
  const { api, navigateToContracts } = useAuth();
  const [clientes, setClientes] = useState<ClienteOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editCliente, setEditCliente] = useState<ClienteOut | null>(null);
  const [formData, setFormData] = useState({
    nome: '',
    cpf: '',
    telefone: '',
    telegram_id: '',
  });
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const fetchClientes = useCallback(
    async (pageOffset = 0) => {
      setLoading(true);
      setError('');
      try {
        const params: Record<string, unknown> = { limit: PAGE_SIZE, offset: pageOffset };
        if (debouncedSearch.trim()) params.q = debouncedSearch.trim();
        const r = await api.get<Paginated<ClienteOut>>('/api/v1/clientes', { params });
        setClientes(r.data.items);
        setTotal(r.data.total);
        setOffset(pageOffset);
      } catch (e) {
        setError(parseApiError(e, 'Erro ao carregar clientes'));
      } finally {
        setLoading(false);
      }
    },
    [api, debouncedSearch]
  );

  useEffect(() => {
    void fetchClientes(0);
  }, [fetchClientes]);

  const openCreate = () => {
    setEditCliente(null);
    setFormData({ nome: '', cpf: '', telefone: '', telegram_id: '' });
    setShowModal(true);
  };

  const openEdit = (c: ClienteOut) => {
    setEditCliente(c);
    setFormData({
      nome: c.nome,
      cpf: c.cpf,
      telefone: c.telefone,
      telegram_id: c.telegram_id ?? '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      if (editCliente) {
        await api.patch(`/api/v1/clientes/${editCliente.id}`, {
          nome: formData.nome,
          telefone: formData.telefone,
          telegram_id: formData.telegram_id || null,
        });
      } else {
        await api.post('/api/v1/clientes', {
          nome: formData.nome,
          cpf: formData.cpf,
          telefone: formData.telefone,
          telegram_id: formData.telegram_id || null,
        });
      }
      setShowModal(false);
      await fetchClientes(offset);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao salvar cliente'));
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Deseja realmente excluir este cliente?')) return;
    setError('');
    const wasLast = clientes.length === 1;
    try {
      await api.delete(`/api/v1/clientes/${id}`);
      await fetchClientes(offsetAfterDelete(offset, PAGE_SIZE, wasLast));
    } catch (err) {
      setError(parseApiError(err, 'Erro ao excluir cliente'));
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Base de Clientes</h2>
          <p className="text-muted">{total} motoristas parceiros</p>
        </div>
        <button className="btn-primary" onClick={openCreate} data-tour="clients-add">
          <Plus size={20} /> Novo Cliente
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <AdminScopeBanner />

      <div className="table-actions glass">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Buscar por nome ou CPF..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="glass table-container" data-tour="clients-table">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando clientes...</p>
        ) : clientes.length === 0 ? (
          <EmptyState
            title={search ? 'Nenhum resultado' : 'Nenhum cliente cadastrado'}
            description={
              search
                ? 'Tente outro termo de busca.'
                : 'Cadastre clientes com Telegram ID para receber cobranças automáticas.'
            }
            action={
              !search ? (
                <button className="btn-primary" onClick={openCreate}>
                  <Plus size={18} /> Novo Cliente
                </button>
              ) : undefined
            }
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>CPF</th>
                <th>Telefone</th>
                <th>Telegram</th>
                <th>Score</th>
                <th style={{ textAlign: 'right' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{c.nome}</div>
                    {c.moto_placa && (
                      <div
                        style={{
                          fontSize: '0.75rem',
                          color: 'var(--primary)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                        }}
                      >
                        <Bike size={12} /> {c.moto_placa} - {c.moto_modelo}
                      </div>
                    )}
                  </td>
                  <td className="text-muted">{c.cpf}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Phone size={14} color="#94a3b8" /> {c.telefone}
                    </div>
                  </td>
                  <td className={c.telegram_id ? '' : 'text-muted'}>
                    {c.telegram_id || '—'}
                  </td>
                  <td>
                    <div className="score-badge">
                      <Star
                        size={12}
                        fill={c.score > 80 ? '#10b981' : '#f59e0b'}
                        stroke="none"
                      />
                      {c.score} pts
                    </div>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      type="button"
                      className="icon-btn"
                      title="Ver contratos"
                      onClick={() => navigateToContracts('todos', c.id)}
                    >
                      <FileText size={16} />
                    </button>
                    <button type="button" className="icon-btn" onClick={() => openEdit(c)}>
                      Editar
                    </button>
                    <button
                      type="button"
                      className="icon-btn danger"
                      onClick={() => void handleDelete(c.id)}
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
            onClick={() => void fetchClientes(Math.max(0, offset - PAGE_SIZE))}
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
            onClick={() => void fetchClientes(offset + PAGE_SIZE)}
          >
            Próxima
          </button>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>{editCliente ? 'Editar Cliente' : 'Cadastrar Novo Cliente'}</h3>
            <form onSubmit={(e) => void handleSubmit(e)}>
              <div className="input-group">
                <label className="input-label">Nome Completo</label>
                <input
                  className="input-field"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  required
                />
              </div>
              {!editCliente && (
                <div className="input-group">
                  <label className="input-label">CPF</label>
                  <input
                    className="input-field"
                    value={formData.cpf}
                    onChange={(e) => setFormData({ ...formData, cpf: e.target.value })}
                    placeholder="000.000.000-00"
                    required
                  />
                </div>
              )}
              <div className="input-group">
                <label className="input-label">Telefone (WhatsApp)</label>
                <input
                  className="input-field"
                  value={formData.telefone}
                  onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                  placeholder="(00) 00000-0000"
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Telegram ID</label>
                <input
                  className="input-field"
                  value={formData.telegram_id}
                  onChange={(e) => setFormData({ ...formData, telegram_id: e.target.value })}
                  placeholder="ID numérico do chat (obrigatório para bot)"
                />
                <small className="text-muted">
                  Necessário para lembretes, Pix em atraso e confirmação de pagamento.
                </small>
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
        }
        .search-box {
          flex: 1;
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
        .table-container {
          overflow-x: auto;
        }
        .custom-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 700px;
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
        .score-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          background: rgba(255, 255, 255, 0.05);
          padding: 4px 10px;
          border-radius: 20px;
          width: fit-content;
          font-size: 0.8rem;
          font-weight: 600;
        }
        .icon-btn {
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 5px;
          font-size: 0.8rem;
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

export default ClientsView;
