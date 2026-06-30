import { useState, useEffect, type FormEvent } from 'react';
import { Plus, Pencil, Trash2, Filter, X, AlertTriangle, Paperclip, Check } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { ContratoOut, MotoOut, MultaOut, Paginated } from './apiTypes';
import { PAGE_SIZE } from './apiTypes';
import { formatBrl, formatDate, todayIso } from './utils/format';
import { parseApiError } from './utils/apiError';
import { fetchAllPaginated } from './utils/fetchPaginated';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';
import AnexoUploader from './components/AnexoUploader';

type MultaForm = {
  moto_id: string;
  contrato_id: string;
  descricao: string;
  orgao: string;
  valor: string;
  data: string;
  vencimento: string;
  status: 'pendente' | 'pago';
};

const emptyForm = (): MultaForm => ({
  moto_id: '',
  contrato_id: '',
  descricao: '',
  orgao: '',
  valor: '',
  data: todayIso(),
  vencimento: '',
  status: 'pendente',
});

type Filters = {
  status: '' | 'pendente' | 'pago';
  moto_id: string;
  q: string;
  data_inicio: string;
  data_fim: string;
};

const emptyFilters = (): Filters => ({ status: '', moto_id: '', q: '', data_inicio: '', data_fim: '' });

const MultasView = () => {
  const { api } = useAuth();
  const [multas, setMultas] = useState<MultaOut[]>([]);
  const [motos, setMotos] = useState<MotoOut[]>([]);
  const [contratos, setContratos] = useState<ContratoOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Filters>(emptyFilters());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [createdHint, setCreatedHint] = useState(false);
  const [form, setForm] = useState<MultaForm>(emptyForm());

  const filterParams = (f: Filters) => ({
    ...(f.status ? { status: f.status } : {}),
    ...(f.moto_id ? { moto_id: parseInt(f.moto_id, 10) } : {}),
    ...(f.q.trim() ? { q: f.q.trim() } : {}),
    ...(f.data_inicio ? { data_inicio: f.data_inicio } : {}),
    ...(f.data_fim ? { data_fim: f.data_fim } : {}),
  });

  const fetchMultas = async (pageOffset = offset, f: Filters = filters) => {
    setLoading(true);
    setError('');
    try {
      const [res, motoItems, contratoItems] = await Promise.all([
        api.get<Paginated<MultaOut>>('/api/v1/multas', {
          params: { limit: PAGE_SIZE, offset: pageOffset, ...filterParams(f) },
        }),
        fetchAllPaginated<MotoOut>(api, '/api/v1/motos'),
        fetchAllPaginated<ContratoOut>(api, '/api/v1/contratos'),
      ]);
      setMultas(res.data.items);
      setTotal(res.data.total);
      setOffset(pageOffset);
      setMotos(motoItems);
      setContratos(contratoItems);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar multas'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchMultas(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  const applyFilters = () => void fetchMultas(0, filters);
  const clearFilters = () => {
    const cleared = emptyFilters();
    setFilters(cleared);
    void fetchMultas(0, cleared);
  };
  const hasActiveFilters = Object.values(filters).some((v) => v !== '');

  const motoLabel = (id: number) => {
    const m = motos.find((x) => x.id === id);
    if (!m) return `#${id}`;
    const parts = [m.modelo, m.ano ? String(m.ano) : '', m.cor || ''].filter(Boolean);
    return `${parts.join(' ')} • ${m.placa}`;
  };

  const contratosDaMoto = form.moto_id
    ? contratos.filter((c) => c.moto_id === parseInt(form.moto_id, 10))
    : contratos;

  const openCreate = () => {
    setEditingId(null);
    setCreatedHint(false);
    setForm(emptyForm());
    setShowModal(true);
  };

  const openEdit = (m: MultaOut) => {
    setEditingId(m.id);
    setCreatedHint(false);
    setForm({
      moto_id: String(m.moto_id),
      contrato_id: m.contrato_id ? String(m.contrato_id) : '',
      descricao: m.descricao,
      orgao: m.orgao || '',
      valor: String(m.valor),
      data: m.data,
      vencimento: m.vencimento || '',
      status: m.status === 'pago' ? 'pago' : 'pendente',
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingId(null);
    setCreatedHint(false);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.moto_id) {
      setError('Selecione a moto da multa');
      return;
    }
    const payload = {
      moto_id: parseInt(form.moto_id, 10),
      contrato_id: form.contrato_id ? parseInt(form.contrato_id, 10) : null,
      descricao: form.descricao,
      orgao: form.orgao.trim() || null,
      valor: parseFloat(form.valor),
      data: form.data,
      vencimento: form.vencimento || null,
      status: form.status,
    };
    try {
      if (editingId != null) {
        await api.patch(`/api/v1/multas/${editingId}`, payload);
        await fetchMultas();
        closeModal();
      } else {
        const res = await api.post<MultaOut>('/api/v1/multas', payload);
        await fetchMultas(0);
        setEditingId(res.data.id);
        setCreatedHint(true);
      }
    } catch (err) {
      setError(parseApiError(err, 'Erro ao salvar multa'));
    }
  };

  const handleDelete = async (m: MultaOut) => {
    if (!confirm('Excluir esta multa? Os anexos vinculados também serão removidos.')) return;
    setError('');
    try {
      await api.delete(`/api/v1/multas/${m.id}`);
      const nextOffset = multas.length === 1 && offset > 0 ? offset - PAGE_SIZE : offset;
      await fetchMultas(nextOffset);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao excluir multa'));
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Multas</h2>
          <p className="text-muted">Controle de multas por veículo, com anexos de PDF e fotos</p>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className={`btn-secondary ${hasActiveFilters ? 'btn-active' : ''}`}
            onClick={() => setShowFilters((v) => !v)}
          >
            <Filter size={18} /> Filtros{hasActiveFilters ? ' (ativos)' : ''}
          </button>
          <button type="button" className="btn-primary" onClick={openCreate}>
            <Plus size={18} /> Nova multa
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <AdminScopeBanner />

      {showFilters && (
        <div className="filter-bar glass">
          <div className="filter-field">
            <label className="input-label">Status</label>
            <select
              className="input-field"
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value as Filters['status'] })}
            >
              <option value="">Todos</option>
              <option value="pendente">Pendente</option>
              <option value="pago">Pago</option>
            </select>
          </div>
          <div className="filter-field">
            <label className="input-label">Moto</label>
            <select
              className="input-field"
              value={filters.moto_id}
              onChange={(e) => setFilters({ ...filters, moto_id: e.target.value })}
            >
              <option value="">Todas</option>
              {motos.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.placa} — {m.modelo}
                </option>
              ))}
            </select>
          </div>
          <div className="filter-field">
            <label className="input-label">De</label>
            <input
              type="date"
              className="input-field"
              value={filters.data_inicio}
              onChange={(e) => setFilters({ ...filters, data_inicio: e.target.value })}
            />
          </div>
          <div className="filter-field">
            <label className="input-label">Até</label>
            <input
              type="date"
              className="input-field"
              value={filters.data_fim}
              onChange={(e) => setFilters({ ...filters, data_fim: e.target.value })}
            />
          </div>
          <div className="filter-field filter-grow">
            <label className="input-label">Buscar</label>
            <input
              className="input-field"
              value={filters.q}
              placeholder="Descrição ou órgão..."
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              onKeyDown={(e) => {
                if (e.key === 'Enter') applyFilters();
              }}
            />
          </div>
          <div className="filter-actions">
            <button type="button" className="btn-primary" onClick={applyFilters}>
              Aplicar
            </button>
            <button type="button" className="btn-secondary" onClick={clearFilters}>
              <X size={16} /> Limpar
            </button>
          </div>
        </div>
      )}

      <div className="glass table-container">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando multas...</p>
        ) : multas.length === 0 ? (
          <EmptyState
            icon={<AlertTriangle size={40} />}
            title="Nenhuma multa"
            description={
              hasActiveFilters
                ? 'Nenhuma multa corresponde aos filtros aplicados.'
                : 'Registre multas de trânsito e anexe o PDF/foto da notificação.'
            }
            action={
              <button className="btn-primary" onClick={openCreate}>
                <Plus size={18} /> Nova multa
              </button>
            }
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Descrição</th>
                <th>Órgão</th>
                <th>Moto</th>
                <th>Locatário</th>
                <th>Valor</th>
                <th>Status</th>
                <th>Anexos</th>
                <th aria-label="Ações" />
              </tr>
            </thead>
            <tbody>
              {multas.map((m) => (
                <tr key={m.id}>
                  <td>{formatDate(m.data)}</td>
                  <td style={{ maxWidth: '240px' }}>{m.descricao}</td>
                  <td className="text-muted">{m.orgao || '—'}</td>
                  <td>{m.moto_descricao || motoLabel(m.moto_id)}</td>
                  <td className={m.locatario_nome ? 'text-primary' : 'text-muted'}>
                    {m.locatario_nome || '—'}
                  </td>
                  <td style={{ fontWeight: 700 }}>{formatBrl(m.valor)}</td>
                  <td>
                    <span className={`badge ${m.status === 'pago' ? 'badge-ok' : 'badge-warn'}`}>
                      {m.status === 'pago' ? (
                        <>
                          <Check size={14} /> Pago
                        </>
                      ) : (
                        'Pendente'
                      )}
                    </span>
                  </td>
                  <td className="text-muted">
                    <span className="anexo-count">
                      <Paperclip size={14} /> {m.total_anexos}
                    </span>
                  </td>
                  <td>
                    <div className="row-actions">
                      <button
                        type="button"
                        className="icon-btn"
                        title="Editar multa"
                        aria-label="Editar multa"
                        onClick={() => openEdit(m)}
                      >
                        <Pencil size={16} />
                        <span className="icon-btn__label">Editar</span>
                      </button>
                      <button
                        type="button"
                        className="icon-btn danger"
                        title="Excluir multa"
                        aria-label="Excluir multa"
                        onClick={() => void handleDelete(m)}
                      >
                        <Trash2 size={16} />
                        <span className="icon-btn__label">Excluir</span>
                      </button>
                    </div>
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
            onClick={() => void fetchMultas(Math.max(0, offset - PAGE_SIZE))}
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
            onClick={() => void fetchMultas(offset + PAGE_SIZE)}
          >
            Próxima
          </button>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>{editingId != null ? 'Editar multa' : 'Nova multa'}</h3>
            <form onSubmit={(e) => void handleSubmit(e)}>
              <div className="input-group">
                <label className="input-label">Moto</label>
                <select
                  className="input-field"
                  value={form.moto_id}
                  onChange={(e) =>
                    setForm({ ...form, moto_id: e.target.value, contrato_id: '' })
                  }
                  required
                >
                  <option value="">Selecione...</option>
                  {motos.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.placa} — {m.modelo}
                    </option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Contrato / locatário (opcional)</label>
                <select
                  className="input-field"
                  value={form.contrato_id}
                  onChange={(e) => setForm({ ...form, contrato_id: e.target.value })}
                >
                  <option value="">Sem contrato vinculado</option>
                  {contratosDaMoto.map((c) => (
                    <option key={c.id} value={c.id}>
                      Contrato #{c.numero ?? c.id} ({c.status})
                    </option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Descrição</label>
                <input
                  className="input-field"
                  value={form.descricao}
                  placeholder="Ex.: Excesso de velocidade"
                  onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Órgão autuador (opcional)</label>
                <input
                  className="input-field"
                  value={form.orgao}
                  placeholder="Ex.: DETRAN-SP"
                  onChange={(e) => setForm({ ...form, orgao: e.target.value })}
                />
              </div>
              <div className="form-row">
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
                  <label className="input-label">Status</label>
                  <select
                    className="input-field"
                    value={form.status}
                    onChange={(e) =>
                      setForm({ ...form, status: e.target.value as 'pendente' | 'pago' })
                    }
                  >
                    <option value="pendente">Pendente</option>
                    <option value="pago">Pago</option>
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="input-group">
                  <label className="input-label">Data da infração</label>
                  <input
                    type="date"
                    className="input-field"
                    value={form.data}
                    onChange={(e) => setForm({ ...form, data: e.target.value })}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Vencimento (opcional)</label>
                  <input
                    type="date"
                    className="input-field"
                    value={form.vencimento}
                    onChange={(e) => setForm({ ...form, vencimento: e.target.value })}
                  />
                </div>
              </div>

              {editingId != null && (
                <div className="input-group">
                  {createdHint && (
                    <p className="hint-ok">Multa salva. Anexe o PDF/foto da notificação abaixo.</p>
                  )}
                  <AnexoUploader
                    entityBase={`/api/v1/multas/${editingId}`}
                    anexoBase="/api/v1/multas"
                  />
                </div>
              )}

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={closeModal}>
                  {editingId != null && createdHint ? 'Concluir' : 'Cancelar'}
                </button>
                <button type="submit" className="btn-primary">
                  {editingId != null ? 'Salvar alterações' : 'Salvar'}
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
        .btn-active {
          outline: 2px solid var(--primary);
        }
        .filter-bar {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          padding: 16px;
          border-radius: 12px;
          margin-bottom: 16px;
          align-items: flex-end;
        }
        .filter-field {
          display: flex;
          flex-direction: column;
          gap: 4px;
          min-width: 140px;
        }
        .filter-grow {
          flex: 1;
          min-width: 200px;
        }
        .filter-actions {
          display: flex;
          gap: 8px;
        }
        .form-row {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }
        .form-row .input-group {
          flex: 1;
          min-width: 140px;
        }
        .table-container {
          overflow-x: auto;
        }
        .custom-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 860px;
        }
        .custom-table th {
          text-align: left;
          padding: 14px 18px;
          color: var(--text-muted);
          font-size: 0.85rem;
          border-bottom: 1px solid var(--glass-border);
        }
        .custom-table td {
          padding: 14px 18px;
          border-bottom: 1px solid var(--glass-border);
          font-size: 0.9rem;
        }
        .badge {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 3px 10px;
          border-radius: 999px;
          font-size: 0.78rem;
          font-weight: 600;
        }
        .badge-ok {
          background: rgba(34, 197, 94, 0.15);
          color: var(--accent);
        }
        .badge-warn {
          background: rgba(234, 179, 8, 0.15);
          color: #eab308;
        }
        .anexo-count {
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }
        .hint-ok {
          color: var(--accent);
          font-size: 0.85rem;
          margin: 0 0 8px;
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

export default MultasView;
