#!/usr/bin/env node
/**
 * Gera todas as splash screens para iOS/iPadOS.
 *
 * Uso:
 *   node scripts/generate-splash.js
 *
 * Lê:  public/icons/pwa-512.png  (ou pwa-512-maskable.png como fallback)
 * Gera: public/splash/apple-splash-{W}x{H}.png
 */

import sharp from 'sharp';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const ROOT = path.join(__dirname, '..');
const ICONS_DIR = path.join(ROOT, 'public', 'icons');
const SPLASH_DIR = path.join(ROOT, 'public', 'splash');

// Cor de fundo da splash — igual ao background_color do manifest
const BG = { r: 10, g: 10, b: 15, alpha: 1 };

// O ícone ocupa 25% da menor dimensão da splash
const ICON_RATIO = 0.25;

// Todas as dimensões físicas necessárias (portrait)
const SIZES = [
  // ── iPhone ──────────────────────────────────────────────────────────────
  { w: 750,  h: 1334, label: 'iPhone 8 / SE 1ª gen'          },
  { w: 1242, h: 2208, label: 'iPhone 8 Plus'                  },
  { w: 1125, h: 2436, label: 'iPhone X / XS / 11 Pro'         },
  { w: 828,  h: 1792, label: 'iPhone XR / 11'                 },
  { w: 1170, h: 2532, label: 'iPhone 12 / 13 / 14'            },
  { w: 1284, h: 2778, label: 'iPhone 12/13/14 Pro Max'        },
  { w: 1179, h: 2556, label: 'iPhone 14 Pro / 15 / 15 Pro'    },
  { w: 1290, h: 2796, label: 'iPhone 15 Pro Max / 16 Plus'    },
  { w: 1206, h: 2622, label: 'iPhone 16 / 16 Pro'             },
  { w: 1320, h: 2868, label: 'iPhone 16 Pro Max'              },
  // ── iPad (portrait) ─────────────────────────────────────────────────────
  { w: 1536, h: 2048, label: 'iPad mini 5ª / iPad Air 3ª'    },
  { w: 1620, h: 2160, label: 'iPad 9ª gen'                    },
  { w: 1488, h: 2266, label: 'iPad mini 6ª gen'               },
  { w: 1640, h: 2360, label: 'iPad Air 5ª / iPad 10ª gen'     },
  { w: 1668, h: 2388, label: 'iPad Pro 11" 3ª/4ª gen'         },
  { w: 2048, h: 2732, label: 'iPad Pro 12.9" 5ª/6ª gen'       },
  // ── iPad (landscape) ────────────────────────────────────────────────────
  { w: 2048, h: 1536, label: 'iPad mini 5ª / Air 3ª landscape'},
  { w: 2160, h: 1620, label: 'iPad 9ª gen landscape'          },
  { w: 2266, h: 1488, label: 'iPad mini 6ª landscape'         },
  { w: 2360, h: 1640, label: 'iPad Air 5ª / 10ª landscape'    },
  { w: 2388, h: 1668, label: 'iPad Pro 11" landscape'         },
  { w: 2732, h: 2048, label: 'iPad Pro 12.9" landscape'       },
];

async function iconBuffer(size) {
  const src =
    fs.existsSync(path.join(ICONS_DIR, 'pwa-512.png'))
      ? path.join(ICONS_DIR, 'pwa-512.png')
      : path.join(ICONS_DIR, 'pwa-512-maskable.png');
  return sharp(src).resize(size, size, { fit: 'contain', background: BG }).toBuffer();
}

async function main() {
  fs.mkdirSync(SPLASH_DIR, { recursive: true });

  for (const { w, h, label } of SIZES) {
    const iconSize = Math.round(Math.min(w, h) * ICON_RATIO);
    const icon = await iconBuffer(iconSize);

    const file = path.join(SPLASH_DIR, `apple-splash-${w}x${h}.png`);
    await sharp({ create: { width: w, height: h, channels: 4, background: BG } })
      .composite([{ input: icon, gravity: 'centre' }])
      .png({ compressionLevel: 8 })
      .toFile(file);

    console.log(`✅  ${w}x${h}  ${label}`);
  }

  console.log('\nTodos os splash screens gerados em public/splash/');
}

main().catch((e) => { console.error('❌', e.message); process.exit(1); });
