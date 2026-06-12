import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import {
  isBareLocalDevUrl,
  pageOriginApiUrl,
  sanitizeApiBase,
  shouldUseRelativeApiForClient,
} from './utils/apiBase';

export function normalizeBase(url: string): string {
  return url.replace(/\/$/, '');
}

/**
 * baseURL do axios. Em Docker/dev com proxy, usa '' e o interceptor
 * reescreve paths para pageOriginApiUrl (porta correta).
 */
export function resolveClientBaseUrl(baseURL: string): string {
  if (shouldUseRelativeApiForClient(baseURL)) {
    return '';
  }
  return sanitizeApiBase(normalizeBase(baseURL));
}

export function absoluteApiUrl(path: string, baseURL: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (shouldUseRelativeApiForClient(baseURL)) {
    return normalizedPath;
  }
  const base = sanitizeApiBase(normalizeBase(baseURL));
  return `${base}${normalizedPath}`;
}

function applyRequestOrigin(config: InternalAxiosRequestConfig, baseURL: string): void {
  const raw = typeof config.url === 'string' ? config.url : '';

  if (raw.startsWith('http://') || raw.startsWith('https://')) {
    try {
      const parsed = new URL(raw);
      if (isBareLocalDevUrl(parsed.origin)) {
        config.baseURL = '';
        config.url = pageOriginApiUrl(`${parsed.pathname}${parsed.search}`);
      }
    } catch {
      // ignore malformed URL
    }
    return;
  }

  if (!raw.startsWith('/')) return;

  if (shouldUseRelativeApiForClient(baseURL)) {
    config.baseURL = '';
    return;
  }

  const base = String(config.baseURL ?? '');
  if (base && isBareLocalDevUrl(base)) {
    config.baseURL = sanitizeApiBase(normalizeBase(base));
  }
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
  const client = axios.create({ baseURL: resolveClientBaseUrl(baseURL) });
  let refreshPromise: Promise<string | null> | null = null;

  const doRefresh = async (): Promise<string | null> => {
    if (!callbacks) return null;
    const rt = callbacks.getRefreshToken();
    if (!rt) return null;
    try {
      const res = await axios.post<{ access_token: string; refresh_token: string }>(
        absoluteApiUrl('/api/v1/auth/refresh', baseURL),
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
    applyRequestOrigin(config, baseURL);

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
      applyRequestOrigin(original, baseURL);
      return client.request(original);
    }
  );

  return client;
}
