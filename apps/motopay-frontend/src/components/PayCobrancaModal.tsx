<<<<<<< HEAD
import { useEffect, useState } from 'react';
import { Copy, Check } from 'lucide-react';
import type { AxiosInstance } from 'axios';
import PaymentBrickCheckout from '../integrations/mercadopago/PaymentBrickCheckout';
import StatusScreenBrickView from '../integrations/mercadopago/StatusScreenBrickView';
=======
import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { createPortal } from 'react-dom';
import { Copy, Check, CreditCard } from 'lucide-react';
import type { AxiosInstance } from 'axios';
import PaymentBrickCheckout from '../integrations/mercadopago/PaymentBrickCheckout';
import StatusScreenCheckout from '../integrations/mercadopago/StatusScreenCheckout';
import { ensureMercadoPagoDeviceId } from '../integrations/mercadopago/deviceId';
>>>>>>> main
import type {
  CardPaymentOut,
  ClienteMpCardOut,
  ClienteOut,
  CobrancaOut,
  PaymentsConfig,
} from '../apiTypes';
import { formatBrl } from '../utils/format';
import { parseApiError } from '../utils/apiError';
<<<<<<< HEAD
import {
  filterSavedCardsByKind,
  type PaymentMethodKind,
  PAYMENT_METHOD_LABELS,
} from '../utils/paymentMethods';
import { mercadoPagoPayerEmail } from '../utils/mercadopagoPayer';
=======
import { mercadoPagoPayerEmail } from '../utils/mercadopagoPayer';
import { formatMercadoPagoStatusDetail } from '../utils/mercadopagoStatusDetail';

type PaymentMethodKind = 'pix' | 'credit_card' | 'debit_card';

const METHOD_LABELS: Record<PaymentMethodKind, string> = {
  pix: 'Pix',
  credit_card: 'Crédito',
  debit_card: 'Débito',
};
>>>>>>> main

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

<<<<<<< HEAD
const METHOD_TABS: PaymentMethodKind[] = ['pix', 'credit_card', 'debit_card'];

=======
>>>>>>> main
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
<<<<<<< HEAD
  const [selectedSavedCardId, setSelectedSavedCardId] = useState<number | ''>('');
  const [cardResult, setCardResult] = useState<CardPaymentOut | null>(null);
  const [copied, setCopied] = useState(false);
  const [credentialsMode, setCredentialsMode] = useState<'test' | 'production'>('production');
