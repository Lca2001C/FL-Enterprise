import { useState, useEffect, useCallback, type FormEvent } from 'react';
import { Filter, UserPlus, Users } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { Paginated, UserAdminOut } from './apiTypes';
import { PAGE_SIZE } from './apiTypes';
import { formatDate, roleLabel } from './utils/format';
import { parseApiError } from './utils/apiError';
import ErrorBanner from './components/ErrorBanner';
import EmptyState from './components/EmptyState';

type TipoFilter = 'todos' | 'admin' | 'dono';

function operacaoLabel(u: UserAdminOut): string {
  if (u.operacao_nome) return u.operacao_nome;
  if (u.tipo === 'admin') return 'Plataforma';
  if (u.operacao_id) return `#${u.operacao_id}`;
  return '—';
}

const AdminUsuariosView = () => {
  const { api, operacoes, operacoesLoading } = useAuth();
  const [usuarios, setUsuarios] = useState<UserAdminOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [tipoFilter, setTipoFilter] = useState<TipoFilter>('todos');
  const [operacaoFilter, setOperacaoFilter] = useState('');
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [form, setForm] = useState({
    email: '',
    password: '',
    operacao_id: '',
  });

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  };

  const fetchUsuarios = useCallback(
    async (pageOffset: number) => {
      setLoadingUsers(true);
      try {
        const params: Record<string, unknown> = {
          limit: PAGE_SIZE,
          offset: pageOffset,
        };
        if (tipoFilter !== 'todos') params.tipo = tipoFilter;
        if (operacaoFilter) params.operacao_id = parseInt(operacaoFilter, 10);
        const r = await api.get<Paginated<UserAdminOut>>('/api/v1/usuarios', { params });
        setUsuarios(r.data.items);
        setTotal(r.data.total);
        setOffset(pageOffset);
      } catch (e) {
        setError(parseApiError(e, 'Erro ao carregar usuários'));
      } finally {
        setLoadingUsers(false);
      }
    },
    [api, operacaoFilter, tipoFilter]
  );

  useEffect(() => {
    void fetchUsuarios(0);
  }, [fetchUsuarios]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    try {
      if (!form.operacao_id) {
        setError('Selecione a operação do dono.');
        setCreating(false);
        return;
      }
      await api.post('/api/v1/usuarios', {
        email: form.email.trim(),
        password: form.password,
        tipo: 'dono',
        operacao_id: parseInt(form.operacao_id, 10),
      });
      setForm({ email: '', password: '', operacao_id: '' });
      showToast('Dono criado com sucesso.');
      await fetchUsuarios(0);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao criar usuário'));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Usuários</h2>
          <p className="text-muted">Visualize administradores e donos de operação</p>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      {toast && <div className="toast success">{toast}</div>}

      <div className="glass table-container list-card">
        <div className="list-header">
          <h3>
            <Users size={20} color="var(--primary)" /> Todos os usuários
          </h3>
          <span className="text-muted">{total} cadastrado(s)</span>
        </div>

        <div className="filter-row glass">
          <Filter size={16} />
          <select
            className="input-field filter-select"
            value={tipoFilter}
            onChange={(e) => setTipoFilter(e.target.value as TipoFilter)}
          >
            <option value="todos">Todos os tipos</option>
            <option value="admin">Administrador</option>
            <option value="dono">Dono</option>
          </select>
          <select
            className="input-field filter-select"
            value={operacaoFilter}
            onChange={(e) => setOperacaoFilter(e.target.value)}
          >
            <option value="">Todas as operações</option>
            {operacoes.map((op) => (
              <option key={op.id} value={op.id}>
                {op.nome}
              </option>
            ))}
          </select>
        </div>

        {loadingUsers ? (
          <p style={{ padding: 40, textAlign: 'center' }} className="text-muted">
            Carregando usuários...
          </p>
        ) : usuarios.length === 0 ? (
          <EmptyState
            icon={<Users size={40} />}
            title="Nenhum usuário encontrado"
            description="Ajuste os filtros ou crie um novo dono abaixo."
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>E-mail</th>
                <th>Tipo</th>
                <th>Operação</th>
                <th>Criado em</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td className="text-muted">#{u.id}</td>
                  <td style={{ fontWeight: 600 }}>{u.email}</td>
                  <td>
                    <span className={`role-badge role-${u.tipo}`}>{roleLabel(u.tipo)}</span>
                  </td>
                  <td className="text-muted">{operacaoLabel(u)}</td>
                  <td className="text-muted">{formatDate(u.created_at)}</td>
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
            disabled={offset === 0 || loadingUsers}
            onClick={() => void fetchUsuarios(Math.max(0, offset - PAGE_SIZE))}
          >
            Anterior
          </button>
          <span className="text-muted">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
          </span>
          <button
            type="button"
            className="btn-secondary"
            disabled={offset + PAGE_SIZE >= total || loadingUsers}
            onClick={() => void fetchUsuarios(offset + PAGE_SIZE)}
          >
            Próxima
          </button>
        </div>
      )}

      <div className="glass card form-card">
        <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
          <UserPlus size={20} color="var(--primary)" /> Novo dono
        </h3>
        {operacoesLoading ? (
          <p className="text-muted">Carregando operações...</p>
        ) : (
          <form onSubmit={(e) => void handleCreate(e)}>
            <div className="input-group">
              <label className="input-label">E-mail</label>
              <input
                type="email"
                className="input-field"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>
            <div className="input-group">
              <label className="input-label">Senha (mín. 8 caracteres)</label>
              <input
                type="password"
                className="input-field"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
                minLength={8}
              />
            </div>
            <div className="input-group">
              <label className="input-label">Operação</label>
              <select
                className="input-field"
                value={form.operacao_id}
                onChange={(e) => setForm({ ...form, operacao_id: e.target.value })}
                required
              >
                <option value="">Selecione...</option>
                {operacoes.map((op) => (
                  <option key={op.id} value={op.id}>
                    {op.nome}
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? 'Criando...' : 'Criar dono'}
            </button>
          </form>
        )}
      </div>

      <style jsx>{`
        .view-header {
          margin-bottom: 20px;
        }
        .list-card {
          margin-bottom: 20px;
          overflow: hidden;
        }
        .list-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 20px 24px 12px;
          flex-wrap: wrap;
          gap: 8px;
        }
        .list-header h3 {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 1rem;
          margin: 0;
        }
        .filter-row {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 0 16px 16px;
          padding: 12px 16px;
          flex-wrap: wrap;
        }
        .filter-select {
          width: auto;
          min-width: 180px;
        }
        .table-container {
          overflow-x: auto;
        }
        .custom-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 640px;
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
        .role-badge {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 999px;
          font-size: 0.75rem;
          font-weight: 600;
          background: rgba(99, 102, 241, 0.15);
          color: var(--primary);
        }
        .role-badge.role-dono {
          background: rgba(16, 185, 129, 0.15);
          color: var(--accent);
        }
        .role-badge.role-admin {
          background: rgba(245, 158, 11, 0.15);
          color: var(--warning);
        }
        .form-card {
          padding: 24px;
          max-width: 480px;
        }
        .input-group {
          margin-bottom: 15px;
        }
        .pagination {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 16px;
          padding: 12px 20px;
          margin-bottom: 20px;
        }
        .btn-secondary {
          background: var(--secondary);
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 8px;
          cursor: pointer;
        }
        .btn-secondary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .toast {
          padding: 12px 16px;
          border-radius: 8px;
          margin-bottom: 16px;
          font-size: 0.9rem;
        }
        .toast.success {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent);
          border: 1px solid rgba(16, 185, 129, 0.2);
        }
      `}</style>
    </div>
  );
};

export default AdminUsuariosView;
