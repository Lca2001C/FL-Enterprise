import { describe, expect, it } from 'vitest';
import {
  buildMercadoPagoBrickPayer,
  mercadoPagoPayerEmail,
  normalizeBrickAmount,
} from './mercadopagoPayer';

describe('normalizeBrickAmount', () => {
  it('parses API decimal strings', () => {
    expect(normalizeBrickAmount('7000.00')).toBe(7000);
    expect(normalizeBrickAmount(399.98)).toBe(399.98);
  });

  it('rejects invalid amounts', () => {
    expect(normalizeBrickAmount(0)).toBe(0);
    expect(normalizeBrickAmount('')).toBe(0);
  });
});

describe('buildMercadoPagoBrickPayer', () => {
  it('sets entityType individual for Payment Brick', () => {
    const payer = buildMercadoPagoBrickPayer({
      email: 'test@example.com',
      identification: { type: 'CPF', number: '12345678901' },
    });
    expect(payer.entityType).toBe('individual');
    expect(payer.email).toBe('test@example.com');
    expect(payer.identification?.number).toBe('12345678901');
  });

  it('includes identification when any digits are present', () => {
    const payer = buildMercadoPagoBrickPayer({
      email: 'test@example.com',
      identification: { type: 'CPF', number: '123' },
    });
    expect(payer.identification?.number).toBe('123');
  });

  it('omits identification when empty', () => {
    const payer = buildMercadoPagoBrickPayer({
      email: 'test@example.com',
      identification: { type: 'CPF', number: '' },
    });
    expect(payer.identification).toBeUndefined();
  });

  it('omits entityType when customerId is set (saved cards)', () => {
    const payer = buildMercadoPagoBrickPayer({
      email: 'test@example.com',
      identification: { type: 'CPF', number: '12345678901' },
      customerId: 'cust-1',
      cardsIds: ['card-1'],
    });
    expect(payer.entityType).toBeUndefined();
    expect(payer.customerId).toBe('cust-1');
  });
});

describe('mercadoPagoPayerEmail', () => {
  it('uses test user email in test mode', () => {
    expect(mercadoPagoPayerEmail(5, 'test')).toBe('test_user_5@testuser.com');
  });
});
