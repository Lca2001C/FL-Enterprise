import { describe, expect, it, beforeEach, vi } from 'vitest';
import {
  getOwnerTourSteps,
  isOwnerTourEligible,
  shouldShowOwnerTourBanner,
  OWNER_TOUR_DONE_KEY,
  OWNER_TOUR_BANNER_DISMISSED_KEY,
  markOwnerTourCompleted,
  dismissOwnerTourBanner,
} from './ownerTourSteps';
describe('getOwnerTourSteps', () => {
  it('includes ajustes step for dono', () => {
    const steps = getOwnerTourSteps('dono');
    expect(steps.some((s) => s.id === 'settings')).toBe(true);
    expect(steps.every((s) => s.tourId === undefined || s.tourId.length > 0)).toBe(true);
  });

  it('includes scope step only for admin', () => {
    const adminSteps = getOwnerTourSteps('admin');
    const donoSteps = getOwnerTourSteps('dono');
    expect(adminSteps.some((s) => s.id === 'scope')).toBe(true);
    expect(donoSteps.some((s) => s.id === 'scope')).toBe(false);
  });

  it('includes ajustes step for admin', () => {
    const steps = getOwnerTourSteps('admin');
    expect(steps.some((s) => s.id === 'settings')).toBe(true);
  });

  it('defines tour anchors for highlighted steps', () => {
    const steps = getOwnerTourSteps('dono').filter((s) => s.tourId);
    expect(steps.length).toBeGreaterThan(8);
    for (const step of steps) {
      expect(step.tourId).toMatch(/^[a-z0-9-]+$/);
    }
  });
});

describe('isOwnerTourEligible', () => {
  it('allows dono and admin only', () => {
    expect(isOwnerTourEligible('dono')).toBe(true);
    expect(isOwnerTourEligible('admin')).toBe(true);
    expect(isOwnerTourEligible('')).toBe(false);
  });
});

describe('shouldShowOwnerTourBanner', () => {
  const store: Record<string, string> = {};

  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => {
        store[key] = value;
      },
      removeItem: (key: string) => {
        delete store[key];
      },
      clear: () => {
        for (const key of Object.keys(store)) delete store[key];
      },
    });
    localStorage.removeItem(OWNER_TOUR_DONE_KEY);
    localStorage.removeItem(OWNER_TOUR_BANNER_DISMISSED_KEY);
  });

  it('mostra no dashboard quando elegível e tour não concluído', () => {
    expect(shouldShowOwnerTourBanner('dashboard', false, true)).toBe(true);
  });

  it('oculta fora do dashboard', () => {
    expect(shouldShowOwnerTourBanner('motos', false, true)).toBe(false);
  });

  it('oculta enquanto carrega', () => {
    expect(shouldShowOwnerTourBanner('dashboard', true, true)).toBe(false);
  });

  it('oculta após tour concluído', () => {
    markOwnerTourCompleted();
    expect(shouldShowOwnerTourBanner('dashboard', false, true)).toBe(false);
  });

  it('oculta após dismiss do banner', () => {
    dismissOwnerTourBanner();
    expect(shouldShowOwnerTourBanner('dashboard', false, true)).toBe(false);
  });

  it('oculta quando usuário não é elegível', () => {
    expect(shouldShowOwnerTourBanner('dashboard', false, false)).toBe(false);
  });
});