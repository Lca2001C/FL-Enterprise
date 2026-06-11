import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { CreditCard, Trash2 } from 'lucide-react';
import type { AxiosInstance } from 'axios';
import type { ClienteMpCardOut, ClienteOut, PaymentsConfig } from '../apiTypes';
import { parseApiError } from '../utils/apiError';
import { mercadoPagoPayerEmail } from '../utils/mercadopagoPayer';
import CardSecureFieldsSave from '../integrations/mercadopago/CardSecureFieldsSave';
import {
  getMercadoPagoSdkPublicKey,
  initMercadoPagoSdk,
} from '../integrations/mercadopago/init';

type Props = {
  cliente: ClienteOut;
  api: AxiosInstance;
  onClose: () => void;
  onError: (message: string) => void;
};

export default function ClientMpCardsModal({ cliente, api, onClose, onError }: Props) {
  const [cards, setCards] = useState<ClienteMpCardOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showCardForm, setShowCardForm] = useState(false);
  const [formSession, setFormSession] = useState(0);
  const [formError, setFormError] = useState('');
  const [credentialsMode, setCredentialsMode] = useState<'test' | 'production' | null>(null);
  const [mpConfigured, setMpConfigured] = useState(false);
  const onErrorRef = useRef(onError);
  const showCardFormRef = useRef(showCardForm);
  onErrorRef.current = onError;
  showCardFormRef.current = showCardForm;

  useEffect(() => {
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, []);

  const load = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      onErrorRef.current('');
      try {
        const [cardsRes, cfgRes] = await Promise.allSettled([
          api.get<ClienteMpCardOut[]>(`/api/v1/clientes/${cliente.id}/mp-cards`),
          api.get<PaymentsConfig>('/api/v1/config/payments'),
        ]);
        if (cardsRes.status === 'fulfilled') {
          setCards(cardsRes.value.data);
        } else {
          setCards([]);
          onErrorRef.current(parseApiError(cardsRes.reason, 'Erro ao carregar cartões'));
        }
        if (cfgRes.status === 'fulfilled') {
          setCredentialsMode(cfgRes.value.data.credentials_mode);
          setMpConfigured(cfgRes.value.data.mercadopago_credentials_complete);
        } else {
          onErrorRef.current(parseApiError(cfgRes.reason, 'Erro ao carregar Mercado Pago'));
        }
      } catch (e) {
        onErrorRef.current(parseApiError(e, 'Erro ao carregar cartões'));
      } finally {
        if (!silent) setLoading(false);
      }
    },
    [api, cliente.id]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const payer = useMemo(() => {
    if (credentialsMode == null) return null;
    const cpfDigits = cliente.cpf.replace(/\D/g, '');
    return {
      email: mercadoPagoPayerEmail(cliente.id, credentialsMode, cliente.email),
      identification: { type: 'CPF', number: cpfDigits },
    };
  }, [cliente.cpf, cliente.email, cliente.id, credentialsMode]);

  const saveCard = useCallback(
    async (token: string) => {
      setSaving(true);
      onErrorRef.current('');
      setFormError('');
      try {
        await api.post(`/api/v1/clientes/${cliente.id}/mp-cards`, { token });
        setShowCardForm(false);
        await load(true);
      } catch (e) {
        onErrorRef.current(parseApiError(e, 'Erro ao salvar cartão'));
      } finally {
        setSaving(false);
      }
    },
    [api, cliente.id, load]
  );

  const removeCard = async (cardId: number) => {
    if (!confirm('Remover este cartão?')) return;
    onErrorRef.current('');
    try {
      await api.delete(`/api/v1/clientes/${cliente.id}/mp-cards/${cardId}`);
      await load(showCardFormRef.current);
    } catch (e) {
      onErrorRef.current(parseApiError(e, 'Erro ao remover cartão'));
    }
  };

  const openCardForm = () => {
    void (async () => {
      setFormError('');
      if (!getMercadoPagoSdkPublicKey()) {
        try {
          const cfg = await api.get<PaymentsConfig>('/api/v1/config/payments');
          const key = (cfg.data.mercadopago_public_key ?? '').trim();
          if (key) {
            initMercadoPagoSdk(key);
          } else {
            onErrorRef.current('Public key do Mercado Pago não configurada em Ajustes.');
            return;
          }
        } catch (e) {
          onErrorRef.current(parseApiError(e, 'Erro ao carregar Mercado Pago'));
          return;
        }
      }
      setFormSession((n) => n + 1);
      setShowCardForm(true);
    })();
  };

  const retryForm = () => {
    setFormError('');
    setFormSession((n) => n + 1);
  };

  const handleOverlayClick = () => {
    if (showCardForm || saving) return;
    onClose();
  };

  const modalUi = (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div
        className={`glass modal-content modal-content--wide modal--payment animate-fade${showCardForm ? ' modal--card-form-open' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        <h3>Cartões — {cliente.nome}</h3>

        {loading && !showCardForm && <p className="text-muted">Carregando…</p>}

        {!loading && !mpConfigured && (
          <p className="text-muted">
            Configure Mercado Pago (token, public key e webhook secret) em Ajustes.
          </p>
        )}

        {!loading && cards.length > 0 && (
          <ul className="mp-cards-list">
            {cards.map((c) => (
              <li key={c.id} className="mp-cards-list-item">
                <span className="mp-cards-list-item__info">
                  <CreditCard size={16} />
                  {c.payment_method_id.toUpperCase()} •••• {c.last_four_digits}
                  {c.is_default && (
                    <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                      (padrão)
                    </span>
                  )}
                </span>
                <span className="mp-cards-list-item__actions">
                  {!c.is_default && (
                    <button
                      type="button"
                      className="icon-btn"
                      title="Definir como padrão"
                      onClick={() =>
                        void api
                          .post(`/api/v1/clientes/${cliente.id}/mp-cards/${c.id}/default`)
                          .then(() => load(showCardFormRef.current))
                      }
                    >
                      Padrão
                    </button>
                  )}
                  <button
                    type="button"
                    className="icon-btn danger"
                    title="Remover"
                    onClick={() => void removeCard(c.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}

        {!loading && mpConfigured && !showCardForm && (
          <button type="button" className="btn-primary" onClick={openCardForm}>
            Adicionar cartão
          </button>
        )}

        {showCardForm && payer && (
          <div className="mp-card-form-section">
            <CardSecureFieldsSave
              key={formSession}
              payer={payer}
              onToken={saveCard}
              onFieldError={setFormError}
            />
            {formError && (
              <div className="mp-card-form-actions">
                <p style={{ color: 'var(--warning)', fontSize: '0.85rem', margin: 0 }}>
                  {formError}
                </p>
                <button type="button" className="btn-primary" disabled={saving} onClick={retryForm}>
                  Tentar novamente
                </button>
              </div>
            )}
            <div className="mp-card-form-actions">
              <button
                type="button"
                className="btn-secondary"
                disabled={saving}
                onClick={() => {
                  setShowCardForm(false);
                  setFormError('');
                }}
              >
                Cancelar cadastro
              </button>
            </div>
          </div>
        )}

        <div className="mp-card-form-actions" style={{ marginTop: 16 }}>
          <button type="button" className="btn-secondary" disabled={saving} onClick={onClose}>
            Fechar
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalUi, document.body);
}
