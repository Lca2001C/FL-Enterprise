import { describe, expect, it } from 'vitest';
import { normalizeBase } from './apiClient';

describe('normalizeBase', () => {
  it('remove barra final da URL', () => {
    expect(normalizeBase('http://localhost:8000/')).toBe('http://localhost:8000');
    expect(normalizeBase('http://localhost:8000')).toBe('http://localhost:8000');
  });
});
