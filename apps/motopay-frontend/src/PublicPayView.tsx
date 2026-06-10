import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { Copy, Check, Shield, CreditCard } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import PaymentBrickCheckout from './integrations/mercadopago/PaymentBrickCheckout';
import StatusScreenCheckout from './integrations/mercadopago/StatusScreenCheckout';
import { initMercadoPagoSdk } from './integrations/mercadopago/init';
import { ensureMercadoPagoDeviceId } from './integrations/mercadopago/deviceId';
import type { CardPaymentOut, ClienteMpCardOut, PayerPortalOut } from './apiTypes';
import { formatBrl, formatDate } from './utils/format';
import { parseApiError } from './utils/apiError';
import { formatMercadoPagoStatusDetail } from './utils/mercadopagoStatusDetail';
import { mercadoPagoPayerEmail } from './utils/mercadopagoPayer';
import { resolveApiBase } from './utils/apiBase';
import ErrorBanner from './components/ErrorBanner';
import ReloadPrompt from './components/ReloadPrompt';

type PaymentMethodKind = 'pix' | 'credit_card' | 'debit_card';

const METHOD_LABELS: Record<PaymentMethodKind, string> = {
  pix: 'Pix',
  credit_card: 'Crédito',
  debit_card: 'Débito',
};

function portalTokenFromPath(): string | null {
  const m = window.location.pathname.match(/^\/pay\/([^/]+)\/?$/);
  return m?.[1] ?? null;
}

