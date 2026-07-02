import { useState, useEffect, type FormEvent } from 'react';
import { Plus, Pencil, Trash2, Filter, X, Wrench, FileDown } from 'lucide-react';
import { useAuth } from './AuthContext';
import type {
  ManutencaoCausa,
  ManutencaoOut,
  ManutencaoResumoOut,
  ManutencaoTipo,
  MotoOut,
  Paginated,
} from './apiTypes';
import { PAGE_SIZE } from './apiTypes';
import { formatBrl, formatDate, todayIso } from './utils/format';
import { parseApiError } from './utils/apiError';
import { fetchAllPaginated } from './utils/fetchPaginated';
import {
  buildManutencaoReportHtml,
  formatKm,
  MANUTENCAO_CAUSA_LABELS,
  MANUTENCAO_TIPO_LABELS,
} from './utils/reportHtml';
import { printHtmlDocument } from './utils/printHtml';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';
import AdminScopeBanner from './components/AdminScopeBanner';

const DESCRICAO_SUGESTOES = [
  'Trocar óleo de motor',
  'Trocar filtro de óleo motor',
  'Lâmpadas',
  'Pneu traseiro',
  'Pneu dianteiro',
  'Kit relação (pinhão, coroa e corrente)',
  'Borracharia',
  'Lona de freio traseiro',
  'Lona de freio dianteiro',
  'Troca de bateria',
  'Desamassar roda',
  'Câmara de ar',
];

type ManutencaoForm = {
  moto_id: string;
  tipo: ManutencaoTipo;
  descricao: string;
  causa: ManutencaoCausa;
  valor: string;
  data: string;
  km: string;
};

const emptyForm = (): ManutencaoForm => ({
  moto_id: '',
  tipo: 'preventiva',
  descricao: '',
  causa: 'prevencao',
  valor: '',
  data: todayIso(),
  km: '',
});

type Filters = {
  tipo: '' | ManutencaoTipo;
  causa: '' | ManutencaoCausa;
  moto_id: string;
  q: string;
  data_inicio: string;
  data_fim: string;
};

const emptyFilters = (): Filters => ({
  tipo: '',
  causa: '',
  moto_id: '',
  q: '',
  data_inicio: '',
  data_fim: '',
});

