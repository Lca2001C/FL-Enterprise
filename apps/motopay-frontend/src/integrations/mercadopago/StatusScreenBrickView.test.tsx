import { describe, expect, it } from 'vitest';
import { buildStatusScreenInitialization } from './StatusScreenBrickView';

describe('buildStatusScreenInitialization', () => {
  it('retorna apenas paymentId sem 3DS', () => {
    const init = buildStatusScreenInitialization('pay-123');
    expect(init.paymentId).toBe('pay-123');
    expect(init.additionalInfo).toBeUndefined();
  });

  it('inclui additionalInfo quando há dados 3DS', () => {
    const init = buildStatusScreenInitialization('pay-456', {
      external_resource_url: 'https://mp.test/3ds',
      creq: 'creq-val',
    });
    expect(init.additionalInfo).toEqual({
      externalResourceURL: 'https://mp.test/3ds',
      creq: 'creq-val',
    });
  });
});
