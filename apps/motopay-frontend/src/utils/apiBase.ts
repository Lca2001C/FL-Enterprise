const DEFAULT_API_PORT = '8000';

function isSeparateProductionApi(envUrl: string): boolean {
  if (!envUrl || envUrl === 'SAME_ORIGIN') return false;
  try {
    const u = new URL(envUrl.includes('://') ? envUrl : `http://${envUrl}`);
    if (u.hostname === 'localhost' || u.hostname === '127.0.0.1') return false;
    if (/^192\.168\./.test(u.hostname) || /^10\./.test(u.hostname)) return false;
    return true;
  } catch {
    return false;
  }
}

/** URL base da API. Docker/LAN usa mesma origem do painel (nginx faz proxy de /api). */
export function resolveApiBase(envUrl?: string, stored?: string | null): string {
  const fallback = `http://localhost:${DEFAULT_API_PORT}`;
  const configured = (envUrl?.trim() || stored?.trim() || fallback).replace(/\/$/, '');

  if (typeof window === 'undefined') {
    return configured === 'SAME_ORIGIN' ? fallback : configured;
  }

  const origin = window.location.origin.replace(/\/$/, '');
  const env = (envUrl?.trim() || '').replace(/\/$/, '');

  if (env === 'SAME_ORIGIN' || !isSeparateProductionApi(env || configured)) {
    return origin;
  }

  return configured;
}
