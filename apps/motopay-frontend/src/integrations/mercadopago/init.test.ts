import { beforeEach, describe, expect, it, vi } from 'vitest';

const initMercadoPago = vi.fn();

vi.mock('@mercadopago/sdk-react', () => ({
  initMercadoPago,
}));

describe('initMercadoPagoSdk', () => {
  beforeEach(async () => {
    vi.resetModules();
    initMercadoPago.mockClear();
    const mod = await import('./init');
    mod.resetMercadoPagoSdkForTests();
  });

  it('inicializa uma vez com chave não vazia', async () => {
    const { initMercadoPagoSdk, isMercadoPagoSdkInitialized } = await import('./init');
    expect(initMercadoPagoSdk('TEST_PUBLIC_KEY')).toBe(true);
    expect(initMercadoPago).toHaveBeenCalledTimes(1);
    expect(initMercadoPago).toHaveBeenCalledWith('TEST_PUBLIC_KEY', { locale: 'pt-BR' });
    expect(isMercadoPagoSdkInitialized()).toBe(true);
    expect(initMercadoPagoSdk('TEST_PUBLIC_KEY')).toBe(true);
    expect(initMercadoPago).toHaveBeenCalledTimes(1);
  });

  it('não inicializa com chave vazia', async () => {
    const { initMercadoPagoSdk, isMercadoPagoSdkInitialized } = await import('./init');
    expect(initMercadoPagoSdk('   ')).toBe(false);
    expect(initMercadoPago).not.toHaveBeenCalled();
    expect(isMercadoPagoSdkInitialized()).toBe(false);
  });

  it('reinicializa quando a public key muda', async () => {
    const { initMercadoPagoSdk, getMercadoPagoSdkPublicKey } = await import('./init');
    expect(initMercadoPagoSdk('KEY_A')).toBe(true);
    expect(initMercadoPago).toHaveBeenCalledTimes(1);
    expect(getMercadoPagoSdkPublicKey()).toBe('KEY_A');
    expect(initMercadoPagoSdk('KEY_B')).toBe(true);
    expect(initMercadoPago).toHaveBeenCalledTimes(2);
    expect(initMercadoPago).toHaveBeenLastCalledWith('KEY_B', { locale: 'pt-BR' });
    expect(getMercadoPagoSdkPublicKey()).toBe('KEY_B');
  });
});
