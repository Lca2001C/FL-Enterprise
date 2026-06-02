import { Payment } from '@mercadopago/sdk-react';
import { useMercadoPagoReady } from './useMercadoPagoReady';
import type { PaymentMethodKind } from '../../utils/paymentMethods';

export type PaymentBrickPayer = {
  email: string;
  identification?: { type: string; number: string };
};

export type PaymentBrickSubmitData = {
  token?: string;
  installments?: number;
  payment_method_id?: string;
  issuer_id?: string;
};

type Props = {
  amount: number;
  payer: PaymentBrickPayer;
  cardMode: Extract<PaymentMethodKind, 'credit_card' | 'debit_card'>;
  onSubmit: (data: PaymentBrickSubmitData) => Promise<void>;
  onError?: (error: unknown) => void;
};

export default function PaymentBrickCheckout({
  amount,
  payer,
  cardMode,
  onSubmit,
  onError,
}: Props) {
  const ready = useMercadoPagoReady();
  if (!ready) {
    return (
      <p className="text-muted" style={{ fontSize: '0.9rem' }}>
        Carregando Mercado Pago…
      </p>
    );
  }

  const customization =
    cardMode === 'debit_card'
      ? {
          paymentMethods: {
            debitCard: 'all' as const,
            maxInstallments: 1,
          },
        }
      : {
          paymentMethods: {
            creditCard: 'all' as const,
            maxInstallments: 12,
          },
        };

  return (
    <Payment
      initialization={{
        amount,
        payer,
      }}
      customization={customization}
      onSubmit={async (param) => {
        const wrapped = param as unknown as { formData?: Record<string, unknown> };
        const formData: Record<string, unknown> =
          wrapped.formData ?? (param as unknown as Record<string, unknown>);
        await onSubmit({
          token: typeof formData.token === 'string' ? formData.token : undefined,
          installments:
            cardMode === 'debit_card'
              ? 1
              : typeof formData.installments === 'number'
                ? formData.installments
                : Number(formData.installments) || 1,
          payment_method_id:
            typeof formData.payment_method_id === 'string'
              ? formData.payment_method_id
              : undefined,
          issuer_id: typeof formData.issuer_id === 'string' ? formData.issuer_id : undefined,
        });
      }}
      onError={(error) => onError?.(error)}
    />
  );
}
