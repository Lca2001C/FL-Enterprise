import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const manifestPath = join(frontendRoot, 'dist', 'manifest.webmanifest');

describe('dist/manifest.webmanifest', () => {
  it.skipIf(!existsSync(manifestPath))(
    'includes required icons after npm run build',
    () => {
      const manifest = JSON.parse(readFileSync(manifestPath, 'utf8')) as {
        icons?: { src: string; sizes: string; purpose?: string }[];
        prefer_related_applications?: boolean;
        screenshots?: unknown[];
      };

      expect(manifest.prefer_related_applications).toBe(false);

      const icons = manifest.icons ?? [];
      const anySizes = icons
        .filter((i) => !i.purpose || i.purpose === 'any')
        .map((i) => i.sizes);
      expect(anySizes).toContain('192x192');
      expect(anySizes).toContain('512x512');
      expect(icons.some((i) => i.purpose === 'maskable')).toBe(true);
      expect(anySizes.length).toBeGreaterThanOrEqual(8);

      expect(manifest.screenshots?.length).toBeGreaterThanOrEqual(2);
    },
  );
});
