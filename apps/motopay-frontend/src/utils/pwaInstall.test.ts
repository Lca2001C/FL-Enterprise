import { describe, expect, it } from 'vitest';
import {
  PWA_INSTALL_DISMISS_TTL_MS,
  dismissInstallPrompt,
  isIosDevice,
  isIosSafari,
  isMobileDevice,
  isStandalone,
  resolveInstallPromptMode,
  shouldShowInstallPrompt,
  wasInstallPromptDismissed,
} from './pwaInstall';

describe('pwaInstall', () => {
  it('detects mobile user agents', () => {
    expect(isMobileDevice('Mozilla/5.0 (Linux; Android 14)')).toBe(true);
    expect(isMobileDevice('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)')).toBe(true);
    expect(isMobileDevice('Mozilla/5.0 (Windows NT 10.0; Win64; x64)')).toBe(false);
  });

  it('detects iOS Safari vs Chrome on iOS', () => {
    const safari =
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';
    const chrome =
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1';
    expect(isIosDevice(safari)).toBe(true);
    expect(isIosSafari(safari)).toBe(true);
    expect(isIosSafari(chrome)).toBe(false);
  });

  it('tracks dismiss with TTL', () => {
    const storage = new Map<string, string>();
    const now = 1_700_000_000_000;
    dismissInstallPrompt(now, {
      setItem: (k, v) => storage.set(k, v),
    });
    expect(
      wasInstallPromptDismissed(now + 1000, {
        getItem: (k) => storage.get(k) ?? null,
      }),
    ).toBe(true);
    expect(
      wasInstallPromptDismissed(now + PWA_INSTALL_DISMISS_TTL_MS + 1, {
        getItem: (k) => storage.get(k) ?? null,
      }),
    ).toBe(false);
  });

  it('resolveInstallPromptMode prefers ios on Safari', () => {
    const safari =
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';
    expect(resolveInstallPromptMode({ userAgent: safari })).toBe('ios');
  });

  it('resolveInstallPromptMode uses native when prompt available', () => {
    expect(
      resolveInstallPromptMode({
        userAgent: 'Mozilla/5.0 (Linux; Android 14)',
        hasNativePrompt: true,
      }),
    ).toBe('native');
  });

  it('shouldShowInstallPrompt hides when standalone or dismissed', () => {
    const android = 'Mozilla/5.0 (Linux; Android 14)';
    expect(
      shouldShowInstallPrompt({
        userAgent: android,
        standalone: true,
      }),
    ).toBe(false);
    expect(
      shouldShowInstallPrompt({
        userAgent: android,
        dismissed: true,
      }),
    ).toBe(false);
  });

  it('shouldShowInstallPrompt shows on mobile Android', () => {
    expect(
      shouldShowInstallPrompt({
        userAgent: 'Mozilla/5.0 (Linux; Android 14)',
        standalone: false,
        dismissed: false,
        hasNativePrompt: true,
      }),
    ).toBe(true);
  });

  it('isStandalone is false without window matchMedia standalone', () => {
    expect(isStandalone()).toBe(false);
  });
});
