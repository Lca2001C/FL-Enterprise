import { useEffect, useState } from 'react';
import { Copy, Check } from 'lucide-react';
import type { AxiosInstance } from 'axios';
import PaymentBrickCheckout from '../integrations/mercadopago/PaymentBrickCheckout';
import StatusScreenBrickView from '../integrations/mercadopago/StatusScreenBrickView';
import type {
  CardPaymentOut,
  ClienteMpCardOut,
  ClienteOut,
  CobrancaOut,
  PaymentsConfig,
} from '../apiTypes';
import { formatBrl } from '../utils/format';
import { parseApiError } from '../utils/apiError';
import {
  filterSavedCardsByKind,
  type PaymentMethodKind,
  PAYMENT_METHOD_LABELS,
} from '../utils/paymentMethods';
import { mercadoPagoPayerEmail } from '../utils/mercadopagoPayer';

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

const METHOD_TABS: PaymentMethodKind[] = ['pix', 'credit_card', 'debit_card'];

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
  const [selectedSavedCardId, setSelectedSavedCardId] = useState<number | ''>('');
  const [cardResult, setCardResult] = useState<CardPaymentOut | null>(null);
  const [copied, setCopied] = useState(false);
  const [credentialsMode, setCredentialsMode] = useState<'test' | 'production'>('production');

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

  const ensurePix = async () => {
    setPixLoading(true);
    onError('');
    try {
      const r = await api.post<CobrancaOut>(`/api/v1/cobrancas/${cob.id}/pix`);
      setPixCode(r.data.pix_copia_cola ?? '');
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
            <button
              key={m}
              type="button"
              className={`tab ${method === m ? 'active' : ''}`}
              onClick={() => {
                setMethod(m);
                setSelectedSavedCardId('');
              }}
            >
              {PAYMENT_METHOD_LABELS[m]}
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
                {pixLoading ? 'Gerando Pix…' : 'Gerar código Pix'}
              </button>
            )}
            {pixCode && (
              <div>
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
}
