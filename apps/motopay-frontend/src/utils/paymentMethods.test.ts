import { describe, expect, it } from 'vitest';
import {
  filterSavedCardsByKind,
  isDebitPaymentMethodId,
  paymentMethodLabel,
} from './paymentMethods';

describe('paymentMethods', () => {
  it('detects debit payment method ids', () => {
    expect(isDebitPaymentMethodId('debvisa')).toBe(true);
    expect(isDebitPaymentMethodId('visa')).toBe(false);
  });

  it('labels known types', () => {
    expect(paymentMethodLabel('pix')).toBe('Pix');
    expect(paymentMethodLabel('credit_card')).toBe('Cartão de crédito');
    expect(paymentMethodLabel(null)).toBe('—');
  });

  it('filters saved cards by kind', () => {
    const cards = [
      { id: 1, payment_method_id: 'visa' },
      { id: 2, payment_method_id: 'debvisa' },
    ];
    expect(filterSavedCardsByKind(cards, 'debit_card')).toEqual([cards[1]]);
    expect(filterSavedCardsByKind(cards, 'credit_card')).toEqual([cards[0]]);
  });
});
