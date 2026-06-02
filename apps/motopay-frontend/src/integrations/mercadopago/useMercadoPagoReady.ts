import { isMercadoPagoSdkInitialized } from './init';

export function useMercadoPagoReady(): boolean {
  return isMercadoPagoSdkInitialized();
}
