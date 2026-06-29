const STATUS_DETAIL_PT: Record<string, string> = {
  rejected_by_issuer:
    'Cartão recusado pelo banco emissor. No sandbox, use cartão de teste aprovado (ex.: Visa 4509 9535 6623 3704, titular APRO, CVV 123).',
  cc_rejected_insufficient_amount: 'Saldo ou limite insuficiente no cartão.',
  cc_rejected_bad_filled_security_code: 'CVV inválido.',
  cc_rejected_bad_filled_date: 'Data de validade inválida.',
  cc_rejected_bad_filled_card_number: 'Número do cartão inválido.',
};

export function formatMercadoPagoStatusDetail(statusDetail: string | null | undefined): string {
  const code = (statusDetail ?? '').trim();
  if (!code) return 'Pagamento recusado. Tente outro cartão ou forma de pagamento.';
  if (STATUS_DETAIL_PT[code]) return STATUS_DETAIL_PT[code];
  if (code.startsWith('cc_rejected')) return 'Pagamento recusado pelo emissor do cartão.';
  return `Pagamento não aprovado (${code}).`;
}
