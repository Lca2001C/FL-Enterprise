import { initMercadoPago } from '@mercadopago/sdk-react';

let initialized = false;
<<<<<<< HEAD
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
=======
let currentPublicKey = '';
const readyListeners = new Set<() => void>();

function notifySdkReady(): void {
  readyListeners.forEach((listener) => listener());
}

export function subscribeMercadoPagoSdkReady(listener: () => void): () => void {
  readyListeners.add(listener);
  if (initialized) listener();
  return () => readyListeners.delete(listener);
}

export function initMercadoPagoSdk(publicKey: string): void {
  const key = publicKey.trim();
  if (!key) return;
  if (initialized && key === currentPublicKey) return;
  // security.js em index.html já fornece device fingerprint; evita scripts extras (mlstatic).
  initMercadoPago(key, { locale: 'pt-BR', advancedFraudPrevention: false });
  currentPublicKey = key;
  initialized = true;
  notifySdkReady();
}

export function getMercadoPagoSdkPublicKey(): boolean {
  return initialized;
}

export function getMercadoPagoCurrentPublicKey(): string {
  return currentPublicKey;
>>>>>>> main
}
