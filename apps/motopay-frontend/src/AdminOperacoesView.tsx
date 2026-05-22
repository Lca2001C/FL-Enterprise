import { useState, type FormEvent } from 'react';
import { Building2, Plus } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { OperacaoOut } from './apiTypes';
import { formatDate } from './utils/format';
import { parseApiError } from './utils/apiError';
import EmptyState from './components/EmptyState';
import ErrorBanner from './components/ErrorBanner';

const AdminOperacoesView = () => {
  const { api, operacoes, operacoesLoading, refreshOperacoes, setOperacaoScopeId } = useAuth();
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [nome, setNome] = useState('');

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = nome.trim();
    if (!trimmed) {
      setError('Informe o nome da operação.');
      return;
    }
    if (trimmed.length > 255) {
      setError('Nome da operação deve ter no máximo 255 caracteres.');
      return;
    }
    const duplicate = operacoes.some((op) => op.nome.toLowerCase() === trimmed.toLowerCase());
    if (duplicate) {
      setError('Já existe uma operação com este nome.');
      return;
    }

    setCreating(true);
    setError('');
    try {
      const res = await api.post<OperacaoOut>('/api/v1/operacoes', { nome: trimmed });
      setNome('');
      showToast('Operação criada com sucesso.');
      await refreshOperacoes();
      setOperacaoScopeId(res.data.id);
    } catch (err) {
      setError(parseApiError(err, 'Erro ao criar operação'));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Operações</h2>
          <p className="text-muted">Gerencie operações da plataforma</p>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      {toast && <div className="toast success">{toast}</div>}

      <div className="glass card form-card">
        <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <Plus size={20} color="var(--primary)" /> Nova operação
        </h3>
        <form onSubmit={(e) => void handleCreate(e)} className="create-form">
          <input
            type="text"
            className="input-field"
            placeholder="Nome da operação"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            maxLength={255}
            required
          />
          <button type="submit" className="btn-primary" disabled={creating || !nome.trim()}>
            {creating ? 'Criando...' : 'Criar'}
          </button>
        </form>
      </div>

      <div className="glass table-container">
        {operacoesLoading ? (
          <p style={{ padding: 40, textAlign: 'center' }}>Carregando operações...</p>
        ) : operacoes.length === 0 ? (
          <EmptyState
            icon={<Building2 size={40} />}
            title="Nenhuma operação cadastrada"
            description="Crie a primeira operação para vincular donos e frotas."
          />
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nome</th>
                <th>Gateway</th>
                <th>Criada em</th>
              </tr>
            </thead>
            <tbody>
              {operacoes.map((op) => (
                <tr key={op.id}>
                  <td className="text-muted">#{op.id}</td>
                  <td style={{ fontWeight: 600 }}>{op.nome}</td>
                  <td>
                    <span className={`gateway-badge ${op.payment_provider}`}>
                      {op.payment_provider === 'mercadopago' ? 'Mercado Pago' : 'Asaas'}
                    </span>
                  </td>
                  <td>{formatDate(op.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <style jsx>{`
        .view-header {
          margin-bottom: 20px;
        }
        .form-card {
          padding: 24px;
          margin-bottom: 20px;
          max-width: 560px;
        }
        .create-form {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }
        .create-form .input-field {
          flex: 1;
          min-width: 200px;
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
        .table-container {
          overflow-x: auto;
        }
        .custom-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 480px;
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
        .gateway-badge {
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.75rem;
          font-weight: 600;
        }
        .gateway-badge.asaas {
          background: rgba(99, 102, 241, 0.1);
          color: var(--primary);
        }
        .gateway-badge.mercadopago {
          background: rgba(245, 158, 11, 0.1);
          color: var(--warning);
        }
      `}</style>
    </div>
  );
};

export default AdminOperacoesView;
