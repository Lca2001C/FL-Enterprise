import { useEffect } from 'react';
import { StatusScreen } from '@mercadopago/sdk-react';

type Props = {
  paymentId: string;
  externalResourceUrl?: string | null;
  onComplete?: () => void;
};

export default function StatusScreenCheckout({
  paymentId,
  externalResourceUrl,
  onComplete,
}: Props) {
  useEffect(() => {
    if (!onComplete) return;
    const timer = window.setInterval(() => onComplete(), 5000);
    return () => window.clearInterval(timer);
  }, [onComplete]);

  if (externalResourceUrl) {
    return (
      <iframe
        src={externalResourceUrl}
        title="Autenticação 3DS"
        style={{ width: '100%', height: 420, border: 'none', borderRadius: 8 }}
      />
    );
  }

  return (
    <StatusScreen
      initialization={{ paymentId }}
      onReady={() => {
        /* brick carregado */
      }}
      onError={() => {
        /* erro exibido pelo brick */
      }}
    />
  );
}
