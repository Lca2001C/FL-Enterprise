export const PWA_INSTALL_DISMISS_KEY = 'motopay-pwa-install-dismissed';
export const PWA_INSTALL_DISMISS_TTL_MS = 7 * 24 * 60 * 60 * 1000;

export type InstallPromptMode = 'native' | 'ios' | 'manual';

export function isStandalone(): boolean {
  if (typeof window === 'undefined') return false;
  const nav = window.navigator as Navigator & { standalone?: boolean };
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    nav.standalone === true
  );
}

export function isMobileDevice(userAgent = ''): boolean {
  const ua = userAgent || (typeof navigator !== 'undefined' ? navigator.userAgent : '');
  return /Android|iPhone|iPad|iPod|Mobile/i.test(ua);
}

export function isIosDevice(userAgent = ''): boolean {
  const ua = userAgent || (typeof navigator !== 'undefined' ? navigator.userAgent : '');
  if (/iPhone|iPad|iPod/i.test(ua)) return true;
  // iPadOS 13+ em modo "desktop" reporta "Macintosh" mas tem toque
  if (
    /Macintosh/i.test(ua) &&
    typeof navigator !== 'undefined' &&
    navigator.maxTouchPoints > 1
  ) return true;
  return false;
}

/** Safari no iOS/iPadOS (único que suporta Add to Home Screen nativo). */
export function isIosSafari(userAgent = ''): boolean {
  const ua = userAgent || (typeof navigator !== 'undefined' ? navigator.userAgent : '');
  if (!isIosDevice(ua)) return false;
  // Chrome iOS, Firefox iOS, Edge iOS, Opera iOS, DuckDuckGo
  return !/CriOS|FxiOS|EdgiOS|OPiOS|DuckDuckGo/i.test(ua);
}

export function wasInstallPromptDismissed(
  now = Date.now(),
  storage: Pick<Storage, 'getItem'> = typeof localStorage !== 'undefined' ? localStorage : { getItem: () => null },
): boolean {
  const raw = storage.getItem(PWA_INSTALL_DISMISS_KEY);
  if (!raw) return false;
  const dismissedAt = Number(raw);
  if (!Number.isFinite(dismissedAt)) return false;
  return now - dismissedAt < PWA_INSTALL_DISMISS_TTL_MS;
}

export function dismissInstallPrompt(
  now = Date.now(),
  storage: Pick<Storage, 'setItem'> = typeof localStorage !== 'undefined' ? localStorage : { setItem: () => undefined },
): void {
  storage.setItem(PWA_INSTALL_DISMISS_KEY, String(now));
}

export function resolveInstallPromptMode(
  options: {
    userAgent?: string;
    hasNativePrompt?: boolean;
    isSecureContext?: boolean;
  } = {},
): InstallPromptMode | null {
  const ua = options.userAgent ?? (typeof navigator !== 'undefined' ? navigator.userAgent : '');
  if (!isMobileDevice(ua)) return null;
  if (isIosSafari(ua)) return 'ios';
  if (options.hasNativePrompt) return 'native';
  return 'manual';
}

export function shouldShowInstallPrompt(
  options: {
    userAgent?: string;
    standalone?: boolean;
    dismissed?: boolean;
    hasNativePrompt?: boolean;
    forceManual?: boolean;
  } = {},
): boolean {
  const ua = options.userAgent ?? (typeof navigator !== 'undefined' ? navigator.userAgent : '');
  const standalone = options.standalone ?? isStandalone();
  const dismissed = options.dismissed ?? wasInstallPromptDismissed();
  if (standalone || dismissed) return false;
  if (!isMobileDevice(ua)) return false;
  if (isIosSafari(ua)) return true;
  if (options.hasNativePrompt) return true;
  if (options.forceManual) return true;
  return true;
}
