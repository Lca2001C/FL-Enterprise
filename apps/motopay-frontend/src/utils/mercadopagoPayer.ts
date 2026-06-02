/** E-mail do pagador aceito pelo Mercado Pago (sandbox exige @testuser.com). */
export function mercadoPagoPayerEmail(
  clienteId: number,
  credentialsMode: 'test' | 'production' = 'production',
): string {
  if (credentialsMode === 'test') {
    return `test_user_${clienteId}@testuser.com`;
  }
  return `cliente${clienteId}@motopay.local`;
}
