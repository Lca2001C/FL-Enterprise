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
      customerId,
      cardsIds:
        savedMpCardId && customerId ? [savedMpCardId] : undefined,
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
        Carregando Mercado Pago…
      </p>
    );
  }

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
