<<<<<<< HEAD
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
=======
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Payment } from '@mercadopago/sdk-react';
import type { IPaymentBrickCustomization } from '@mercadopago/sdk-react/esm/bricks/payment/type';
import {
  buildMercadoPagoBrickPayer,
  normalizeBrickAmount,
  type MercadoPagoBrickPayer,
} from '../../utils/mercadopagoPayer';
import { getMercadoPagoSdkPublicKey, subscribeMercadoPagoSdkReady } from './init';

type Payer = Omit<MercadoPagoBrickPayer, 'entityType' | 'cardsIds'> & {
  identification: { type: string; number: string };
};

type SubmitPayload = {
  token: string;
  payment_method_id: string;
  installments: number;
};

type Props = {
  amount: number | string;
  payer: Payer;
  mode: 'credit_card' | 'debit_card';
  savedMpCardId?: string;
  onSubmit: (data: SubmitPayload) => void | Promise<void>;
};

function PaymentBrickCheckoutInner({
  amount,
  payer,
  mode,
  savedMpCardId,
  onSubmit,
}: Props) {
  const [sdkReady, setSdkReady] = useState(getMercadoPagoSdkPublicKey);
  const onSubmitRef = useRef(onSubmit);
  onSubmitRef.current = onSubmit;

  const brickAmount = useMemo(() => normalizeBrickAmount(amount), [amount]);
  const payerEmail = payer.email;
  const payerIdType = payer.identification.type;
  const payerIdNumber = payer.identification.number;
  const customerId = payer.customerId;

  useEffect(() => subscribeMercadoPagoSdkReady(() => setSdkReady(true)), []);

  const initialization = useMemo(() => {
    const payerInit = buildMercadoPagoBrickPayer({
      email: payerEmail,
      identification: { type: payerIdType, number: payerIdNumber },
      customerId: savedMpCardId && customerId ? customerId : undefined,
      cardsIds: savedMpCardId && customerId ? [savedMpCardId] : undefined,
    });
    return { amount: brickAmount, payer: payerInit };
  }, [brickAmount, payerEmail, payerIdType, payerIdNumber, customerId, savedMpCardId]);

  const customization: IPaymentBrickCustomization = useMemo(
    () => ({
      paymentMethods: {
        creditCard: mode === 'credit_card' ? 'all' : [],
        debitCard: mode === 'debit_card' ? 'all' : [],
        maxInstallments: mode === 'credit_card' ? 12 : 1,
      },
    }),
    [mode]
  );

  const handleSubmit = useCallback(async ({ formData }: { formData: unknown }) => {
    const raw = formData as Record<string, unknown>;
    const token = String(raw.token ?? '');
    const paymentMethodId = String(raw.payment_method_id ?? '');
    const installments = Number(raw.installments ?? 1);
    await onSubmitRef.current({
      token,
      payment_method_id: paymentMethodId,
      installments,
    });
  }, []);

  if (!sdkReady) {
    return (
      <p className="text-muted mp-brick-status">
>>>>>>> main
        Carregando Mercado Pago…
      </p>
    );
  }

<<<<<<< HEAD
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
=======
  if (brickAmount <= 0) {
    return (
      <p className="text-muted mp-brick-status">
        Valor inválido para pagamento.
      </p>
    );
  }

  return (
    <div className="mp-brick-container">
      <Payment
        key={`${mode}-${savedMpCardId ?? 'new'}`}
        locale="pt-BR"
        initialization={initialization}
        customization={customization}
        onSubmit={handleSubmit}
      />
    </div>
  );
}

const PaymentBrickCheckout = memo(PaymentBrickCheckoutInner);
export default PaymentBrickCheckout;
>>>>>>> main
