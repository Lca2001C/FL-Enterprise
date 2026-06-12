const DEFAULT_API_PORT = '8000';
const DEFAULT_FRONTEND_PORT =
  (typeof import.meta !== 'undefined' &&
    (import.meta.env.VITE_DEV_FRONTEND_PORT as string | undefined)) ||
  '5173';

const LOCAL_DEV_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);

export function isLocalDevHostname(hostname: string): boolean {
  return LOCAL_DEV_HOSTS.has(hostname);
}

function isPrivateLanHostname(hostname: string): boolean {
  return (
    /^192\.168\./.test(hostname) ||
    /^10\./.test(hostname) ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname)
  );
}

export function isBareLocalDevUrl(url: string): boolean {
  try {
    const u = new URL(url.includes('://') ? url : `http://${url}`);
    if (!isLocalDevHostname(u.hostname)) return false;
    const port = u.port || (u.protocol === 'https:' ? '443' : '80');
    return port === '80' || port === '443';
  } catch {
    return false;
  }
}

export function sanitizeApiBase(url: string): string {
  const trimmed = url.trim().replace(/\/$/, '');
  if (!trimmed) return trimmed;
  return normalizeLocalDevOrigin(trimmed);
}

/** Docker expõe nginx em :5173 no host; localhost sem porta aponta para :80 (nada escuta). */
export function normalizeLocalDevOrigin(origin: string): string {
  if (!isBareLocalDevUrl(origin)) return origin;
  try {
    const u = new URL(origin.includes('://') ? origin : `http://${origin}`);
    return `${u.protocol}//${u.hostname}:${DEFAULT_FRONTEND_PORT}`;
  } catch {
    return origin;
  }
}

function normalizeStoredLocalDev(stored: string | null | undefined): string | undefined {
  const trimmed = stored?.trim().replace(/\/$/, '');
  if (!trimmed) return undefined;
  if (isBareLocalDevUrl(trimmed)) {
    return normalizeLocalDevOrigin(trimmed);
  }
  return trimmed;
}

export function isSeparateProductionApi(envUrl: string): boolean {
  if (!envUrl || envUrl === 'SAME_ORIGIN') return false;
  try {
    const u = new URL(envUrl.includes('://') ? envUrl : `http://${envUrl}`);
    if (isLocalDevHostname(u.hostname)) return false;
    if (/^192\.168\./.test(u.hostname) || /^10\./.test(u.hostname)) return false;
    return true;
  } catch {
    return false;
  }
}

export function viteApiBaseFromEnv(): string {
  return ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '').trim().replace(/\/$/, '');
}

/** Em dev local, força mesma origem da página (proxy /api e /alerts) para respeitar CSP. */
function preferPageOriginForLocalDev(configured: string, origin: string): string {
  try {
    const target = new URL(configured.includes('://') ? configured : `http://${configured}`);
    const current = new URL(origin);
    if (isLocalDevHostname(target.hostname) && isLocalDevHostname(current.hostname)) {
      return origin;
    }
  } catch {
    // ignore malformed URL
  }
  return configured;
}

/** URL base da API. Docker/LAN usa mesma origem do painel (nginx faz proxy de /api). */
export function resolveApiBase(envUrl?: string, stored?: string | null): string {
  const fallback = `http://localhost:${DEFAULT_API_PORT}`;
  const env = (envUrl?.trim() || '').replace(/\/$/, '');
  const normalizedStored = normalizeStoredLocalDev(stored);
  const configured = (env || normalizedStored || fallback).replace(/\/$/, '');

  if (typeof window === 'undefined') {
    const resolved = configured === 'SAME_ORIGIN' ? fallback : configured;
    return sanitizeApiBase(resolved);
  }

  const origin = normalizeLocalDevOrigin(window.location.origin.replace(/\/$/, ''));

  let resolved: string;
  if (env === 'SAME_ORIGIN' || configured === 'SAME_ORIGIN') {
    resolved = origin;
  } else if (!isSeparateProductionApi(env || configured)) {
    resolved = origin;
  } else {
    resolved = normalizeLocalDevOrigin(preferPageOriginForLocalDev(configured, origin));
  }

  return sanitizeApiBase(resolved);
}

/** Painel Docker/Vite: API em /api e /alerts no mesmo host da página. */
export function usesSameOriginApiProxy(envUrl?: string): boolean {
  if (typeof window === 'undefined') return false;
  const env = (envUrl?.trim() || '').replace(/\/$/, '');
  if (!env || env === 'SAME_ORIGIN') return true;
  return !isSeparateProductionApi(env);
}

/** Navegador em localhost/LAN: sempre /api e /alerts via proxy (nginx ou Vite). */
export function shouldUseRelativeApiRequests(envUrl?: string): boolean {
  if (typeof window === 'undefined') return false;
  const host = window.location.hostname;
  if (isLocalDevHostname(host) || isPrivateLanHostname(host)) return true;
  const env = (envUrl ?? viteApiBaseFromEnv()).trim().replace(/\/$/, '');
  return usesSameOriginApiProxy(env || undefined);
}

/**
 * Axios/fetch: em Vercel + API no Render, usa URL absoluta quando apiBase ou VITE_API_BASE_URL
 * apontam para host de produção separado do painel.
 */
function apiBaseSharesPageOrigin(apiBase: string): boolean {
  const normalized = apiBase.trim().replace(/\/$/, '');
  if (!normalized) return false;
  try {
    const apiHost = new URL(normalized.includes('://') ? normalized : `http://${normalized}`).host;
    return apiHost === window.location.host;
  } catch {
    return false;
  }
}

export function shouldUseRelativeApiForClient(apiBase: string, envUrl?: string): boolean {
  if (typeof window === 'undefined') return false;
  const host = window.location.hostname;
  if (isLocalDevHostname(host) || isPrivateLanHostname(host)) return true;
  if (apiBaseSharesPageOrigin(apiBase)) return true;
  if (isSeparateProductionApi(apiBase.trim().replace(/\/$/, ''))) return false;
  const env = (envUrl ?? viteApiBaseFromEnv()).trim().replace(/\/$/, '');
  return usesSameOriginApiProxy(env || undefined);
}

/** Origem da API no browser (corrige localhost sem porta → :5173). */
export function pageOriginApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (typeof window === 'undefined') return normalizedPath;
  const origin = normalizeLocalDevOrigin(window.location.origin.replace(/\/$/, ''));
  return `${origin}${normalizedPath}`;
}

/**
 * Path para fetch/axios em dev Docker/Vite: relativo à página (porta correta garantida).
 * Em produção com API separada, retorna URL absoluta.
 */
export function sameOriginApiPath(path: string, envUrl?: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (typeof window !== 'undefined' && shouldUseRelativeApiRequests(envUrl)) {
    return normalizedPath;
  }
  return pageOriginApiUrl(normalizedPath);
}
