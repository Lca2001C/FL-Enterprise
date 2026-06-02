import { StatusScreen } from '@mercadopago/sdk-react';
import { useMercadoPagoReady } from './useMercadoPagoReady';
import type { ThreeDsInfo } from '../../apiTypes';

type Props = {
  paymentId: string;
  threeDsInfo?: ThreeDsInfo | null;
  onError?: (error: unknown) => void;
};

export function buildStatusScreenInitialization(
  paymentId: string,
  threeDsInfo?: ThreeDsInfo | null
) {
  const additionalInfo =
    threeDsInfo?.external_resource_url && threeDsInfo?.creq
      ? {
          externalResourceURL: threeDsInfo.external_resource_url,
          creq: threeDsInfo.creq,
        }
      : undefined;
  return {
    paymentId,
    ...(additionalInfo ? { additionalInfo } : {}),
  };
}

export default function StatusScreenBrickView({ paymentId, threeDsInfo, onError }: Props) {
  const ready = useMercadoPagoReady();
  if (!ready || !paymentId) {
    return null;
  }

  return (
    <StatusScreen
      key={paymentId}
      initialization={buildStatusScreenInitialization(paymentId, threeDsInfo)}
      onError={(error) => onError?.(error)}
    />
  );
}
