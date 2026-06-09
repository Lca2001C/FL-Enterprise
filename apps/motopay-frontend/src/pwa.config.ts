/** Ícones e metadados PWA compartilhados entre vite.config e testes. */

export const PWA_ICON_SIZES = [72, 96, 120, 128, 144, 152, 167, 192, 384, 512] as const;

export const PWA_MANIFEST_ICONS = [
  ...PWA_ICON_SIZES.map((size) => ({
    src: `icons/pwa-${size}.png`,
    sizes: `${size}x${size}`,
    type: 'image/png' as const,
    purpose: 'any' as const,
  })),
  {
    src: 'icons/pwa-512-maskable.png',
    sizes: '512x512',
    type: 'image/png' as const,
    purpose: 'maskable' as const,
  },
];

export const PWA_SCREENSHOTS = [
  {
    src: 'screenshots/screenshot-wide.png',
    sizes: '1280x720',
    type: 'image/png' as const,
    form_factor: 'wide' as const,
    label: 'Painel MotoPay — visão desktop',
  },
  {
    src: 'screenshots/screenshot-narrow.png',
    sizes: '720x1280',
    type: 'image/png' as const,
    form_factor: 'narrow' as const,
    label: 'Painel MotoPay — visão mobile',
  },
];

/** Media queries para apple-touch-startup-image (portrait + landscape). */
export const IOS_SPLASH_LINKS: { href: string; media: string }[] = [
  // ── iPhone (portrait) ────────────────────────────────────────────────────
  { href: '/splash/apple-splash-750x1334.png',
    media: '(device-width: 375px) and (device-height: 667px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1242x2208.png',
    media: '(device-width: 414px) and (device-height: 736px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1125x2436.png',
    media: '(device-width: 375px) and (device-height: 812px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)' },
  { href: '/splash/apple-splash-828x1792.png',
    media: '(device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1170x2532.png',
    media: '(device-width: 390px) and (device-height: 844px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1284x2778.png',
    media: '(device-width: 428px) and (device-height: 926px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1179x2556.png',
    media: '(device-width: 393px) and (device-height: 852px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1290x2796.png',
    media: '(device-width: 430px) and (device-height: 932px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1206x2622.png',
    media: '(device-width: 402px) and (device-height: 874px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1320x2868.png',
    media: '(device-width: 440px) and (device-height: 956px) and (-webkit-device-pixel-ratio: 3) and (orientation: portrait)' },
  // ── iPad (portrait) ──────────────────────────────────────────────────────
  { href: '/splash/apple-splash-1536x2048.png',
    media: '(device-width: 768px) and (device-height: 1024px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1620x2160.png',
    media: '(device-width: 810px) and (device-height: 1080px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1488x2266.png',
    media: '(device-width: 744px) and (device-height: 1133px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1640x2360.png',
    media: '(device-width: 820px) and (device-height: 1180px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)' },
  { href: '/splash/apple-splash-1668x2388.png',
    media: '(device-width: 834px) and (device-height: 1194px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)' },
  { href: '/splash/apple-splash-2048x2732.png',
    media: '(device-width: 1024px) and (device-height: 1366px) and (-webkit-device-pixel-ratio: 2) and (orientation: portrait)' },
  // ── iPad (landscape) ─────────────────────────────────────────────────────
  { href: '/splash/apple-splash-2048x1536.png',
    media: '(device-width: 768px) and (device-height: 1024px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)' },
  { href: '/splash/apple-splash-2160x1620.png',
    media: '(device-width: 810px) and (device-height: 1080px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)' },
  { href: '/splash/apple-splash-2266x1488.png',
    media: '(device-width: 744px) and (device-height: 1133px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)' },
  { href: '/splash/apple-splash-2360x1640.png',
    media: '(device-width: 820px) and (device-height: 1180px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)' },
  { href: '/splash/apple-splash-2388x1668.png',
    media: '(device-width: 834px) and (device-height: 1194px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)' },
  { href: '/splash/apple-splash-2732x2048.png',
    media: '(device-width: 1024px) and (device-height: 1366px) and (-webkit-device-pixel-ratio: 2) and (orientation: landscape)' },
];
