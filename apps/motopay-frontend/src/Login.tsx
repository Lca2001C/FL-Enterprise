import { useState, type FormEvent } from 'react';
import { useAuth } from './AuthContext';
import { LogIn, ShieldCheck, Mail, Lock, Settings } from 'lucide-react';
import { parseApiError } from './utils/apiError';

const Login = () => {
  const { login, apiBase, setApiBase } = useAuth();
  const [email, setEmail] = useState(import.meta.env.PROD ? '' : 'admin@motopay.local');
  const [password, setPassword] = useState(import.meta.env.PROD ? '' : 'adminadmin');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: unknown) {
      setError(parseApiError(err, 'Falha na conexão com o servidor'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="bg-gradient"></div>

      <div className="glass login-card animate-fade">
        <div className="card-header">
          <div className="logo-box">
            <ShieldCheck size={32} color="#6366f1" />
          </div>
          <h1 className="brand-font">
            MotoPay <span className="text-primary">Painel</span>
          </h1>
          <p className="text-muted">Acesse o ecossistema de gestão de frotas</p>
        </div>

        {error && <div className="error-alert">{error}</div>}

        <form onSubmit={(e) => void handleSubmit(e)}>
          <div className="input-group">
            <label className="input-label">E-mail</label>
            <div className="input-with-icon">
              <Mail size={18} className="icon" />
              <input
                type="email"
                className="input-field"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">Senha</label>
            <div className="input-with-icon">
              <Lock size={18} className="icon" />
              <input
                type="password"
                className="input-field"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
          </div>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? 'Autenticando...' : (
              <>
                <LogIn size={20} /> Entrar
              </>
            )}
          </button>
        </form>

        <div className="card-footer">
          <button
            type="button"
            className="settings-toggle"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings size={16} /> Configurações de Rede
          </button>

          {showSettings && (
            <div className="settings-panel animate-fade">
              <label className="input-label">URL Base da API</label>
              <input
                type="text"
                className="input-field sm"
                value={apiBase}
                onChange={(e) => setApiBase(e.target.value)}
              />
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        .login-container {
          min-height: 100vh;
          min-height: 100dvh;
          padding: calc(16px + env(safe-area-inset-top, 0px)) max(24px, env(safe-area-inset-right, 0px))
            calc(16px + env(safe-area-inset-bottom, 0px)) max(24px, env(safe-area-inset-left, 0px));
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow-x: hidden;
          overflow-y: auto;
        }
        .bg-gradient {
          position: absolute;
          width: 150%;
          height: 150%;
          background: radial-gradient(circle at 50% 50%, #1e1b4b 0%, #020617 100%);
          z-index: -1;
        }
        .login-card {
          width: 100%;
          max-width: 420px;
          padding: 40px;
          text-align: center;
        }
        .logo-box {
          width: 60px;
          height: 60px;
          background: rgba(99, 102, 241, 0.1);
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 20px;
          border: 1px solid rgba(99, 102, 241, 0.2);
        }
        .card-header h1 {
          font-size: 2rem;
          margin-bottom: 8px;
        }
        .text-primary {
          color: var(--primary);
        }
        .w-full {
          width: 100%;
        }
        .input-with-icon {
          position: relative;
        }
        .input-with-icon .icon {
          position: absolute;
          left: 12px;
          top: 50%;
          transform: translateY(-50%);
          color: var(--text-muted);
        }
        .input-with-icon input {
          padding-left: 40px;
        }
        .error-alert {
          background: rgba(239, 68, 68, 0.1);
          color: var(--danger);
          padding: 12px;
          border-radius: 8px;
          font-size: 0.9rem;
          margin-bottom: 20px;
          border: 1px solid rgba(239, 68, 68, 0.2);
        }
        .card-footer {
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid var(--glass-border);
        }
        .settings-toggle {
          background: none;
          border: none;
          color: var(--text-muted);
          font-size: 0.8rem;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          margin: 0 auto;
        }
        .settings-panel {
          margin-top: 15px;
          text-align: left;
        }
        .input-field.sm {
          padding: 8px 12px;
          font-size: 0.8rem;
        }
      `}</style>
    </div>
  );
};

export default Login;
