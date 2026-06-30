import axios from 'axios';

const GENERIC_ERROR = 'Ocorreu um erro inesperado. Tente novamente em instantes.';

function detailToString(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'object' && item !== null && 'msg' in item) {
          return String((item as { msg: unknown }).msg);
        }
        if (typeof item === 'string') return item;
        return '';
      })
      .filter(Boolean);
    return parts.length ? parts.join('; ') : GENERIC_ERROR;
  }
  // Nunca expõe objetos crus/JSON técnico ao usuário final.
  return GENERIC_ERROR;
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
