import { useState, type FormEvent } from 'react';
import { KeyRound, LogOut, ShieldCheck, HelpCircle } from 'lucide-react';
import { useAuth } from './AuthContext';
import { parseApiError } from './utils/apiError';
import ErrorBanner from './components/ErrorBanner';
import { isOwnerTourEligible } from './guide/ownerTourSteps';

const AccountView = () => {
  const { api, logout, user, resetOwnerTour } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [loggingOutAll, setLoggingOutAll] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  };

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (newPassword !== confirmPassword) {
      setError('A confirmação da nova senha não confere.');
      return;
    }
    if (newPassword.length < 8) {
      setError('A nova senha deve ter pelo menos 8 caracteres.');
      return;
    }
    setSaving(true);
    try {
      await api.post('/api/v1/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      showToast('Senha alterada. Você foi desconectado de outros dispositivos.');
    } catch (err) {
      setError(parseApiError(err, 'Erro ao alterar senha'));
    } finally {
      setSaving(false);
    }
  };

  const handleLogoutAll = async () => {
    if (!confirm('Encerrar sessão em todos os dispositivos?')) return;
    setLoggingOutAll(true);
    setError('');
    try {
      await api.post('/api/v1/auth/logout-all');
      showToast('Sessões encerradas em todos os dispositivos.');
    } catch (err) {
      setError(parseApiError(err, 'Erro ao encerrar sessões'));
    } finally {
      setLoggingOutAll(false);
    }
  };

  return (
    <div className="view-container animate-fade">
      <div className="view-header">
        <div>
          <h2>Minha Conta</h2>
          <p className="text-muted">{user?.email}</p>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      {toast && <div className="toast success">{toast}</div>}

      {isOwnerTourEligible(user?.tipo) && (
        <div className="glass card" style={{ maxWidth: '480px', marginBottom: 24 }} data-tour="account-help">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <HelpCircle size={20} color="var(--primary)" /> Ajuda
          </h3>
          <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 16 }}>
            Revise o tour guiado pelas telas do painel sempre que precisar relembrar fluxos de cobrança,
            Telegram e ajustes da operação.
          </p>
          <button type="button" className="btn-primary" onClick={() => resetOwnerTour()}>
            Reiniciar tour guiado
          </button>
        </div>
      )}

      <div className="glass card" style={{ maxWidth: '480px', marginBottom: 24 }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
          <KeyRound size={20} color="var(--primary)" /> Alterar senha
        </h3>
        <form onSubmit={(e) => void handleChangePassword(e)}>
          <div className="input-group">
            <label className="input-label">Senha atual</label>
            <input
              type="password"
              className="input-field"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
          <div className="input-group">
            <label className="input-label">Nova senha</label>
            <input
              type="password"
              className="input-field"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>
          <div className="input-group">
            <label className="input-label">Confirmar nova senha</label>
            <input
              type="password"
              className="input-field"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Salvando...' : 'Alterar senha'}
          </button>
        </form>
      </div>

      <div className="glass card" style={{ maxWidth: '480px' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <ShieldCheck size={20} color="var(--warning)" /> Segurança
        </h3>
        <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 16 }}>
          Encerre todas as sessões ativas em outros navegadores e dispositivos.
        </p>
        <div className="actions-row">
          <button
            type="button"
            className="btn-secondary"
            disabled={loggingOutAll}
            onClick={() => void handleLogoutAll()}
          >
            {loggingOutAll ? 'Encerrando...' : 'Encerrar em todos os dispositivos'}
          </button>
          <button type="button" className="logout-btn" onClick={logout}>
            <LogOut size={16} /> Sair deste dispositivo
          </button>
        </div>
      </div>

      <style jsx>{`
        .view-header {
          margin-bottom: 20px;
        }
        .input-group {
          margin-bottom: 15px;
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
        .actions-row {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }
        .btn-secondary {
          background: var(--secondary);
          color: white;
          border: none;
          padding: 10px 16px;
          border-radius: 8px;
          cursor: pointer;
        }
        .logout-btn {
          background: rgba(239, 68, 68, 0.1);
          color: var(--danger);
          border: none;
          padding: 10px 16px;
          border-radius: 8px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }
        .logout-btn:hover {
          background: var(--danger);
          color: white;
        }
      `}</style>
    </div>
  );
};

export default AccountView;
