import { describe, expect, it } from 'vitest';
import { resolveApiBase } from './apiBase';

describe('resolveApiBase', () => {
  it('uses configured localhost when not in browser', () => {
    expect(resolveApiBase('http://localhost:8000')).toBe('http://localhost:8000');
  });

  it('uses stored value when env is empty and not in browser', () => {
    expect(resolveApiBase(undefined, 'http://192.168.1.10:8000')).toBe('http://192.168.1.10:8000');
  });
});
