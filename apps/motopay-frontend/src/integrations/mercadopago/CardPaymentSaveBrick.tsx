import { CardPayment } from '@mercadopago/sdk-react';
import { useMercadoPagoReady } from './useMercadoPagoReady';
import type { PaymentBrickPayer, PaymentBrickSubmitData } from './PaymentBrickCheckout';

type Props = {
  payer: PaymentBrickPayer;
  onSubmit: (data: PaymentBrickSubmitData) => Promise<void>;
  onError?: (error: unknown) => void;
};

/** Tokeniza cartão para salvar no cliente (sem cobrança). */
export default function CardPaymentSaveBrick({ payer, onSubmit, onError }: Props) {
  const ready = useMercadoPagoReady();
  if (!ready) {
    return (
      <p className="text-muted" style={{ fontSize: '0.9rem' }}>
        Carregando Mercado Pago…
      </p>
    );
  }

  return (
    <CardPayment
      initialization={{
        amount: 1,
        payer,
      }}
      onSubmit={async (param) => {
        const formData = (param as { formData?: Record<string, unknown> }).formData ?? param;
        await onSubmit({
          token: typeof formData.token === 'string' ? formData.token : undefined,
          payment_method_id:
            typeof formData.payment_method_id === 'string'
              ? formData.payment_method_id
              : undefined,
        });
      }}
      onError={(error) => onError?.(error)}
    />
  );
}
