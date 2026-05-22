import { describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import { normalizeBase, createApiClient } from './apiClient';
import { formatBrl, roleLabel } from './utils/format';
import { parseApiError } from './utils/apiError';

describe('normalizeBase', () => {
  it('remove barra final da URL', () => {
    expect(normalizeBase('http://localhost:8000/')).toBe('http://localhost:8000');
    expect(normalizeBase('http://localhost:8000')).toBe('http://localhost:8000');
  });
});

describe('formatBrl', () => {
  it('formata valor em reais', () => {
    expect(formatBrl(358.05)).toContain('358,05');
    expect(formatBrl(358.05)).toMatch(/^R\$/);
  });
});

describe('roleLabel', () => {
  it('traduz papéis conhecidos', () => {
    expect(roleLabel('admin')).toBe('Administrador');
    expect(roleLabel('dono')).toBe('Dono da operação');
  });
});

describe('parseApiError', () => {
  it('extrai detail string do axios', () => {
    const err = {
      isAxiosError: true,
      response: { data: { detail: 'Credenciais inválidas' } },
      message: 'Request failed',
    };
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true);
    expect(parseApiError(err)).toBe('Credenciais inválidas');
  });

  it('usa fallback para erro genérico', () => {
    expect(parseApiError(new Error('falha'), 'Ops')).toBe('falha');
  });
});

describe('createApiClient', () => {
  it('registra interceptors de request e response', () => {
    const client = createApiClient('http://localhost:8000', () => 'token', () => 1, {
      getRefreshToken: () => 'refresh',
      onTokenRefreshed: vi.fn(),
      onAuthFailed: vi.fn(),
    });
    expect(client.interceptors.request.handlers?.length).toBeGreaterThan(0);
    expect(client.interceptors.response.handlers?.length).toBeGreaterThan(0);
  });
});
