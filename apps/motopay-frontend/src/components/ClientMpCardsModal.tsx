import { useCallback, useEffect, useState } from 'react';
import { CreditCard, Trash2 } from 'lucide-react';
import type { AxiosInstance } from 'axios';
import type { ClienteMpCardOut, ClienteOut, PaymentsConfig } from '../apiTypes';
import { parseApiError } from '../utils/apiError';
import { mercadoPagoPayerEmail } from '../utils/mercadopagoPayer';
import CardBrickSave from '../integrations/mercadopago/CardBrickSave';
import { getMercadoPagoSdkPublicKey } from '../integrations/mercadopago/init';

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
  const [showBrick, setShowBrick] = useState(false);
  const [credentialsMode, setCredentialsMode] = useState<'test' | 'production'>('production');
  const [mpConfigured, setMpConfigured] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    onError('');
    try {
      const [cardsRes, cfgRes] = await Promise.all([
        api.get<ClienteMpCardOut[]>(`/api/v1/clientes/${cliente.id}/mp-cards`),
        api.get<PaymentsConfig>('/api/v1/config/payments'),
      ]);
      setCards(cardsRes.data);
      setCredentialsMode(cfgRes.data.credentials_mode);
      setMpConfigured(cfgRes.data.mercadopago_credentials_complete);
    } catch (e) {
      onError(parseApiError(e, 'Erro ao carregar cartões'));
    } finally {
      setLoading(false);
    }
  }, [api, cliente.id, onError]);

  useEffect(() => {
    void load();
  }, [load]);

  const cpfDigits = (cpf: string) => cpf.replace(/\D/g, '');
  const payer = {
    email: mercadoPagoPayerEmail(cliente.id, credentialsMode, cliente.email),
    identification: { type: 'CPF', number: cpfDigits(cliente.cpf) },
  };

  const saveCard = async (token: string) => {
    setSaving(true);
    onError('');
    try {
      await api.post(`/api/v1/clientes/${cliente.id}/mp-cards`, { token });
      setShowBrick(false);
      await load();
    } catch (e) {
      onError(parseApiError(e, 'Erro ao salvar cartão'));
    } finally {
      setSaving(false);
    }
  };

  const removeCard = async (cardId: number) => {
    if (!confirm('Remover este cartão?')) return;
    onError('');
    try {
      await api.delete(`/api/v1/clientes/${cliente.id}/mp-cards/${cardId}`);
      await load();
    } catch (e) {
      onError(parseApiError(e, 'Erro ao remover cartão'));
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal glass" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
        <h3>Cartões — {cliente.nome}</h3>

        {loading && <p className="text-muted">Carregando…</p>}

        {!loading && !mpConfigured && (
          <p className="text-muted">
            Configure Mercado Pago (token, public key e webhook secret) em Ajustes.
          </p>
        )}

        {!loading && cards.length > 0 && (
          <ul style={{ listStyle: 'none', padding: 0, margin: '12px 0' }}>
            {cards.map((c) => (
              <li
                key={c.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 0',
                  borderBottom: '1px solid var(--glass-border)',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CreditCard size={16} />
                  {c.payment_method_id.toUpperCase()} •••• {c.last_four_digits}
                  {c.is_default && (
                    <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                      (padrão)
                    </span>
                  )}
                </span>
                <span style={{ display: 'flex', gap: 4 }}>
                  {!c.is_default && (
                    <button
                      type="button"
                      className="icon-btn"
                      title="Definir como padrão"
                      onClick={() =>
                        void api
                          .post(`/api/v1/clientes/${cliente.id}/mp-cards/${c.id}/default`)
                          .then(() => load())
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

        {!loading && mpConfigured && !showBrick && (
          <button
            type="button"
            className="btn-primary"
            disabled={!getMercadoPagoSdkPublicKey()}
            onClick={() => setShowBrick(true)}
          >
            Adicionar cartão
          </button>
        )}

        {showBrick && (
          <div style={{ marginTop: 12 }}>
            <CardBrickSave payer={payer} onToken={saveCard} />
            {saving && <p className="text-muted">Salvando…</p>}
          </div>
        )}

        <button type="button" className="btn-secondary" style={{ marginTop: 16 }} onClick={onClose}>
          Fechar
        </button>
      </div>
    </div>
  );
}
