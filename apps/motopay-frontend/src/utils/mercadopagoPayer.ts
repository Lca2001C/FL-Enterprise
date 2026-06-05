export function mercadoPagoPayerEmail(
  clienteId: number,
  credentialsMode: 'test' | 'production' = 'production',
  email?: string | null,
): string {
  if (credentialsMode === 'test') {
    return `test_user_${clienteId}@testuser.com`;
  }
  const trimmed = (email ?? '').trim().toLowerCase();
  if (trimmed && trimmed.includes('@')) {
    return trimmed;
  }
  return `cliente${clienteId}@motopay.local`;
}
