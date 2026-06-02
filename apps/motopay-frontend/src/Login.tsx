import { useState, type FormEvent } from 'react';
import { useAuth } from './AuthContext';
import { LogIn, Shield, Mail, Lock, Settings } from 'lucide-react';
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
      <div className="bg-orb orb-a"></div>
      <div className="bg-orb orb-b"></div>

      <div className="login-card animate-fade">
        <div className="card-header">
          <div className="logo-box">
            <Shield size={28} color="#d4a574" />
          </div>
          <h1 className="brand-font">
            MotoPay
          </h1>
          <p className="login-subtitle">Gestão de Frotas & Cobranças</p>
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>Entre com suas credenciais de acesso</p>
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
          background: var(--bg-main);
        }
        .bg-gradient {
          position: absolute;
          inset: 0;
          background:
            radial-gradient(ellipse 80% 60% at 30% 20%, rgba(212,165,116,0.06) 0%, transparent 55%),
            radial-gradient(ellipse 60% 50% at 70% 80%, rgba(212,165,116,0.04) 0%, transparent 50%);
          z-index: 0;
        }
        .bg-orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          pointer-events: none;
          z-index: 0;
        }
        .orb-a {
          width: 400px; height: 400px;
          top: -100px; left: -80px;
          background: rgba(212,165,116,0.06);
        }
        .orb-b {
          width: 300px; height: 300px;
          bottom: -60px; right: -60px;
          background: rgba(212,165,116,0.04);
        }
        .login-card {
          position: relative;
          z-index: 1;
          width: 100%;
          max-width: 400px;
          padding: 40px 36px;
          background: rgba(16,13,22,0.9);
          border: 1px solid rgba(212,165,116,0.15);
          border-radius: var(--radius-lg);
          box-shadow:
            0 32px 80px rgba(0,0,0,0.7),
            inset 0 1px 0 rgba(212,165,116,0.08);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
        }
        .card-header {
          text-align: center;
          margin-bottom: 28px;
        }
        .logo-box {
          width: 58px;
          height: 58px;
          background: rgba(212,165,116,0.08);
          border-radius: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 18px;
          border: 1px solid rgba(212,165,116,0.2);
          box-shadow: 0 0 30px rgba(212,165,116,0.1);
        }
        .card-header h1 {
          font-size: 1.9rem;
          margin-bottom: 4px;
          color: var(--text-main);
          letter-spacing: 0.02em;
        }
        .login-subtitle {
          font-size: 0.75rem;
          font-weight: 700;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--primary);
          margin-bottom: 8px;
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
          background: rgba(224,92,92,0.08);
          color: var(--danger);
          padding: 12px 14px;
          border-radius: var(--radius-sm);
          font-size: 0.88rem;
          margin-bottom: 20px;
          border: 1px solid rgba(224,92,92,0.2);
        }
        .card-footer {
          margin-top: 24px;
          padding-top: 18px;
          border-top: 1px solid var(--glass-border);
          text-align: center;
        }
        .settings-toggle {
          background: none;
          border: none;
          color: var(--text-muted);
          font-size: 0.8rem;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          margin: 0 auto;
          transition: var(--transition);
        }
        .settings-toggle:hover { color: var(--text-main); }
        .settings-panel {
          margin-top: 14px;
          text-align: left;
        }
        .input-field.sm {
          padding: 8px 12px;
          font-size: 0.82rem;
        }
      `}</style>
    </div>
  );
};

export default Login;
