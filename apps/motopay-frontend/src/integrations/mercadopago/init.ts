import { initMercadoPago } from '@mercadopago/sdk-react';

let initialized = false;
let currentPublicKey = '';

export function initMercadoPagoSdk(publicKey: string): void {
  const key = publicKey.trim();
  if (!key) return;
  if (initialized && key === currentPublicKey) return;
  initMercadoPago(key);
  currentPublicKey = key;
  initialized = true;
}

export function getMercadoPagoSdkPublicKey(): boolean {
  return initialized;
}

export function getMercadoPagoCurrentPublicKey(): string {
  return currentPublicKey;
}
