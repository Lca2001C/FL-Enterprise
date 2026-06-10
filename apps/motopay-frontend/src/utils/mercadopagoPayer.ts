export type MercadoPagoBrickPayer = {
  email: string;
  entityType: 'individual' | 'association';
  identification?: { type: string; number: string };
  customerId?: string;
  cardsIds?: string[];
};

/** Valor numérico para o Brick (API pode devolver string decimal). */
export function normalizeBrickAmount(value: number | string): number {
  const n =
    typeof value === 'number'
      ? value
      : Number(String(value).trim().replace(',', '.'));
  if (!Number.isFinite(n) || n <= 0) return 0;
  return Math.round(n * 100) / 100;
}

/** Payer exigido pelo Payment/Card Brick (entityType: individual | association). */
export function buildMercadoPagoBrickPayer(input: {
  email: string;
  identification: { type: string; number: string };
  customerId?: string;
  cardsIds?: string[];
}): MercadoPagoBrickPayer {
  const idNumber = input.identification.number.replace(/\D/g, '');
  return {
    entityType: 'individual',
    email: input.email,
    ...(idNumber.length > 0
      ? {
          identification: {
            type: input.identification.type,
            number: idNumber,
          },
        }
      : {}),
    ...(input.customerId ? { customerId: input.customerId } : {}),
    ...(input.cardsIds?.length ? { cardsIds: input.cardsIds } : {}),
  };
}

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
