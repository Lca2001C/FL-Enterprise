import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import { sanitizeApiBase } from './utils/apiBase';

export function normalizeBase(url: string): string {
  return url.replace(/\/$/, '');
}

export type ApiClientCallbacks = {
  getRefreshToken: () => string | null;
  onTokenRefreshed: (accessToken: string, refreshToken: string) => void;
  onAuthFailed: () => void;
};

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };

function isAuthPath(url: string | undefined): boolean {
  if (!url) return false;
  return url.includes('/auth/login') || url.includes('/auth/refresh') || url.includes('/auth/logout');
}

/** Cliente HTTP com Bearer, operacao_id em query e refresh automático em 401. */
export function createApiClient(
  baseURL: string,
  getToken: () => string | null,
  getEffectiveOperacaoId: () => number | null,
  callbacks?: ApiClientCallbacks
): AxiosInstance {
  const client = axios.create({ baseURL: sanitizeApiBase(normalizeBase(baseURL)) });
  let refreshPromise: Promise<string | null> | null = null;

  const doRefresh = async (): Promise<string | null> => {
    if (!callbacks) return null;
    const rt = callbacks.getRefreshToken();
    if (!rt) return null;
    try {
      const res = await axios.post<{ access_token: string; refresh_token: string }>(
        `${sanitizeApiBase(normalizeBase(baseURL))}/api/v1/auth/refresh`,
        { refresh_token: rt }
      );
      callbacks.onTokenRefreshed(res.data.access_token, res.data.refresh_token);
      return res.data.access_token;
    } catch {
      callbacks.onAuthFailed();
      return null;
    }
  };

  client.interceptors.request.use((config) => {
    if (config.baseURL) {
      config.baseURL = sanitizeApiBase(normalizeBase(config.baseURL));
    }

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

  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const original = error.config as RetryConfig | undefined;
      if (
        !callbacks ||
        !original ||
        original._retry ||
        error.response?.status !== 401 ||
        isAuthPath(original.url)
      ) {
        return Promise.reject(error);
      }

      original._retry = true;

      if (!refreshPromise) {
        refreshPromise = doRefresh().finally(() => {
          refreshPromise = null;
        });
      }

      const newToken = await refreshPromise;
      if (!newToken) {
        return Promise.reject(error);
      }

      original.headers.Authorization = `Bearer ${newToken}`;
      return client.request(original);
    }
  );

  return client;
}
