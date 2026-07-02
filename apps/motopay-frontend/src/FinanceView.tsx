import { useState, useEffect, useMemo, type FormEvent } from 'react';
import {
  ArrowUpCircle,
  ArrowDownCircle,
  FileText,
  Plus,
  Pencil,
  Trash2,
  Filter,
  X,
} from 'lucide-react';
import { useAuth } from './AuthContext';
import type { FinanceiroOut, MotoOut, Paginated } from './apiTypes';
import { PAGE_SIZE } from './apiTypes';
import { formatBrl, formatDate, todayIso } from './utils/format';
import { parseApiError } from './utils/apiError';
import { fetchAllPaginated } from './utils/fetchPaginated';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';
import AnexoUploader from './components/AnexoUploader';
import FinanceStatementModal, { computeTotals } from './components/FinanceStatementModal';

type FinanceForm = {
  tipo: 'receita' | 'despesa';
  valor: string;
  descricao: string;
  data: string;
  moto_id: string;
};

const emptyForm = (): FinanceForm => ({
  tipo: 'despesa',
  valor: '',
  descricao: '',
  data: todayIso(),
  moto_id: '',
});

type Filters = {
  tipo: '' | 'receita' | 'despesa';
  moto_id: string;
  q: string;
  data_inicio: string;
  data_fim: string;
};

const emptyFilters = (): Filters => ({ tipo: '', moto_id: '', q: '', data_inicio: '', data_fim: '' });

