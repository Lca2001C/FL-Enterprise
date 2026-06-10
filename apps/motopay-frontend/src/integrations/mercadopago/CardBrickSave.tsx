import { CardPayment } from '@mercadopago/sdk-react';
import { buildMercadoPagoBrickPayer } from '../../utils/mercadopagoPayer';

type Payer = {
  email: string;
  identification: { type: string; number: string };
};

type Props = {
  payer: Payer;
  onToken: (token: string) => void | Promise<void>;
};

export default function CardBrickSave({ payer, onToken }: Props) {
  return (
    <CardPayment
      initialization={{ amount: 1, payer: buildMercadoPagoBrickPayer(payer) }}
      customization={{}}
      onSubmit={async (formData) => {
        if (formData.token) await onToken(formData.token);
      }}
    />
  );
}
