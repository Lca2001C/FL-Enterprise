import { afterEach, describe, expect, it, vi } from 'vitest';
import { normalizeLocalDevOrigin, resolveApiBase } from './apiBase';

describe('normalizeLocalDevOrigin', () => {
  it('maps bare localhost to docker frontend port', () => {
    expect(normalizeLocalDevOrigin('http://localhost')).toBe('http://localhost:5173');
    expect(normalizeLocalDevOrigin('http://127.0.0.1')).toBe('http://127.0.0.1:5173');
  });

  it('keeps explicit dev ports unchanged', () => {
    expect(normalizeLocalDevOrigin('http://localhost:5173')).toBe('http://localhost:5173');
    expect(normalizeLocalDevOrigin('http://localhost:8000')).toBe('http://localhost:8000');
  });
});

describe('resolveApiBase', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('uses configured localhost when not in browser', () => {
    expect(resolveApiBase('http://localhost:8000')).toBe('http://localhost:8000');
  });

  it('uses stored value when env is empty and not in browser', () => {
    expect(resolveApiBase(undefined, 'http://192.168.1.10:8000')).toBe('http://192.168.1.10:8000');
  });

  it('uses page origin for local dev when vite proxies API', () => {
    vi.stubGlobal('window', { location: { origin: 'http://localhost:5173' } });
    expect(resolveApiBase('http://localhost:8000')).toBe('http://localhost:5173');
    expect(resolveApiBase(undefined, 'http://localhost')).toBe('http://localhost:5173');
    expect(resolveApiBase('SAME_ORIGIN')).toBe('http://localhost:5173');
  });

  it('normalizes bare localhost origin to docker host port', () => {
    vi.stubGlobal('window', { location: { origin: 'http://localhost' } });
    expect(resolveApiBase('http://localhost:8000')).toBe('http://localhost:5173');
    expect(resolveApiBase('SAME_ORIGIN')).toBe('http://localhost:5173');
  });
});
