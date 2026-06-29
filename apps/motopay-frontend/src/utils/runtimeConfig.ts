/** API base injected at container start (Render) when VITE build arg is SAME_ORIGIN. */
let runtimeApiBase = '';

export function setRuntimeApiBase(url: string): void {
  runtimeApiBase = url.trim().replace(/\/$/, '');
}

export function getRuntimeApiBase(): string {
  return runtimeApiBase;
}

export async function loadRuntimeConfig(): Promise<void> {
  if (typeof window === 'undefined') return;
  try {
    const res = await fetch('/runtime-config.json', { cache: 'no-store' });
    if (!res.ok) return;
    const data = (await res.json()) as { apiBase?: string };
    if (data.apiBase?.trim()) {
      setRuntimeApiBase(data.apiBase);
    }
  } catch {
    // optional file — ignore when missing (local dev / docker-compose)
  }
}
