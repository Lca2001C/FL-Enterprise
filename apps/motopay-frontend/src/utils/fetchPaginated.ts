import type { AxiosInstance } from 'axios';
import type { Paginated } from '../apiTypes';

export const FETCH_PAGE_SIZE = 200;
const MAX_PAGES = 50; // safety cap: 50 * 200 = 10.000 registros máximo

export function offsetAfterDelete(
  currentOffset: number,
  pageSize: number,
  wasLastItemOnPage: boolean
): number {
  if (wasLastItemOnPage && currentOffset > 0) {
    return Math.max(0, currentOffset - pageSize);
  }
  return currentOffset;
}

export async function fetchAllPaginated<T>(
  api: AxiosInstance,
  path: string,
  extraParams: Record<string, unknown> = {}
): Promise<T[]> {
  const items: T[] = [];
  let offset = 0;
  let total = Infinity;
  let pages = 0;

  while (items.length < total && pages < MAX_PAGES) {
    const r = await api.get<Paginated<T>>(path, {
      params: { ...extraParams, limit: FETCH_PAGE_SIZE, offset },
    });
    items.push(...r.data.items);
    total = r.data.total;
    offset += FETCH_PAGE_SIZE;
    pages++;
  }

  return items;
}
