import { describe, expect, it } from 'vitest';
import {
  IOS_SPLASH_LINKS,
  PWA_ICON_SIZES,
  PWA_MANIFEST_ICONS,
  PWA_SCREENSHOTS,
} from './pwa.config';

describe('pwa.config', () => {
  it('lists all standard icon sizes for manifest', () => {
    expect(PWA_ICON_SIZES).toEqual([72, 96, 120, 128, 144, 152, 167, 192, 384, 512]);
    for (const size of PWA_ICON_SIZES) {
      expect(PWA_MANIFEST_ICONS).toContainEqual({
        src: `icons/pwa-${size}.png`,
        sizes: `${size}x${size}`,
        type: 'image/png',
        purpose: 'any',
      });
    }
  });

  it('includes maskable icon required by Lighthouse and Android', () => {
    expect(PWA_MANIFEST_ICONS).toContainEqual({
      src: 'icons/pwa-512-maskable.png',
      sizes: '512x512',
      type: 'image/png',
      purpose: 'maskable',
    });
  });

  it('includes 192 and 512 any-purpose icons', () => {
    const sizes = PWA_MANIFEST_ICONS.filter((i) => i.purpose === 'any').map(
      (i) => i.sizes,
    );
    expect(sizes).toContain('192x192');
    expect(sizes).toContain('512x512');
  });

  it('defines wide and narrow screenshots for store prep', () => {
    expect(PWA_SCREENSHOTS).toHaveLength(2);
    expect(PWA_SCREENSHOTS.map((s) => s.form_factor)).toEqual(['wide', 'narrow']);
  });

  it('defines iOS splash startup images with media queries', () => {
    expect(IOS_SPLASH_LINKS.length).toBeGreaterThanOrEqual(6);
    for (const link of IOS_SPLASH_LINKS) {
      expect(link.href).toMatch(/^\/splash\/apple-splash-/);
      // Setup iOS completo inclui portrait (iPhone/iPad) e landscape (iPad).
      expect(link.media).toMatch(/orientation: (portrait|landscape)/);
    }
  });
});
