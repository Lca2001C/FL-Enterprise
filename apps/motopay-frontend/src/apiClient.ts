import axios, { type AxiosInstance } from 'axios';

export function normalizeBase(url: string): string {
  return url.replace(/\/$/, '');
}

/** Cliente HTTP com Bearer e operacao_id em query (paridade com Streamlit). */
export function createApiClient(
  baseURL: string,
  getToken: () => string | null,
  getEffectiveOperacaoId: () => number | null
): AxiosInstance {
  const client = axios.create({ baseURL: normalizeBase(baseURL) });

  client.interceptors.request.use((config) => {
    const t = getToken();
    if (t) {
      config.headers.Authorization = `Bearer ${t}`;
    }

    const path = typeof config.url === 'string' ? config.url : '';
    if (!path.includes('/auth/')) {
      const oid = getEffectiveOperacaoId();
      if (oid != null && oid > 0) {
        const prev = config.params;
        const base =
          typeof prev === 'object' && prev !== null && !Array.isArray(prev) ? prev : {};
        config.params = { ...base, operacao_id: oid };
      }
    }

    return config;
  });

  return client;
}
