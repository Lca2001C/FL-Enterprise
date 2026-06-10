const DEFAULT_API_PORT = '8000';
const DEFAULT_FRONTEND_PORT =
  (typeof import.meta !== 'undefined' &&
    (import.meta.env.VITE_DEV_FRONTEND_PORT as string | undefined)) ||
  '5173';

const LOCAL_DEV_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);

function isLocalDevHostname(hostname: string): boolean {
  return LOCAL_DEV_HOSTS.has(hostname);
}

function isBareLocalDevUrl(url: string): boolean {
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

function isSeparateProductionApi(envUrl: string): boolean {
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
