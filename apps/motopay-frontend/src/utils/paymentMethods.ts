export type PaymentMethodKind = 'pix' | 'credit_card' | 'debit_card';

export const PAYMENT_METHOD_LABELS: Record<PaymentMethodKind, string> = {
  pix: 'Pix',
  credit_card: 'Cartão de crédito',
  debit_card: 'Cartão de débito',
};

export function isDebitPaymentMethodId(paymentMethodId: string): boolean {
  const pm = paymentMethodId.toLowerCase();
  return pm.startsWith('deb') || pm.includes('debit');
}

export function paymentMethodLabel(type: string | null | undefined): string {
  if (!type) return '—';
  if (type in PAYMENT_METHOD_LABELS) {
    return PAYMENT_METHOD_LABELS[type as PaymentMethodKind];
  }
  return type;
}

export function filterSavedCardsByKind<T extends { payment_method_id: string }>(
  cards: T[],
  kind: 'credit_card' | 'debit_card'
): T[] {
  return cards.filter((c) => {
    const isDebit = isDebitPaymentMethodId(c.payment_method_id);
    return kind === 'debit_card' ? isDebit : !isDebit;
  });
}
