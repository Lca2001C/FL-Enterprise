import { useEffect } from 'react';
import { StatusScreen } from '@mercadopago/sdk-react';

type Props = {
  paymentId: string;
  externalResourceUrl?: string | null;
  onComplete?: () => void;
  /** Quando true, interrompe o polling de 5s (pagamento já confirmado). */
  paid?: boolean;
};

export default function StatusScreenCheckout({
  paymentId,
  externalResourceUrl,
  onComplete,
  paid,
}: Props) {
  useEffect(() => {
    if (!onComplete || paid) return;
    const timer = window.setInterval(() => onComplete(), 5000);
    return () => window.clearInterval(timer);
  }, [onComplete, paid]);

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
