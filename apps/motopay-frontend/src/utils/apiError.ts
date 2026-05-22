import axios from 'axios';

function detailToString(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'object' && item !== null && 'msg' in item) {
          return String((item as { msg: unknown }).msg);
        }
        return String(item);
      })
      .join('; ');
  }
  if (typeof detail === 'object' && detail !== null) {
    return JSON.stringify(detail);
  }
  return 'Erro desconhecido';
}

export function parseApiError(err: unknown, fallback = 'Ocorreu um erro'): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data;
    if (data && typeof data === 'object' && data !== null && 'detail' in data) {
      return detailToString((data as { detail: unknown }).detail);
    }
    if (err.message) return err.message;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}
