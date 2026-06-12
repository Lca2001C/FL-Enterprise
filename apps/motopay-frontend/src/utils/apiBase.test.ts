import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  normalizeLocalDevOrigin,
  pageOriginApiUrl,
  resolveApiBase,
  sameOriginApiPath,
  shouldUseRelativeApiForClient,
  shouldUseRelativeApiRequests,
  usesSameOriginApiProxy,
} from './apiBase';
import { absoluteApiUrl, resolveClientBaseUrl } from '../apiClient';

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

describe('usesSameOriginApiProxy', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('is true for SAME_ORIGIN docker build', () => {
    vi.stubGlobal('window', { location: { origin: 'http://localhost:5173', hostname: 'localhost' } });
    expect(usesSameOriginApiProxy('SAME_ORIGIN')).toBe(true);
    expect(shouldUseRelativeApiRequests('SAME_ORIGIN')).toBe(true);
    expect(resolveClientBaseUrl('http://localhost')).toBe('');
  });

  it('uses relative requests on localhost even with external VITE_API_BASE_URL', () => {
    vi.stubGlobal('window', {
      location: { origin: 'http://localhost:5173', hostname: 'localhost' },
    });
    expect(shouldUseRelativeApiRequests('https://api.production.example.com')).toBe(true);
    expect(resolveClientBaseUrl('http://localhost')).toBe('');
  });

  it('pageOriginApiUrl fixes bare localhost to dev port', () => {
    vi.stubGlobal('window', { location: { origin: 'http://localhost', hostname: 'localhost' } });
    expect(pageOriginApiUrl('/alerts?limit=50')).toBe('http://localhost:5173/alerts?limit=50');
  });

  it('sameOriginApiPath uses relative path on localhost (avoids port 80)', () => {
    vi.stubGlobal('window', {
      location: { origin: 'http://localhost', hostname: 'localhost' },
    });
    expect(sameOriginApiPath('/alerts?limit=50')).toBe('/alerts?limit=50');
  });

  it('uses relative requests on LAN IP', () => {
    vi.stubGlobal('window', {
      location: { origin: 'http://192.168.0.209:5173', hostname: '192.168.0.209' },
    });
    expect(shouldUseRelativeApiRequests()).toBe(true);
  });

  it('uses absolute API on Vercel when VITE_API_BASE_URL points to Render', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://motopay-api.onrender.com');
    vi.stubGlobal('window', {
      location: {
        origin: 'https://fl-enterprise.vercel.app',
        hostname: 'fl-enterprise.vercel.app',
        host: 'fl-enterprise.vercel.app',
      },
    });
    const apiBase = 'https://motopay-api.onrender.com';
    expect(shouldUseRelativeApiRequests()).toBe(false);
    expect(shouldUseRelativeApiForClient(apiBase)).toBe(false);
    expect(resolveClientBaseUrl(apiBase)).toBe('https://motopay-api.onrender.com');
    expect(absoluteApiUrl('/api/v1/auth/login', apiBase)).toBe(
      'https://motopay-api.onrender.com/api/v1/auth/login'
    );
  });

  it('falls back to relative on Vercel when apiBase is the same origin as the panel', () => {
    vi.stubEnv('VITE_API_BASE_URL', '');
    vi.stubGlobal('window', {
      location: {
        origin: 'https://fl-enterprise.vercel.app',
        hostname: 'fl-enterprise.vercel.app',
        host: 'fl-enterprise.vercel.app',
      },
    });
    expect(shouldUseRelativeApiForClient('https://fl-enterprise.vercel.app')).toBe(true);
    expect(resolveClientBaseUrl('https://fl-enterprise.vercel.app')).toBe('');
  });
});