const motoLabel = (e: FinanceiroOut): string => {
  if (e.moto_descricao) return e.moto_descricao;
  if (e.moto_id) return `#${e.moto_id}`;
  return '—';
};

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
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Filters>(emptyFilters());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [createdHint, setCreatedHint] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<FinanceForm>(emptyForm());

  const allTotals = useMemo(() => computeTotals(allEntries), [allEntries]);

  const filterParams = (f: Filters) => ({
    ...(f.tipo ? { tipo: f.tipo } : {}),
    ...(f.moto_id ? { moto_id: parseInt(f.moto_id, 10) } : {}),
    ...(f.q.trim() ? { q: f.q.trim() } : {}),
    ...(f.data_inicio ? { data_inicio: f.data_inicio } : {}),
    ...(f.data_fim ? { data_fim: f.data_fim } : {}),
  });

  const fetchFinance = async (pageOffset = offset, f: Filters = filters) => {
    setLoading(true);
    setError('');
    try {
      const [finRes, motoItems, allItems] = await Promise.all([
        api.get<Paginated<FinanceiroOut>>('/api/v1/financeiro', {
          params: { limit: PAGE_SIZE, offset: pageOffset, ...filterParams(f) },
        }),
        fetchAllPaginated<MotoOut>(api, '/api/v1/motos'),
        // Respeita os filtros ativos: o resumo e o extrato/PDF devem refletir
        // o período/moto/tipo selecionados, não a base inteira.
        fetchAllPaginated<FinanceiroOut>(api, '/api/v1/financeiro', filterParams(f)),
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
    void fetchFinance(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  const applyFilters = () => {
    void fetchFinance(0, filters);
  };

  const clearFilters = () => {
    const cleared = emptyFilters();
    setFilters(cleared);
    void fetchFinance(0, cleared);
  };

  const hasActiveFilters = Object.values(filters).some((v) => v !== '');

  const openStatement = () => {
    if (allEntries.length === 0) return;
    setShowStatement(true);
  };

  const openCreate = () => {
    setEditingId(null);
    setCreatedHint(false);
    setForm(emptyForm());
    setShowModal(true);
  };

  const openEdit = (e: FinanceiroOut) => {
    setEditingId(e.id);
    setCreatedHint(false);
    setForm({
      tipo: e.tipo === 'receita' ? 'receita' : 'despesa',
      valor: String(e.valor),
      descricao: e.descricao,
      data: e.data,
      moto_id: e.moto_id ? String(e.moto_id) : '',
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
    if (submitting) return;
    setError('');
    const payload = {
      tipo: form.tipo,
      valor: parseFloat(form.valor),
      descricao: form.descricao,
      data: form.data,
      moto_id: form.moto_id ? parseInt(form.moto_id, 10) : null,
    };
    setSubmitting(true);
    try {
      if (editingId != null) {
        await api.patch(`/api/v1/financeiro/${editingId}`, payload);
        await fetchFinance();
        closeModal();
      } else {
        const res = await api.post<FinanceiroOut>('/api/v1/financeiro', payload);
        await fetchFinance(0);
        // Mantém o modal aberto em modo edição para permitir anexar PDF/fotos.
        setEditingId(res.data.id);
        setCreatedHint(true);
      }
    } catch (err) {
      setError(parseApiError(err, 'Erro ao salvar lançamento'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (entry: FinanceiroOut) => {
    if (!confirm('Excluir este lançamento? Esta ação não pode ser desfeita.')) return;
    setError('');
    try {
      await api.delete(`/api/v1/financeiro/${entry.id}`);
      const nextOffset = entries.length === 1 && offset > 0 ? offset - PAGE_SIZE : offset;
      await fetchFinance(nextOffset);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao excluir lançamento'));
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
            className={`btn-secondary ${hasActiveFilters ? 'btn-active' : ''}`}
            onClick={() => setShowFilters((v) => !v)}
          >
            <Filter size={18} /> Filtros{hasActiveFilters ? ' (ativos)' : ''}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => void openStatement()}
            disabled={total === 0}
          >
            <FileText size={18} /> Ver extrato
          </button>
          <button type="button" className="btn-primary" onClick={openCreate}>
            <Plus size={18} /> Novo lançamento
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <AdminScopeBanner />

      {showFilters && (
        <div className="filter-bar glass">
          <div className="filter-field">
            <label className="input-label">Tipo</label>
            <select
              className="input-field"
              value={filters.tipo}
              onChange={(e) => setFilters({ ...filters, tipo: e.target.value as Filters['tipo'] })}
            >
              <option value="">Todos</option>
              <option value="receita">Receita</option>
              <option value="despesa">Despesa</option>
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
            <label className="input-label">Buscar descrição</label>
            <input
              className="input-field"
              value={filters.q}
              placeholder="Ex.: manutenção, aluguel..."
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
          <div className="summary-card despesa">
            <span>Manutenção</span>
            <strong>{formatBrl(allTotals.manutencao)}</strong>
          </div>
        </div>
      )}

      <div className="glass table-container">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando extrato...</p>
        ) : entries.length === 0 ? (
          <EmptyState
            title="Nenhum lançamento"
            description={
              hasActiveFilters
                ? 'Nenhum lançamento corresponde aos filtros aplicados.'
                : 'Registre despesas de manutenção ou receitas manuais.'
            }
            action={
              <button className="btn-primary" onClick={openCreate}>
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
                <th>Locatário</th>
                <th aria-label="Ações" />
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td>{formatDate(e.data)}</td>
                  <td style={{ maxWidth: '280px' }}>
                    {e.descricao}
                    {e.categoria === 'manutencao' && (
                      <span className="origem-badge" title="Gerado pelo módulo de Manutenções">
                        Manutenção
                      </span>
                    )}
                  </td>
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
                  <td className={e.moto_descricao ? '' : 'text-muted'}>{motoLabel(e)}</td>
                  <td className={e.locatario_nome ? 'text-primary' : 'text-muted'}>
                    {e.locatario_nome || '—'}
                  </td>
                  <td>
                    {e.categoria === 'manutencao' ? (
                      <span className="text-muted" style={{ fontSize: '0.78rem' }}>
                        Gerencie em Manutenções
                      </span>
                    ) : (
                      <div className="row-actions">
                        <button
                          type="button"
                          className="icon-btn"
                          title="Editar lançamento"
                          aria-label="Editar lançamento"
                          onClick={() => openEdit(e)}
                        >
                          <Pencil size={16} />
                          <span className="icon-btn__label">Editar</span>
                        </button>
                        <button
                          type="button"
                          className="icon-btn danger"
                          title="Excluir lançamento"
                          aria-label="Excluir lançamento"
                          onClick={() => void handleDelete(e)}
                        >
                          <Trash2 size={16} />
                          <span className="icon-btn__label">Excluir</span>
                        </button>
                      </div>
                    )}
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
            <h3>{editingId != null ? 'Editar lançamento' : 'Novo lançamento'}</h3>
            <form onSubmit={(e) => void handleSubmit(e)}>
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

              {editingId != null && (
                <div className="input-group">
                  {createdHint && (
                    <p className="hint-ok">
                      Lançamento salvo. Anexe PDF/fotos abaixo se desejar.
                    </p>
                  )}
                  <AnexoUploader
                    entityBase={`/api/v1/financeiro/${editingId}`}
                    anexoBase="/api/v1/financeiro"
                  />
                </div>
              )}

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={closeModal}>
                  {editingId != null && createdHint ? 'Concluir' : 'Cancelar'}
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? 'Salvando…' : editingId != null ? 'Salvar alterações' : 'Salvar'}
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
        .hint-ok {
          color: var(--accent);
          font-size: 0.85rem;
          margin: 0 0 8px;
        }
        .origem-badge {
          display: inline-block;
          margin-left: 8px;
          padding: 1px 8px;
          border-radius: 999px;
          font-size: 0.68rem;
          font-weight: 700;
          background: rgba(59, 130, 246, 0.15);
          color: #60a5fa;
          vertical-align: middle;
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
