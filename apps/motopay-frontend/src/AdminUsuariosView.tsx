import { useState, useEffect, useCallback, type FormEvent } from 'react';
import { Filter, UserPlus, Users } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { ClienteOut, OperacaoOut, Paginated, UserAdminOut } from './apiTypes';
import { PAGE_SIZE } from './apiTypes';
import { formatDate, roleLabel } from './utils/format';
import { parseApiError } from './utils/apiError';
import { fetchAllPaginated } from './utils/fetchPaginated';
import ErrorBanner from './components/ErrorBanner';

type UserRole = 'dono' | 'operador' | 'cliente';
type TipoFilter = 'todos' | 'admin' | 'dono' | 'operador' | 'cliente';

const AdminUsuariosView = () => {
  const { api } = useAuth();
  const [operacoes, setOperacoes] = useState<OperacaoOut[]>([]);
  const [clientes, setClientes] = useState<ClienteOut[]>([]);
  const [usuarios, setUsuarios] = useState<UserAdminOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [tipoFilter, setTipoFilter] = useState<TipoFilter>('todos');
  const [operacaoFilter, setOperacaoFilter] = useState('');
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [form, setForm] = useState({
    email: '',
    password: '',
    tipo: 'operador' as UserRole,
    operacao_id: '',
    cliente_id: '',
  });

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  };

  const fetchUsuarios = useCallback(
    async (pageOffset = offset) => {
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
    [api, offset, operacaoFilter, tipoFilter]
  );

  useEffect(() => {
    const loadMeta = async () => {
      setLoadingMeta(true);
      try {
        const [opsRes, clItems] = await Promise.all([
          api.get<OperacaoOut[]>('/api/v1/operacoes'),
          fetchAllPaginated<ClienteOut>(api, '/api/v1/clientes'),
        ]);
        setOperacoes(opsRes.data);
        setClientes(clItems);
      } catch (e) {
        setError(parseApiError(e, 'Erro ao carregar dados'));
      } finally {
        setLoadingMeta(false);
      }
    };
    void loadMeta();
  }, [api]);

  useEffect(() => {
    void fetchUsuarios(0);
  }, [tipoFilter, operacaoFilter, api]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    try {
      if (form.tipo === 'cliente' && !form.operacao_id) {
        setError('Selecione a operação do cliente.');
        setCreating(false);
        return;
      }
      const body: Record<string, unknown> = {
        email: form.email.trim(),
        password: form.password,
        tipo: form.tipo,
      };
      body.operacao_id = form.operacao_id ? parseInt(form.operacao_id, 10) : null;
      if (form.tipo === 'cliente') {
        body.cliente_id = form.cliente_id ? parseInt(form.cliente_id, 10) : null;
      }
      await api.post('/api/v1/usuarios', body);
      setForm({ email: '', password: '', tipo: 'operador', operacao_id: '', cliente_id: '' });
      showToast('Usuário criado com sucesso.');
      await fetchUsuarios(0);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao criar usuário'));
    } finally {
      setCreating(false);
    }
  };

  const clientesFiltrados =
    form.tipo === 'cliente' && form.operacao_id
      ? clientes.filter((c) => c.operacao_id === parseInt(form.operacao_id, 10))
      : [];

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Usuários</h2>
          <p className="text-muted">Visualize e crie acessos para donos, operadores e clientes</p>
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
            <option value="operador">Operador</option>
            <option value="cliente">Cliente</option>
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
          <p style={{ padding: 40, textAlign: 'center' }} className="text-muted">
            Nenhum usuário encontrado com os filtros atuais.
          </p>
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>E-mail</th>
                <th>Tipo</th>
                <th>Operação</th>
                <th>Cliente ID</th>
                <th>Criado em</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td style={{ fontWeight: 600 }}>{u.email}</td>
                  <td>
                    <span className={`role-badge role-${u.tipo}`}>{roleLabel(u.tipo)}</span>
                  </td>
                  <td className="text-muted">{u.operacao_nome ?? (u.operacao_id ? `#${u.operacao_id}` : '—')}</td>
                  <td className="text-muted">{u.cliente_id ?? '—'}</td>
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
          <UserPlus size={20} color="var(--primary)" /> Novo usuário
        </h3>
        {loadingMeta ? (
          <p className="text-muted">Carregando...</p>
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
              <label className="input-label">Tipo</label>
              <select
                className="input-field"
                value={form.tipo}
                onChange={(e) =>
                  setForm({ ...form, tipo: e.target.value as UserRole, cliente_id: '' })
                }
              >
                <option value="dono">Dono</option>
                <option value="operador">Operador</option>
                <option value="cliente">Cliente</option>
              </select>
            </div>
            <div className="input-group">
              <label className="input-label">Operação</label>
              <select
                className="input-field"
                value={form.operacao_id}
                onChange={(e) => setForm({ ...form, operacao_id: e.target.value, cliente_id: '' })}
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
            {form.tipo === 'cliente' && (
              <div className="input-group">
                <label className="input-label">Cliente vinculado</label>
                <select
                  className="input-field"
                  value={form.cliente_id}
                  onChange={(e) => setForm({ ...form, cliente_id: e.target.value })}
                  required
                >
                  <option value="">Selecione...</option>
                  {clientesFiltrados.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nome} — {c.cpf}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? 'Criando...' : 'Criar usuário'}
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
