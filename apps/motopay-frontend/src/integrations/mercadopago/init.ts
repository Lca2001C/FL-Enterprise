import { initMercadoPago } from '@mercadopago/sdk-react';

let initialized = false;
let currentKey = '';

export function initMercadoPagoSdk(publicKey: string): boolean {
  const key = publicKey.trim();
  if (!key) return false;
  if (initialized && currentKey === key) return true;
  initMercadoPago(key, { locale: 'pt-BR' });
  initialized = true;
  currentKey = key;
  return true;
}

export function isMercadoPagoSdkInitialized(): boolean {
  return initialized;
}

export function getMercadoPagoSdkPublicKey(): string {
  return currentKey;
}

/** Apenas para testes: permite reinicializar o estado do módulo. */
export function resetMercadoPagoSdkForTests(): void {
  initialized = false;
  currentKey = '';
}
