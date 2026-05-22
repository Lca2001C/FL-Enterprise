import { describe, expect, it, vi } from 'vitest';
import { fetchAllPaginated, offsetAfterDelete } from './fetchPaginated';

describe('offsetAfterDelete', () => {
  it('mantém offset quando ainda há itens na página', () => {
    expect(offsetAfterDelete(50, 50, false)).toBe(50);
  });

  it('volta uma página quando remove o último item', () => {
    expect(offsetAfterDelete(50, 50, true)).toBe(0);
    expect(offsetAfterDelete(100, 50, true)).toBe(50);
  });

  it('não vai abaixo de zero', () => {
    expect(offsetAfterDelete(0, 50, true)).toBe(0);
  });
});

describe('fetchAllPaginated', () => {
  it('busca todas as páginas até total', async () => {
    const get = vi
      .fn()
      .mockResolvedValueOnce({ data: { items: [1, 2], total: 3 } })
      .mockResolvedValueOnce({ data: { items: [3], total: 3 } });

    const api = { get } as unknown as Parameters<typeof fetchAllPaginated>[0];
    const items = await fetchAllPaginated<number>(api, '/api/v1/test');

    expect(items).toEqual([1, 2, 3]);
    expect(get).toHaveBeenCalledTimes(2);
    expect(get.mock.calls[0][1]?.params).toMatchObject({ limit: 200, offset: 0 });
    expect(get.mock.calls[1][1]?.params).toMatchObject({ limit: 200, offset: 200 });
  });

  it('repassa params extras', async () => {
    const get = vi.fn().mockResolvedValue({ data: { items: [], total: 0 } });
    const api = { get } as unknown as Parameters<typeof fetchAllPaginated>[0];

    await fetchAllPaginated(api, '/api/v1/motos', { status: 'ativo' });

    expect(get.mock.calls[0][1]?.params).toMatchObject({
      status: 'ativo',
      limit: 200,
      offset: 0,
    });
  });
});
