/**
 * Mercado Pago Device ID (MP_DEVICE_SESSION_ID).
 *
 * O script https://www.mercadopago.com/v2/security.js incluído no
 * index.html injeta `window.MP_DEVICE_SESSION_ID` (via attribute
 * output="deviceId") e/ou o id global `MP_DEVICE_SESSION_ID`.
 * Usamos as duas fontes para máxima compatibilidade.
 */

declare global {
  interface Window {
    MP_DEVICE_SESSION_ID?: string;
  }
}

const FALLBACK_KEY = 'mp_device_session_id_local';

function readFromGlobal(): string {
  if (typeof window === 'undefined') return '';
  const id = window.MP_DEVICE_SESSION_ID;
  if (id && typeof id === 'string') return id.trim();
  // O script MP também escreve o id num input hidden quando output="deviceId"
  const el = document.getElementById('deviceId') as HTMLInputElement | null;
  if (el?.value) return el.value.trim();
  return '';
}

function generateFallback(): string {
  if (typeof window === 'undefined') return '';
  // crypto.randomUUID nem sempre existe — fallback robusto
  const c = (window as unknown as { crypto?: Crypto }).crypto;
  if (c && typeof c.randomUUID === 'function') {
    return c.randomUUID();
  }
  return `mp-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Retorna o Device ID atual. Em ambiente onde o script do MP não carrega
 * (ex.: bloqueador de scripts), gera e persiste um fallback estável por
 * sessão para que o backend ainda receba um identificador.
 */
export function getMercadoPagoDeviceId(): string {
  const real = readFromGlobal();
  if (real) return real;
  try {
    const stored = window.sessionStorage.getItem(FALLBACK_KEY);
    if (stored) return stored;
    const generated = generateFallback();
    window.sessionStorage.setItem(FALLBACK_KEY, generated);
    return generated;
  } catch {
    return generateFallback();
  }
}

/**
 * Aguarda o script de security do MP carregar e popular o device id.
 * Resolve no primeiro tick em que window.MP_DEVICE_SESSION_ID estiver
 * disponível — ou após `timeoutMs` (usa fallback).
 */
export async function ensureMercadoPagoDeviceId(timeoutMs = 2000): Promise<string> {
  const start = Date.now();
  return new Promise((resolve) => {
    const tick = () => {
      const id = readFromGlobal();
      if (id) {
        resolve(id);
        return;
      }
      if (Date.now() - start >= timeoutMs) {
        resolve(getMercadoPagoDeviceId());
        return;
      }
      window.setTimeout(tick, 100);
    };
    tick();
  });
}