const ManutencoesView = () => {
  const { api } = useAuth();
  const [rows, setRows] = useState<ManutencaoOut[]>([]);
  const [motos, setMotos] = useState<MotoOut[]>([]);
  const [resumo, setResumo] = useState<ManutencaoResumoOut | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Filters>(emptyFilters());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<ManutencaoForm>(emptyForm());

  const filterParams = (f: Filters) => ({
    ...(f.tipo ? { tipo: f.tipo } : {}),
    ...(f.causa ? { causa: f.causa } : {}),
    ...(f.moto_id ? { moto_id: parseInt(f.moto_id, 10) } : {}),
    ...(f.q.trim() ? { q: f.q.trim() } : {}),
    ...(f.data_inicio ? { data_inicio: f.data_inicio } : {}),
    ...(f.data_fim ? { data_fim: f.data_fim } : {}),
  });

  const fetchRows = async (pageOffset = offset, f: Filters = filters) => {
    setLoading(true);
    setError('');
    try {
      const [res, resumoRes, motoItems] = await Promise.all([
        api.get<Paginated<ManutencaoOut>>('/api/v1/manutencoes', {
          params: { limit: PAGE_SIZE, offset: pageOffset, ...filterParams(f) },
        }),
        api.get<ManutencaoResumoOut>('/api/v1/manutencoes/resumo', {
          params: filterParams(f),
        }),
        fetchAllPaginated<MotoOut>(api, '/api/v1/motos'),
      ]);
      setRows(res.data.items);
      setTotal(res.data.total);
      setOffset(pageOffset);
      setResumo(resumoRes.data);
      setMotos(motoItems);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar manutenções'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchRows(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  const applyFilters = () => void fetchRows(0, filters);
  const clearFilters = () => {
    const cleared = emptyFilters();
    setFilters(cleared);
    void fetchRows(0, cleared);
  };
  const hasActiveFilters = Object.values(filters).some((v) => v !== '');

  const motoLabel = (m: ManutencaoOut): string => {
    if (m.moto_descricao) return m.moto_descricao;
    const moto = motos.find((x) => x.id === m.moto_id);
    return moto ? `${moto.placa} — ${moto.modelo}` : `#${m.moto_id}`;
  };

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setShowModal(true);
  };

  const openEdit = (m: ManutencaoOut) => {
    setEditingId(m.id);
    setForm({
      moto_id: String(m.moto_id),
      tipo: m.tipo,
      descricao: m.descricao,
      causa: m.causa,
      valor: String(m.valor),
      data: m.data,
      km: m.km != null ? String(m.km) : '',
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingId(null);
  };

  const handleTipoChange = (tipo: ManutencaoTipo) => {
    setForm((prev) => {
      // Ajusta a causa apenas se ela ainda for o padrão do tipo anterior.
      const causaPadrao: Record<ManutencaoTipo, ManutencaoCausa> = {
        preventiva: 'prevencao',
        corretiva: 'desgaste',
      };
      const eraPadrao = prev.causa === causaPadrao[prev.tipo];
      return { ...prev, tipo, causa: eraPadrao ? causaPadrao[tipo] : prev.causa };
    });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setError('');
    if (!form.moto_id) {
      setError('Selecione o veículo da manutenção');
      return;
    }
    const valor = parseFloat(form.valor);
    if (!Number.isFinite(valor) || valor <= 0) {
      setError('Informe um valor maior que zero');
      return;
    }
    if (!form.descricao.trim()) {
      setError('Descreva a manutenção realizada');
      return;
    }
    if (form.km && !/^\d+$/.test(form.km.trim())) {
      setError('KM deve ser um número inteiro');
      return;
    }
    setSubmitting(true);
    const payload = {
      moto_id: parseInt(form.moto_id, 10),
      tipo: form.tipo,
      descricao: form.descricao.trim(),
      causa: form.causa,
      valor,
      data: form.data,
      km: form.km ? parseInt(form.km, 10) : null,
    };
    try {
      if (editingId != null) {
        await api.patch(`/api/v1/manutencoes/${editingId}`, payload);
      } else {
        await api.post<ManutencaoOut>('/api/v1/manutencoes', payload);
      }
      await fetchRows(editingId != null ? offset : 0);
      closeModal();
    } catch (err) {
      setError(parseApiError(err, 'Erro ao salvar manutenção'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (m: ManutencaoOut) => {
    if (
      !confirm(
        'Excluir esta manutenção? A despesa vinculada no financeiro também será removida.'
      )
    )
      return;
    setError('');
    try {
      await api.delete(`/api/v1/manutencoes/${m.id}`);
      const nextOffset = rows.length === 1 && offset > 0 ? offset - PAGE_SIZE : offset;
      await fetchRows(nextOffset);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao excluir manutenção'));
    }
  };

  const exportPdf = async () => {
    if (exporting) return;
    setExporting(true);
    setError('');
    try {
      // Exporta TODAS as linhas do filtro atual (não só a página visível).
      const [allRows, resumoRes] = await Promise.all([
        fetchAllPaginated<ManutencaoOut>(api, '/api/v1/manutencoes', filterParams(filters)),
        api.get<ManutencaoResumoOut>('/api/v1/manutencoes/resumo', {
          params: filterParams(filters),
        }),
      ]);
      const r = resumoRes.data;
      const html = buildManutencaoReportHtml(
        allRows.map((m) => ({
          moto: motoLabel(m),
          tipo: m.tipo,
          descricao: m.descricao,
          causa: m.causa,
          valor: m.valor,
          data: m.data,
          km: m.km,
        })),
        {
          totalGeral: r.total_geral,
          quantidade: r.quantidade,
          totalPreventiva: r.total_preventiva,
          totalCorretiva: r.total_corretiva,
          porMoto: r.por_moto.map((pm) => ({
            moto: `${pm.placa} — ${pm.modelo}`,
            total: pm.total,
            quantidade: pm.quantidade,
          })),
        },
        todayIso()
      );
      printHtmlDocument(html);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao exportar PDF de manutenções'));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Manutenções</h2>
          <p className="text-muted">
            Controle de serviços de manutenção — cada registro gera a despesa no financeiro
          </p>
        </div>
        <div className="header-actions">
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
            onClick={() => void exportPdf()}
            disabled={total === 0 || exporting}
          >
            <FileDown size={18} /> {exporting ? 'Gerando…' : 'Exportar PDF'}
          </button>
          <button type="button" className="btn-primary" onClick={openCreate}>
            <Plus size={18} /> Nova manutenção
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
              <option value="preventiva">Preventiva</option>
              <option value="corretiva">Corretiva</option>
            </select>
          </div>
          <div className="filter-field">
            <label className="input-label">Causa</label>
            <select
              className="input-field"
              value={filters.causa}
              onChange={(e) =>
                setFilters({ ...filters, causa: e.target.value as Filters['causa'] })
              }
            >
              <option value="">Todas</option>
              <option value="prevencao">Prevenção</option>
              <option value="desgaste">Desgaste</option>
              <option value="mau_uso">Mau uso</option>
              <option value="outro">Outro</option>
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
              placeholder="Descrição do serviço..."
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

      {!loading && resumo && resumo.quantidade > 0 && (
        <div className="summary-grid glass">
          <div className="summary-card total">
            <span>Total gasto</span>
            <strong>{formatBrl(resumo.total_geral)}</strong>
          </div>
          <div className="summary-card">
            <span>Preventivas</span>
            <strong>{formatBrl(resumo.total_preventiva)}</strong>
          </div>
          <div className="summary-card">
            <span>Corretivas</span>
            <strong>{formatBrl(resumo.total_corretiva)}</strong>
          </div>
          <div className="summary-card">
            <span>Serviços</span>
            <strong>{resumo.quantidade}</strong>
          </div>
        </div>
      )}

      <div className="glass table-container">
        {loading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando manutenções...</p>
        ) : rows.length === 0 ? (
          <EmptyState
            icon={<Wrench size={40} />}
            title="Nenhuma manutenção"
            description={
              hasActiveFilters
                ? 'Nenhuma manutenção corresponde aos filtros aplicados.'
                : 'Registre trocas de óleo, pneus, freios e demais serviços por veículo.'
            }
            action={
              <button className="btn-primary" onClick={openCreate}>
                <Plus size={18} /> Nova manutenção
              </button>
            }
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>Data do serviço</th>
                <th>Veículo</th>
                <th>Tipo</th>
                <th>Manutenção</th>
                <th>Causa</th>
                <th>Valor</th>
                <th>Km</th>
                <th aria-label="Ações" />
              </tr>
            </thead>
            <tbody>
              {rows.map((m) => (
                <tr key={m.id}>
                  <td>{formatDate(m.data)}</td>
                  <td>{motoLabel(m)}</td>
                  <td>
                    <span className={`badge ${m.tipo === 'preventiva' ? 'badge-info' : 'badge-warn'}`}>
                      {MANUTENCAO_TIPO_LABELS[m.tipo] ?? m.tipo}
                    </span>
                  </td>
                  <td style={{ maxWidth: '240px' }}>{m.descricao}</td>
                  <td className="text-muted">{MANUTENCAO_CAUSA_LABELS[m.causa] ?? m.causa}</td>
                  <td style={{ fontWeight: 700 }}>{formatBrl(m.valor)}</td>
                  <td className="text-muted">{formatKm(m.km)}</td>
                  <td>
                    <div className="row-actions">
                      <button
                        type="button"
                        className="icon-btn"
                        title="Editar manutenção"
                        aria-label="Editar manutenção"
                        onClick={() => openEdit(m)}
                      >
                        <Pencil size={16} />
                        <span className="icon-btn__label">Editar</span>
                      </button>
                      <button
                        type="button"
                        className="icon-btn danger"
                        title="Excluir manutenção"
                        aria-label="Excluir manutenção"
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
            onClick={() => void fetchRows(Math.max(0, offset - PAGE_SIZE))}
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
            onClick={() => void fetchRows(offset + PAGE_SIZE)}
          >
            Próxima
          </button>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="glass modal-content animate-fade">
            <h3>{editingId != null ? 'Editar manutenção' : 'Nova manutenção'}</h3>
            <p className="text-muted modal-subtitle">
              A despesa correspondente é criada e mantida automaticamente no financeiro.
            </p>
            <form onSubmit={(e) => void handleSubmit(e)}>
              <div className="input-group">
                <label className="input-label">Veículo</label>
                <select
                  className="input-field"
                  value={form.moto_id}
                  onChange={(e) => setForm({ ...form, moto_id: e.target.value })}
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
              <div className="form-row">
                <div className="input-group">
                  <label className="input-label">Tipo de manutenção</label>
                  <select
                    className="input-field"
                    value={form.tipo}
                    onChange={(e) => handleTipoChange(e.target.value as ManutencaoTipo)}
                    required
                  >
                    <option value="preventiva">Preventiva</option>
                    <option value="corretiva">Corretiva</option>
                  </select>
                </div>
                <div className="input-group">
                  <label className="input-label">Causa</label>
                  <select
                    className="input-field"
                    value={form.causa}
                    onChange={(e) =>
                      setForm({ ...form, causa: e.target.value as ManutencaoCausa })
                    }
                    required
                  >
                    <option value="prevencao">Prevenção</option>
                    <option value="desgaste">Desgaste</option>
                    <option value="mau_uso">Mau uso</option>
                    <option value="outro">Outro</option>
                  </select>
                </div>
              </div>
              <div className="input-group">
                <label className="input-label">Manutenção (descrição)</label>
                <input
                  className="input-field"
                  value={form.descricao}
                  placeholder="Ex.: Trocar óleo de motor"
                  list="manutencao-sugestoes"
                  onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                  required
                />
                <datalist id="manutencao-sugestoes">
                  {DESCRICAO_SUGESTOES.map((s) => (
                    <option key={s} value={s} />
                  ))}
                </datalist>
              </div>
              <div className="form-row">
                <div className="input-group">
                  <label className="input-label">Valor (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    className="input-field"
                    value={form.valor}
                    onChange={(e) => setForm({ ...form, valor: e.target.value })}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Data do serviço</label>
                  <input
                    type="date"
                    className="input-field"
                    value={form.data}
                    onChange={(e) => setForm({ ...form, data: e.target.value })}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Km (opcional)</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    className="input-field"
                    value={form.km}
                    placeholder="Ex.: 24215"
                    onChange={(e) => setForm({ ...form, km: e.target.value })}
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={closeModal}>
                  Cancelar
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
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
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
        .summary-card.total strong {
          color: var(--danger);
        }
        .modal-subtitle {
          font-size: 0.82rem;
          margin: -6px 0 14px;
        }
        .form-row {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }
        .form-row .input-group {
          flex: 1;
          min-width: 130px;
        }
        .table-container {
          overflow-x: auto;
        }
        .custom-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 900px;
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
        .badge-info {
          background: rgba(59, 130, 246, 0.15);
          color: #60a5fa;
        }
        .badge-warn {
          background: rgba(234, 179, 8, 0.15);
          color: #eab308;
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

export default ManutencoesView;
