import { useEffect, useRef, useState } from 'react';
import { Copy, Check, CreditCard } from 'lucide-react';
import type { AxiosInstance } from 'axios';
import PaymentBrickCheckout from '../integrations/mercadopago/PaymentBrickCheckout';
import StatusScreenCheckout from '../integrations/mercadopago/StatusScreenCheckout';
import type {
  CardPaymentOut,
  ClienteMpCardOut,
  ClienteOut,
  CobrancaOut,
  PaymentsConfig,
} from '../apiTypes';
import { formatBrl } from '../utils/format';
import { parseApiError } from '../utils/apiError';
import { mercadoPagoPayerEmail } from '../utils/mercadopagoPayer';

type PaymentMethodKind = 'pix' | 'credit_card' | 'debit_card';

const METHOD_LABELS: Record<PaymentMethodKind, string> = {
  pix: 'Pix',
  credit_card: 'Crédito',
  debit_card: 'Débito',
};

type Props = {
  cob: CobrancaOut;
  cliente: ClienteOut;
  savedCards: ClienteMpCardOut[];
  api: AxiosInstance;
  displayValor: number;
  onClose: () => void;
  onPaid: () => void;
  onError: (message: string) => void;
};

export default function PayCobrancaModal({
  cob,
  cliente,
  savedCards,
  api,
  displayValor,
  onClose,
  onPaid,
  onError,
}: Props) {
  const [method, setMethod] = useState<PaymentMethodKind>('pix');
  const [pixCode, setPixCode] = useState(cob.pix_copia_cola ?? '');
  const [pixLoading, setPixLoading] = useState(false);
  const [payLoading, setPayLoading] = useState(false);
  const [cardResult, setCardResult] = useState<CardPaymentOut | null>(null);
  const [copied, setCopied] = useState(false);
  const [credentialsMode, setCredentialsMode] = useState<'test' | 'production'>('production');
  const defaultCard = savedCards.find((c) => c.is_default) ?? savedCards[0];
  const [selectedSavedId, setSelectedSavedId] = useState<number | null>(null);
  const [cardChoiceInit, setCardChoiceInit] = useState(false);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const r = await api.get<PaymentsConfig>('/api/v1/config/payments');
        setCredentialsMode(r.data.credentials_mode);
      } catch {
        /* mantém production */
      }
    })();
  }, [api]);

  useEffect(() => {
    if (!cardChoiceInit && defaultCard && method !== 'pix') {
      setSelectedSavedId(defaultCard.id);
      setCardChoiceInit(true);
    }
  }, [cardChoiceInit, defaultCard, method]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const startPixPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setPolling(true);
    pollRef.current = setInterval(() => {
      void (async () => {
        try {
          const r = await api.get<CobrancaOut>(`/api/v1/cobrancas/${cob.id}`);
          if (r.data.status === 'recebido') {
            if (pollRef.current) clearInterval(pollRef.current);
            setPolling(false);
            onPaid();
          }
        } catch {
          /* ignora falhas temporárias */
        }
      })();
    }, 4000);
  };

  const cpfDigits = (cpf: string) => cpf.replace(/\D/g, '');
  const payerEmail = mercadoPagoPayerEmail(cliente.id, credentialsMode, cliente.email);
  const payer = {
    email: payerEmail,
    identification: { type: 'CPF', number: cpfDigits(cliente.cpf) },
    ...(cliente.mercadopago_customer_id
      ? { customerId: cliente.mercadopago_customer_id }
      : {}),
  };

  const selectedCard = savedCards.find((c) => c.id === selectedSavedId);

  const ensurePix = async () => {
    setPixLoading(true);
    onError('');
    try {
      const r = await api.post<CobrancaOut>(`/api/v1/cobrancas/${cob.id}/pix`);
      setPixCode(r.data.pix_copia_cola ?? '');
      startPixPolling();
    } catch (e) {
      onError(parseApiError(e, 'Erro ao gerar Pix'));
    } finally {
      setPixLoading(false);
    }
  };

  const copyPix = async () => {
    if (!pixCode) return;
    await navigator.clipboard.writeText(pixCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    if (!pollRef.current) startPixPolling();
  };

  const payWithCard = async (data: {
    token: string;
    payment_method_id: string;
    installments: number;
  }) => {
    setPayLoading(true);
    onError('');
    try {
      const body: Record<string, unknown> = {
        token: data.token,
        payment_method_id: data.payment_method_id,
        payment_method_kind: method,
        installments: data.installments,
      };
      if (selectedSavedId != null) {
        body.saved_card_id = selectedSavedId;
      }
      const r = await api.post<CardPaymentOut>(`/api/v1/cobrancas/${cob.id}/card`, body);
      setCardResult(r.data);
      if (r.data.cobranca.status === 'recebido') {
        onPaid();
      } else if (r.data.requires_3ds && r.data.payment_id) {
        /* Status Screen assume confirmação */
      }
    } catch (e) {
      onError(parseApiError(e, 'Erro ao processar cartão'));
    } finally {
      setPayLoading(false);
    }
  };

  const on3dsComplete = async () => {
    try {
      const r = await api.get<CobrancaOut>(`/api/v1/cobrancas/${cob.id}`);
      if (r.data.status === 'recebido') onPaid();
    } catch {
      onError('Pagamento em processamento — atualize a lista em instantes.');
    }
  };

  const showBrick =
    (method === 'credit_card' || method === 'debit_card') &&
    !cardResult?.requires_3ds &&
    !(cardResult && cardResult.cobranca.status === 'recebido');

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal glass" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
        <h3>Pagar cobrança #{cob.id}</h3>
        <p className="text-muted">Valor: {formatBrl(displayValor)}</p>

        <div className="filter-tabs" style={{ marginBottom: 16 }}>
          {(['pix', 'credit_card', 'debit_card'] as PaymentMethodKind[]).map((m) => (
            <button
              key={m}
              type="button"
              className={`tab ${method === m ? 'active' : ''}`}
              onClick={() => {
                setMethod(m);
                setSelectedSavedId(null);
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
              <button type="button" className="btn-primary" disabled={pixLoading} onClick={() => void ensurePix()}>
                {pixLoading ? 'Gerando…' : 'Gerar código Pix'}
              </button>
            )}
            {pixCode && (
              <div>
                <textarea className="input-field" readOnly rows={4} value={pixCode} />
                <button type="button" className="btn-secondary" onClick={() => void copyPix()}>
                  {copied ? <Check size={16} /> : <Copy size={16} />} Copiar
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
              onComplete={() => void on3dsComplete()}
            />
          </div>
        )}

        {cardResult && !cardResult.requires_3ds && cardResult.cobranca.status !== 'recebido' && (
          <p>
            Status: <strong>{cardResult.status}</strong>
          </p>
        )}

        <button type="button" className="btn-secondary" style={{ marginTop: 16 }} onClick={onClose}>
          Fechar
        </button>
      </div>
    </div>
  );
}