export default function PublicPayView() {
  const token = portalTokenFromPath();
  const apiBase = resolveApiBase(import.meta.env.VITE_API_BASE_URL);
  // useMemo garante uma única instância estável — novo render não recria o cliente HTTP
  const api = useMemo(() => axios.create({ baseURL: apiBase }), [apiBase]);

  const [checkout, setCheckout] = useState<PayerPortalOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [method, setMethod] = useState<PaymentMethodKind>('pix');
  const [pixCode, setPixCode] = useState('');
  const [pixLoading, setPixLoading] = useState(false);
  const [payLoading, setPayLoading] = useState(false);
  const [cardResult, setCardResult] = useState<CardPaymentOut | null>(null);
  const [copied, setCopied] = useState(false);
  const [polling, setPolling] = useState(false);
  const [paid, setPaid] = useState(false);
  const [savedCards, setSavedCards] = useState<ClienteMpCardOut[]>([]);
  const [selectedSavedId, setSelectedSavedId] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadCheckout = useCallback(async () => {
    if (!token) return;
    setError('');
    try {
      const [r, cardsRes] = await Promise.all([
        api.get<PayerPortalOut>(`/api/v1/public/pay/${token}`),
        api.get<ClienteMpCardOut[]>(`/api/v1/public/pay/${token}/cards`).catch(() => ({
          data: [] as ClienteMpCardOut[],
        })),
      ]);
      setCheckout(r.data);
      setSavedCards(cardsRes.data);
      const defaultCard = cardsRes.data.find((c) => c.is_default) ?? cardsRes.data[0];
      if (defaultCard) setSelectedSavedId(defaultCard.id);
      if (!r.data.payable) {
        setPaid(r.data.cobranca.status === 'recebido');
      }
      const pk = (r.data.mercadopago_public_key ?? '').trim();
      if (pk) initMercadoPagoSdk(pk);
      if (r.data.cobranca.pix_copia_cola) {
        setPixCode(r.data.cobranca.pix_copia_cola);
      }
    } catch (e) {
      setError(parseApiError(e, 'Link de pagamento inválido ou expirado'));
    } finally {
      setLoading(false);
    }
  }, [api, token]);

  useEffect(() => {
    void loadCheckout();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadCheckout]);

  const startPixPolling = () => {
    if (!token || pollRef.current) return;
    setPolling(true);
    pollRef.current = setInterval(() => {
      void (async () => {
        try {
          const r = await api.get<PayerPortalOut>(`/api/v1/public/pay/${token}`);
          if (!r.data.payable || r.data.cobranca.status === 'recebido') {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            setPolling(false);
            setPaid(true);
            setCheckout(r.data);
          }
        } catch {
          /* ignora */
        }
      })();
    }, 4000);
  };

  if (!token) {
    return (
      <div className="public-pay-page">
        <p>Link de pagamento inválido.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="public-pay-page">
        <p className="text-muted">Carregando pagamento…</p>
      </div>
    );
  }

  if (paid || (checkout && !checkout.payable && checkout.cobranca.status === 'recebido')) {
    return (
      <div className="public-pay-page">
        <div className="glass card public-pay-card">
          <Check size={48} color="var(--accent)" />
          <h2>Pagamento confirmado</h2>
          <p className="text-muted">Obrigado! Seu pagamento foi recebido.</p>
        </div>
      </div>
    );
  }

  if (!checkout) {
    return (
      <div className="public-pay-page">
        {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      </div>
    );
  }

  const cob = checkout.cobranca;
  const displayValor = cob.dias_atraso > 0 ? cob.valor_total : cob.valor;
  const cpfDigits = (checkout.cliente_cpf || '').replace(/\D/g, '');
  const credentialsMode =
    checkout.credentials_mode === 'test' ? ('test' as const) : ('production' as const);
  const payerEmail = mercadoPagoPayerEmail(
    checkout.cliente_id,
    credentialsMode,
    checkout.cliente_email
  );
  const payer = {
    email: payerEmail,
    identification: { type: 'CPF', number: cpfDigits },
  };

  const ensurePix = async () => {
    setPixLoading(true);
    setError('');
    try {
      const r = await api.post(`/api/v1/public/pay/${token}/pix`);
      setPixCode(r.data.pix_copia_cola ?? '');
      startPixPolling();
    } catch (e) {
      setError(parseApiError(e, 'Erro ao gerar Pix'));
    } finally {
      setPixLoading(false);
    }
  };

  const copyPix = async () => {
    if (!pixCode) return;
    try {
      await navigator.clipboard.writeText(pixCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const el = document.querySelector<HTMLTextAreaElement>('.pix-textarea');
      if (el) {
        el.select();
        el.setSelectionRange(0, 99999);
        const ok = document.execCommand('copy');
        if (ok) {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        } else {
          setError('Não foi possível copiar automaticamente. Selecione o código manualmente.');
        }
      } else {
        setError('Não foi possível copiar automaticamente. Selecione o código manualmente.');
      }
    }
    startPixPolling();
  };

  const payWithCard = async (data: {
    token: string;
    payment_method_id: string;
    installments: number;
  }) => {
    setPayLoading(true);
    setError('');
    try {
      const deviceId = await ensureMercadoPagoDeviceId();
      const body: Record<string, unknown> = {
        token: data.token,
        payment_method_id: data.payment_method_id,
        payment_method_kind: method,
        installments: data.installments,
        device_id: deviceId,
      };
      if (selectedSavedId != null) body.saved_card_id = selectedSavedId;
      const r = await api.post<CardPaymentOut>(`/api/v1/public/pay/${token}/card`, body);
      if (r.data.cobranca.status === 'recebido') {
        setCardResult(r.data);
        setPaid(true);
      } else if (r.data.requires_3ds && r.data.payment_id) {
        setCardResult(r.data);
      } else if (r.data.status === 'failed') {
        setCardResult(null);
        setError(formatMercadoPagoStatusDetail(r.data.status_detail));
      } else {
        setCardResult(r.data);
      }
    } catch (e) {
      setError(parseApiError(e, 'Erro ao processar cartão'));
    } finally {
      setPayLoading(false);
    }
  };

  const selectedCard = savedCards.find((c) => c.id === selectedSavedId);
  const showBrick =
    (method === 'credit_card' || method === 'debit_card') &&
    !cardResult?.requires_3ds &&
    !(cardResult && cardResult.cobranca.status === 'recebido');

  return (
    <>
    <ReloadPrompt />
    <div className="public-pay-page">
      <div className="glass card public-pay-card">
        <div className="public-pay-header">
          <Shield size={28} color="#6366f1" />
          <div>
            <h1>Pagamento</h1>
            <p className="text-muted">{checkout.cliente_nome}</p>
          </div>
        </div>

        {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

        <div className="pay-summary">
          <div>
            <span className="text-muted">Vencimento</span>
            <strong>{formatDate(cob.vencimento)}</strong>
          </div>
          <div>
            <span className="text-muted">Valor</span>
            <strong className="pay-amount">{formatBrl(displayValor)}</strong>
          </div>
        </div>

        {cob.dias_atraso > 0 && (
          <p className="late-fee text-muted">
            Multa {formatBrl(cob.multa)} · Juros {formatBrl(cob.juros)}
          </p>
        )}

        <div className="filter-tabs" style={{ marginBottom: 16 }}>
          {(['pix', 'credit_card', 'debit_card'] as PaymentMethodKind[]).map((m) => (
            <button
              key={m}
              type="button"
              className={`tab ${method === m ? 'active' : ''}`}
              onClick={() => {
                setMethod(m);
                setCardResult(null);
              }}
            >
              {METHOD_LABELS[m]}
            </button>
          ))}
        </div>

        {method === 'pix' && (
          <div>
            {!pixCode && (
              <button
                type="button"
                className="btn-primary"
                disabled={pixLoading}
                onClick={() => void ensurePix()}
              >
                {pixLoading ? 'Gerando…' : 'Gerar código Pix'}
              </button>
            )}
            {pixCode && (
              <div>
                <div className="pix-qr-wrap">
                  <QRCodeSVG
                    value={pixCode}
                    size={200}
                    bgColor="#14111a"
                    fgColor="#d4a574"
                    level="M"
                    style={{ borderRadius: 12, padding: 12, background: '#14111a', display: 'block', margin: '0 auto 16px' }}
                  />
                </div>
                <textarea className="input-field pix-textarea" readOnly rows={4} value={pixCode} />
                <button type="button" className="btn-secondary" onClick={() => void copyPix()}>
                  {copied ? <Check size={16} /> : <Copy size={16} />} Copiar Pix
                </button>
                {polling && (
                  <p className="text-muted" style={{ marginTop: 8, fontSize: '0.85rem' }}>
                    Aguardando confirmação do pagamento…
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {method !== 'pix' && savedCards.length > 0 && !cardResult?.requires_3ds && (
          <div style={{ marginBottom: 12 }}>
            <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 8 }}>
              Cartões salvos
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="savedCard"
                  checked={selectedSavedId === null}
                  onChange={() => setSelectedSavedId(null)}
                />
                Novo cartão
              </label>
              {savedCards.map((c) => (
                <label
                  key={c.id}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
                >
                  <input
                    type="radio"
                    name="savedCard"
                    checked={selectedSavedId === c.id}
                    onChange={() => setSelectedSavedId(c.id)}
                  />
                  <CreditCard size={14} />
                  {c.payment_method_id.toUpperCase()} •••• {c.last_four_digits}
                </label>
              ))}
            </div>
          </div>
        )}

        {showBrick && (
          <PaymentBrickCheckout
            amount={displayValor}
            payer={payer}
            mode={method}
            savedMpCardId={selectedCard?.mp_card_id}
            onSubmit={payWithCard}
          />
        )}

        {payLoading && <p className="text-muted">Processando pagamento…</p>}

        {cardResult?.requires_3ds && cardResult.payment_id && (
          <div style={{ marginTop: 12 }}>
            <p className="text-muted" style={{ marginBottom: 8 }}>
              Conclua a autenticação do banco:
            </p>
            <StatusScreenCheckout
              paymentId={cardResult.payment_id}
              externalResourceUrl={cardResult.three_ds_info?.external_resource_url}
              onComplete={() => {
                setPaid(true);
              }}
            />
          </div>
        )}
      </div>

      <style jsx>{`
        .public-pay-page {
          min-height: 100vh;
          min-height: 100dvh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          padding-top: calc(24px + env(safe-area-inset-top, 0px));
        }
        .public-pay-card {
          width: 100%;
          max-width: 520px;
          padding: 28px;
        }
        .public-pay-header {
          display: flex;
          align-items: center;
          gap: 14px;
          margin-bottom: 24px;
        }
        .public-pay-header h1 {
          font-size: 1.35rem;
          margin: 0;
        }
        .pay-summary {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-bottom: 20px;
          padding: 16px;
          background: rgba(255, 255, 255, 0.04);
          border-radius: 12px;
        }
        .pay-summary span {
          display: block;
          font-size: 0.8rem;
          margin-bottom: 4px;
        }
        .pay-amount {
          font-size: 1.25rem;
          color: var(--accent);
        }
        .late-fee {
          font-size: 0.85rem;
          margin-bottom: 16px;
        }
        .filter-tabs {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }
        .tab {
          background: none;
          border: 1px solid var(--glass-border);
          color: var(--text-muted);
          padding: 8px 14px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.85rem;
        }
        .tab.active {
          background: var(--primary-glow);
          color: var(--primary);
          border-color: var(--primary);
        }
        .btn-primary {
          width: 100%;
        }
        .btn-secondary {
          margin-top: 8px;
          width: 100%;
        }
      `}</style>
    </div>
    </>
  );
}
