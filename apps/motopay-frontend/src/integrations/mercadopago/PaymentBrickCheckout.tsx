import { Payment } from '@mercadopago/sdk-react';
import type { IPaymentBrickCustomization } from '@mercadopago/sdk-react/esm/bricks/payment/type';

type Payer = {
  email: string;
  identification: { type: string; number: string };
  customerId?: string;
};

type Props = {
  amount: number;
  payer: Payer;
  mode: 'credit_card' | 'debit_card';
  savedMpCardId?: string;
  onSubmit: (data: {
    token: string;
    payment_method_id: string;
    installments: number;
  }) => void | Promise<void>;
};

export default function PaymentBrickCheckout({
  amount,
  payer,
  mode,
  savedMpCardId,
  onSubmit,
}: Props) {
  const customization: IPaymentBrickCustomization = {
    paymentMethods: {
      creditCard: mode === 'credit_card' ? 'all' : [],
      debitCard: mode === 'debit_card' ? 'all' : [],
      maxInstallments: mode === 'credit_card' ? 12 : 1,
    },
  };

  const initialization: {
    amount: number;
    payer: Payer & { cardsIds?: string[] };
  } = {
    amount,
    payer: { ...payer },
  };
  if (savedMpCardId && payer.customerId) {
    initialization.payer.cardsIds = [savedMpCardId];
  }

  return (
    <Payment
      initialization={initialization}
      customization={customization}
      onSubmit={async ({ formData }) => {
        const raw = formData as unknown as Record<string, unknown>;
        const token = String(raw.token ?? '');
        const paymentMethodId = String(raw.payment_method_id ?? '');
        const installments = Number(raw.installments ?? 1);
        await onSubmit({ token, payment_method_id: paymentMethodId, installments });
      }}
    />
  );
}