=======
  const [cardResult, setCardResult] = useState<CardPaymentOut | null>(null);
  const [copied, setCopied] = useState(false);
  const [credentialsMode, setCredentialsMode] = useState<'test' | 'production' | null>(null);
  const defaultCard = savedCards.find((c) => c.is_default) ?? savedCards[0];
  const [selectedSavedId, setSelectedSavedId] = useState<number | null>(null);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const payLoadingRef = useRef(payLoading);
  payLoadingRef.current = payLoading;

  useEffect(() => {
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, []);
>>>>>>> main

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

<<<<<<< HEAD
  const cpfDigits = (cpf: string) => cpf.replace(/\D/g, '');
  const payer = {
    email: mercadoPagoPayerEmail(cliente.id, credentialsMode),
    identification: { type: 'CPF', number: cpfDigits(cliente.cpf) },
  };

  const cardsForMethod =
    method === 'credit_card'
      ? filterSavedCardsByKind(savedCards, 'credit_card')
      : method === 'debit_card'
        ? filterSavedCardsByKind(savedCards, 'debit_card')
        : [];
=======
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

  const cpfDigits = useMemo(() => cliente.cpf.replace(/\D/g, ''), [cliente.cpf]);
  const payer = useMemo(() => {
    const mode = credentialsMode ?? 'production';
    return {
      email: mercadoPagoPayerEmail(cliente.id, mode, cliente.email),
      identification: { type: 'CPF', number: cpfDigits },
      ...(cliente.mercadopago_customer_id
        ? { customerId: cliente.mercadopago_customer_id }
        : {}),
    };
  }, [
    cliente.cpf,
    cliente.email,
    cliente.id,
    cliente.mercadopago_customer_id,
    cpfDigits,
    credentialsMode,
  ]);

  const selectedCard = savedCards.find((c) => c.id === selectedSavedId);
>>>>>>> main

  const ensurePix = async () => {
    setPixLoading(true);
    onError('');
    try {
      const r = await api.post<CobrancaOut>(`/api/v1/cobrancas/${cob.id}/pix`);
      setPixCode(r.data.pix_copia_cola ?? '');
<<<<<<< HEAD
=======
      startPixPolling();
>>>>>>> main
    } catch (e) {
      onError(parseApiError(e, 'Erro ao gerar Pix'));
    } finally {
      setPixLoading(false);
    }
  };

  const copyPix = async () => {
    if (!pixCode) return;
<<<<<<< HEAD
    await navigator.clipboard.writeText(pixCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const submitCard = async (data: {
    token?: string;
    installments?: number;
    payment_method_id?: string;
  }) => {
    setPayLoading(true);
    onError('');
    try {
      const body: Record<string, unknown> = {
        installments: data.installments ?? 1,
        payment_method_id: data.payment_method_id,
        payment_method_kind: method,
      };
      if (!data.token) {
        onError(
          selectedSavedCardId
            ? 'Informe o CVV no formulário abaixo para pagar com o cartão salvo.'
            : 'Preencha os dados do cartão no formulário.'
        );
        return;
      }
      body.token = data.token;
      if (selectedSavedCardId) {
        body.saved_card_id = selectedSavedCardId;
      }
      const r = await api.post<CardPaymentOut>(`/api/v1/cobrancas/${cob.id}/card-payment`, body);
      setCardResult(r.data);
      if (r.data.cobranca_finalizada) {
        onPaid();
      }
    } catch (e) {
      onError(parseApiError(e, 'Erro ao processar pagamento'));
    } finally {
      setPayLoading(false);
    }
  };

  if (cardResult) {
    return (
      <div className="modal-overlay">
        <div className="glass modal-content animate-fade" style={{ maxWidth: 520 }}>
          <h3>Pagamento — Cobrança #{cob.id}</h3>
          <p style={{ fontSize: '0.9rem', marginBottom: 12 }}>
            Status: <strong>{cardResult.status}</strong>
            {cardResult.status_detail && (
              <span className="text-muted"> ({cardResult.status_detail})</span>
            )}
          </p>
          <StatusScreenBrickView
            paymentId={cardResult.payment_id}
            threeDsInfo={cardResult.three_ds_info}
          />
          <div className="modal-actions" style={{ marginTop: 20 }}>
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                onClose();
                onPaid();
              }}
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay">
      <div className="glass modal-content animate-fade" style={{ maxWidth: 540 }}>
        <h3>Pagar cobrança #{cob.id}</h3>
        <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 16 }}>
          {cliente.nome} · Total {formatBrl(displayValor)}
        </p>

        <div className="filter-tabs" style={{ marginBottom: 20, padding: '8px 10px' }}>
          {METHOD_TABS.map((m) => (
=======
    try {
      await navigator.clipboard.writeText(pixCode);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = pixCode;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    if (!pollRef.current) startPixPolling();
  };

  const methodRef = useRef(method);
  methodRef.current = method;
  const selectedSavedIdRef = useRef(selectedSavedId);
  selectedSavedIdRef.current = selectedSavedId;

  const payWithCard = useCallback(
    async (data: {
      token: string;
      payment_method_id: string;
      installments: number;
    }) => {
      setPayLoading(true);
      onError('');
      try {
        const deviceId = await ensureMercadoPagoDeviceId();
        const body: Record<string, unknown> = {
          token: data.token,
          payment_method_id: data.payment_method_id,
          payment_method_kind: methodRef.current,
          installments: data.installments,
          device_id: deviceId,
        };
        const savedId = selectedSavedIdRef.current;
        if (savedId != null) {
          body.saved_card_id = savedId;
        }
        const r = await api.post<CardPaymentOut>(`/api/v1/cobrancas/${cob.id}/card`, body);
        if (r.data.cobranca.status === 'recebido') {
          setCardResult(r.data);
          onPaid();
        } else if (r.data.requires_3ds && r.data.payment_id) {
          setCardResult(r.data);
        } else if (r.data.status === 'failed') {
          setCardResult(null);
          onError(formatMercadoPagoStatusDetail(r.data.status_detail));
        } else {
          setCardResult(r.data);
        }
      } catch (e) {
        onError(parseApiError(e, 'Erro ao processar cartão'));
      } finally {
        setPayLoading(false);
      }
    },
    [api, cob.id, onError, onPaid]
  );

  const on3dsComplete = async () => {
    try {
      const r = await api.get<CobrancaOut>(`/api/v1/cobrancas/${cob.id}`);
      if (r.data.status === 'recebido') onPaid();
    } catch {
      onError('Pagamento em processamento — atualize a lista em instantes.');
    }
  };

  const showBrick =
    credentialsMode != null &&
    (method === 'credit_card' || method === 'debit_card') &&
    !cardResult?.requires_3ds &&
    !(cardResult && cardResult.cobranca.status === 'recebido');

  const overlayLocked = showBrick || payLoading || polling || Boolean(cardResult?.requires_3ds);

  const handleOverlayClick = (e: MouseEvent<HTMLDivElement>) => {
    if (overlayLocked) return;
    if (e.target !== e.currentTarget) return;
    onClose();
  };

  const modalUi = (
    <div
      className={`modal-overlay${overlayLocked ? ' modal-overlay--locked' : ''}`}
      onClick={overlayLocked ? undefined : handleOverlayClick}
      role="presentation"
    >
      <div
        className="glass modal-content modal-content--wide modal--payment animate-fade"
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
      >
        <h3>Pagar cobrança #{cob.id}</h3>
        <p className="text-muted">Valor: {formatBrl(displayValor)}</p>

        <div className="filter-tabs" style={{ marginBottom: 16 }}>
          {(['pix', 'credit_card', 'debit_card'] as PaymentMethodKind[]).map((m) => (
>>>>>>> main
            <button
              key={m}
              type="button"
              className={`tab ${method === m ? 'active' : ''}`}
              onClick={() => {
                setMethod(m);
<<<<<<< HEAD
                setSelectedSavedCardId('');
              }}
            >
              {PAYMENT_METHOD_LABELS[m]}
=======
                setCardResult(null);
                if (m === 'pix') {
                  setSelectedSavedId(null);
                } else if (defaultCard) {
                  setSelectedSavedId(defaultCard.id);
                } else {
                  setSelectedSavedId(null);
                }
              }}
            >
              {METHOD_LABELS[m]}
>>>>>>> main
            </button>
          ))}
        </div>

        {method === 'pix' && (
          <div>
            {!pixCode && (
<<<<<<< HEAD
              <button
                type="button"
                className="btn-primary"
                disabled={pixLoading}
                onClick={() => void ensurePix()}
              >
                {pixLoading ? 'Gerando Pix…' : 'Gerar código Pix'}
=======
              <button type="button" className="btn-primary" disabled={pixLoading} onClick={() => void ensurePix()}>
                {pixLoading ? 'Gerando…' : 'Gerar código Pix'}
>>>>>>> main
              </button>
            )}
            {pixCode && (
              <div>
<<<<<<< HEAD
                <label className="input-label">Pix copia e cola</label>
                <textarea
                  className="input-field"
                  readOnly
                  rows={4}
                  value={pixCode}
                  style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
                />
                <button
                  type="button"
                  className="btn-secondary"
                  style={{ marginTop: 8 }}
                  onClick={() => void copyPix()}
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                  {copied ? ' Copiado' : ' Copiar código'}
                </button>
                <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: 12 }}>
                  Após o pagamento, a confirmação chega automaticamente via webhook Mercado Pago.
                </p>
              </div>
            )}
          </div>
        )}

        {(method === 'credit_card' || method === 'debit_card') && (
          <div>
            {cardsForMethod.length > 0 && (
              <div className="input-group">
                <label className="input-label">Cartão salvo (opcional)</label>
                <select
                  className="input-field"
                  value={selectedSavedCardId}
                  onChange={(e) =>
                    setSelectedSavedCardId(e.target.value ? parseInt(e.target.value, 10) : '')
                  }
                >
                  <option value="">Novo cartão</option>
                  {cardsForMethod.map((card) => (
                    <option key={card.id} value={card.id}>
                      •••• {card.last_four_digits} ({card.payment_method_id})
                    </option>
                  ))}
                </select>
                {selectedSavedCardId ? (
                  <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: 8 }}>
                    Informe o CVV no formulário abaixo para usar o cartão salvo.
                  </p>
                ) : null}
              </div>
            )}
            <PaymentBrickCheckout
              amount={displayValor}
              payer={payer}
              cardMode={method}
              onSubmit={submitCard}
            />
            {payLoading && (
              <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: 8 }}>
                Processando pagamento…
              </p>
            )}
          </div>
        )}

        <div className="modal-actions" style={{ marginTop: 20 }}>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
=======
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

        {!overlayLocked && (
          <button
            type="button"
            className="btn-secondary"
            style={{ marginTop: 16 }}
            disabled={payLoading}
            onClick={onClose}
          >
            Fechar
          </button>
        )}
      </div>
    </div>
  );

  return createPortal(modalUi, document.body);
>>>>>>> main
}
