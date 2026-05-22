import { useState, useEffect } from 'react';
import { Copy, Check, ExternalLink, LogOut, Shield, Calendar, FileText } from 'lucide-react';
import { useAuth } from './AuthContext';
import type { CobrancaOut, ContratoOut, Paginated } from './apiTypes';
import { formatBrl, formatDate } from './utils/format';
import { parseApiError } from './utils/apiError';
import ErrorBanner from './components/ErrorBanner';

const botUsername = (import.meta.env.VITE_TELEGRAM_BOT_USERNAME as string | undefined)?.replace(
  '@',
  ''
);
const botLink = botUsername ? `https://t.me/${botUsername}` : null;

const ClientPortalView = () => {
  const { api, logout, user } = useAuth();
  const [contrato, setContrato] = useState<ContratoOut | null>(null);
  const [cobranca, setCobranca] = useState<CobrancaOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const [ctRes, cobRes] = await Promise.all([
          api.get<ContratoOut>('/api/v1/portal/contrato'),
          api.get<Paginated<CobrancaOut>>('/api/v1/portal/cobrancas', {
            params: { limit: 10, offset: 0 },
          }),
        ]);
        setContrato(ctRes.data);
        const pending = cobRes.data.items.find(
          (c) => c.status === 'pendente' || c.status === 'atrasado'
        );
        setCobranca(pending ?? null);
      } catch (e) {
        setError(parseApiError(e, 'Erro ao carregar seus dados'));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [api]);

  const copyPix = async () => {
    if (!cobranca?.pix_copia_cola) return;
    await navigator.clipboard.writeText(cobranca.pix_copia_cola);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const displayValor = cobranca
    ? cobranca.dias_atraso > 0
      ? cobranca.valor_total
      : cobranca.valor
    : 0;

  return (
    <div className="portal-layout">
      <header className="portal-header glass">
        <div className="brand">
          <Shield size={22} color="#6366f1" />
          <span className="brand-font">MotoPay Portal</span>
        </div>
        <button type="button" className="logout-btn" onClick={logout}>
          <LogOut size={16} /> Sair
        </button>
      </header>

      <main className="portal-main">
        <div className="welcome">
          <h1>Olá, {user?.email.split('@')[0]}</h1>
          <p className="text-muted">Acompanhe seu contrato e pagamentos</p>
        </div>

        {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

        {loading ? (
          <p className="text-muted">Carregando...</p>
        ) : (
          <div className="cards">
            <div className="glass card">
              <h2>
                <FileText size={18} /> Contrato ativo
              </h2>
              {contrato ? (
                <div className="info-grid">
                  <div>
                    <span className="label">Valor</span>
                    <strong>{formatBrl(contrato.valor_recorrente)}</strong>
                  </div>
                  <div>
                    <span className="label">Ciclo</span>
                    <strong>{contrato.ciclo}</strong>
                  </div>
                  <div>
                    <span className="label">Próximo vencimento</span>
                    <strong>{formatDate(contrato.proximo_vencimento)}</strong>
                  </div>
                  {contrato.promessa_pagamento_em && (
                    <div className="promessa">
                      <Calendar size={14} />
                      Promessa: {formatDate(contrato.promessa_pagamento_em)}
                      {contrato.promessa_notas && (
                        <span className="text-muted"> — {contrato.promessa_notas}</span>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-muted">Nenhum contrato ativo.</p>
              )}
            </div>

            <div className="glass card">
              <h2>Cobrança pendente</h2>
              {cobranca ? (
                <>
                  <div className="cobranca-valor">{formatBrl(displayValor)}</div>
                  <p className="text-muted">
                    Vencimento: {formatDate(cobranca.vencimento)}
                    {cobranca.dias_atraso > 0 && (
                      <span className="atraso"> · {cobranca.dias_atraso} dia(s) em atraso</span>
                    )}
                  </p>
                  {cobranca.pix_copia_cola && (
                    <button type="button" className="btn-primary pix-btn" onClick={() => void copyPix()}>
                      {copied ? <Check size={18} /> : <Copy size={18} />}
                      {copied ? 'Pix copiado!' : 'Copiar Pix'}
                    </button>
                  )}
                </>
              ) : (
                <p className="text-muted">Nenhuma cobrança pendente no momento.</p>
              )}
            </div>

            <div className="glass card">
              <h2>Registrar promessa de pagamento</h2>
              <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 16 }}>
                Use o bot do Telegram para informar quando você pretende pagar.
              </p>
              {botLink ? (
                <a href={botLink} target="_blank" rel="noopener noreferrer" className="bot-link">
                  <ExternalLink size={16} /> Abrir bot no Telegram
                </a>
              ) : (
                <p className="text-muted" style={{ fontSize: '0.85rem' }}>
                  Abra o bot da sua operação no Telegram e envie o comando de promessa.
                </p>
              )}
            </div>
          </div>
        )}
      </main>

      <style jsx>{`
        .portal-layout {
          min-height: 100vh;
          min-height: 100dvh;
          padding-bottom: env(safe-area-inset-bottom, 0px);
        }
        .portal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 24px;
          padding-top: calc(12px + env(safe-area-inset-top, 0px));
          border-radius: 0;
        }
        .brand {
          display: flex;
          align-items: center;
          gap: 10px;
          font-weight: 700;
        }
        .logout-btn {
          background: rgba(239, 68, 68, 0.1);
          color: var(--danger);
          border: none;
          padding: 8px 14px;
          border-radius: 8px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: 0.85rem;
        }
        .portal-main {
          max-width: 640px;
          margin: 0 auto;
          padding: 24px;
        }
        .welcome {
          margin-bottom: 24px;
        }
        .welcome h1 {
          font-size: 1.5rem;
          margin-bottom: 4px;
        }
        .cards {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .card {
          padding: 24px;
        }
        .card h2 {
          font-size: 1rem;
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 16px;
        }
        .info-grid {
          display: grid;
          gap: 12px;
        }
        .label {
          display: block;
          font-size: 0.75rem;
          color: var(--text-muted);
          margin-bottom: 2px;
        }
        .promessa {
          display: flex;
          align-items: flex-start;
          gap: 6px;
          font-size: 0.85rem;
          color: var(--warning);
          margin-top: 8px;
        }
        .cobranca-valor {
          font-size: 1.8rem;
          font-weight: 700;
          font-family: 'Outfit', sans-serif;
          margin-bottom: 8px;
        }
        .atraso {
          color: var(--danger);
        }
        .pix-btn {
          margin-top: 16px;
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }
        .bot-link {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          color: var(--primary);
          text-decoration: none;
          font-weight: 600;
          font-size: 0.9rem;
        }
        .bot-link:hover {
          text-decoration: underline;
        }
      `}</style>
    </div>
  );
};

export default ClientPortalView;
