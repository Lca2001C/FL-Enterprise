import { useEffect, type ReactNode } from 'react';
import { useAuth } from '../../AuthContext';
import type { PaymentsConfig } from '../../apiTypes';
import { getMercadoPagoSdkPublicKey, initMercadoPagoSdk } from './init';

type Props = { children: ReactNode };

function envPublicKey(): string {
  const key = import.meta.env.VITE_MERCADOPAGO_PUBLIC_KEY;
  return typeof key === 'string' ? key.trim() : '';
}

export function MercadoPagoProvider({ children }: Props) {
  const { token, api, operacaoScopeId, user } = useAuth();

  useEffect(() => {
    if (!token) return;

    const run = async () => {
      const fromEnv = envPublicKey();
      if (fromEnv) {
        initMercadoPagoSdk(fromEnv);
        return;
      }

      try {
        const params =
          user?.tipo === 'admin' && operacaoScopeId != null
            ? { operacao_id: operacaoScopeId }
            : undefined;
        const r = await api.get<PaymentsConfig>('/api/v1/config/payments', { params });
        const key = (r.data.mercadopago_public_key ?? '').trim();
        if (key) {
          initMercadoPagoSdk(key);
        } else if (import.meta.env.DEV) {
          console.debug('[MercadoPago] Public key ausente; SDK não inicializado.');
        }
      } catch {
        if (import.meta.env.DEV) {
          console.debug('[MercadoPago] Falha ao carregar config de pagamentos.');
        }
      }
    };

    void run();
  }, [token, api, operacaoScopeId, user?.tipo]);

  return <>{children}</>;
}

export { getMercadoPagoSdkPublicKey };
