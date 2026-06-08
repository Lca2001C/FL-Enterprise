#!/usr/bin/env python3
"""Gera PNGs PWA, favicon.ico, splash iOS e screenshots (sem deps externas)."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "apps" / "motopay-frontend" / "public"
ICONS = PUBLIC / "icons"
SPLASH = PUBLIC / "splash"
SCREENSHOTS = PUBLIC / "screenshots"

PWA_SIZES = (72, 96, 120, 128, 144, 152, 167, 192, 384, 512)

# iPhone portrait splash (width x height) — apple-touch-startup-image
IOS_SPLASHES: tuple[tuple[str, int, int], ...] = (
    ("apple-splash-1170x2532.png", 1170, 2532),   # iPhone 14 / 16
    ("apple-splash-1179x2556.png", 1179, 2556),   # iPhone 14 Pro / 15 / 16
    ("apple-splash-1206x2622.png", 1206, 2622),   # iPhone 16 Pro
    ("apple-splash-1284x2778.png", 1284, 2778),   # iPhone 14 Plus / 15 Plus
    ("apple-splash-1290x2796.png", 1290, 2796),   # iPhone 14 Pro Max / 15 Pro Max / 16 Plus
    ("apple-splash-1320x2868.png", 1320, 2868),   # iPhone 16 Pro Max
    ("apple-splash-750x1334.png", 750, 1334),
    ("apple-splash-1242x2208.png", 1242, 2208),
    ("apple-splash-828x1792.png", 828, 1792),
    ("apple-splash-1125x2436.png", 1125, 2436),
)


def _chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _png_bytes(size: int, pixels: bytes) -> bytes:
    raw = b""
    row = size * 4
    for y in range(size):
        raw += b"\x00" + pixels[y * row : (y + 1) * row]
    compressed = zlib.compress(raw, 9)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", compressed)
    png += _chunk(b"IEND", b"")
    return png


def _write_png(path: Path, size: int, pixels: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_png_bytes(size, pixels))


def _write_png_rect(path: Path, width: int, height: int, pixels: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = b""
    row = width * 4
    for y in range(height):
        raw += b"\x00" + pixels[y * row : (y + 1) * row]
    compressed = zlib.compress(raw, 9)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", compressed)
    png += _chunk(b"IEND", b"")
    path.write_bytes(png)


def _render_icon(size: int) -> bytes:
    """Raster simples inspirado no favicon.svg."""
    bg = (10, 10, 15)
    primary = (212, 165, 116)
    accent = (92, 191, 138)
    card = (20, 17, 26)
    pixels = bytearray(size * size * 4)

    def set_px(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < size and 0 <= y < size:
            i = (y * size + x) * 4
            pixels[i : i + 3] = bytes(color)
            pixels[i + 3] = 255

    def fill_circle(cx: float, cy: float, r: float, color: tuple[int, int, int], fill: bool = True) -> None:
        r2 = r * r
        y0 = max(0, int(cy - r - 1))
        y1 = min(size, int(cy + r + 2))
        x0 = max(0, int(cx - r - 1))
        x1 = min(size, int(cx + r + 2))
        for y in range(y0, y1):
            for x in range(x0, x1):
                d = (x - cx) ** 2 + (y - cy) ** 2
                if fill and d <= r2:
                    set_px(x, y, color)
                elif not fill and abs(d - r2) < r * 2.5:
                    set_px(x, y, color)

    def fill_round_rect(x: int, y: int, w: int, h: int, rad: int, color: tuple[int, int, int]) -> None:
        for py in range(y, y + h):
            for px in range(x, x + w):
                inside = True
                if px < x + rad and py < y + rad:
                    inside = (px - (x + rad)) ** 2 + (py - (y + rad)) ** 2 <= rad * rad
                elif px >= x + w - rad and py < y + rad:
                    inside = (px - (x + w - rad - 1)) ** 2 + (py - (y + rad)) ** 2 <= rad * rad
                elif px < x + rad and py >= y + h - rad:
                    inside = (px - (x + rad)) ** 2 + (py - (y + h - rad - 1)) ** 2 <= rad * rad
                elif px >= x + w - rad and py >= y + h - rad:
                    inside = (px - (x + w - rad - 1)) ** 2 + (py - (y + h - rad - 1)) ** 2 <= rad * rad
                if inside:
                    set_px(px, py, color)

    s = size / 512.0
    for y in range(size):
        for x in range(size):
            set_px(x, y, bg)

    fill_round_rect(0, 0, size, size, int(112 * s), bg)
    fill_circle(size / 2, size / 2, 200 * s, card)
    fill_circle(size / 2, size / 2, 200 * s, primary, fill=False)

    fill_circle(168 * s, 300 * s, 52 * s, primary, fill=False)
    fill_circle(168 * s, 300 * s, 18 * s, primary)
    fill_circle(340 * s, 300 * s, 52 * s, primary, fill=False)
    fill_circle(340 * s, 300 * s, 18 * s, primary)

    for y in range(int(210 * s), int(300 * s)):
        for x in range(int(120 * s), int(420 * s)):
            t = (y - 210 * s) / (90 * s)
            left = 120 * s + t * 48 * s
            right = 400 * s + t * 20 * s
            if left <= x <= right:
                set_px(x, y, primary)

    fill_round_rect(int(300 * s), int(118 * s), int(120 * s), int(72 * s), int(16 * s), accent)

    return bytes(pixels)


def _render_icon_maskable(size: int) -> bytes:
    inner = int(size * 0.8)
    inner_pixels = _render_icon(inner)
    bg = (10, 10, 15)
    outer = bytearray(size * size * 4)
    offset = (size - inner) // 2
    for y in range(size):
        for x in range(size):
            i = (y * size + x) * 4
            outer[i : i + 3] = bytes(bg)
            outer[i + 3] = 255
    for y in range(inner):
        for x in range(inner):
            src = (y * inner + x) * 4
            dst = ((y + offset) * size + (x + offset)) * 4
            outer[dst : dst + 4] = inner_pixels[src : src + 4]
    return bytes(outer)


def _blit_rgba(
    canvas: bytearray,
    canvas_w: int,
    canvas_h: int,
    src: bytes,
    src_size: int,
    dst_x: int,
    dst_y: int,
) -> None:
    for y in range(src_size):
        for x in range(src_size):
            sx = x
            sy = y
            dx = dst_x + x
            dy = dst_y + y
            if dx < 0 or dy < 0 or dx >= canvas_w or dy >= canvas_h:
                continue
            si = (sy * src_size + sx) * 4
            di = (dy * canvas_w + dx) * 4
            alpha = src[si + 3] / 255.0
            if alpha <= 0:
                continue
            for c in range(3):
                bg = canvas[di + c]
                fg = src[si + c]
                canvas[di + c] = int(fg * alpha + bg * (1 - alpha))
            canvas[di + 3] = 255


def _render_splash(width: int, height: int) -> bytes:
    bg = (10, 10, 15)
    pixels = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            i = (y * width + x) * 4
            pixels[i : i + 3] = bytes(bg)
            pixels[i + 3] = 255
    icon_size = int(min(width, height) * 0.22)
    icon = _render_icon(icon_size)
    x = (width - icon_size) // 2
    y = int(height * 0.38) - icon_size // 2
    _blit_rgba(pixels, width, height, icon, icon_size, x, y)
    return bytes(pixels)


def _render_screenshot(width: int, height: int) -> bytes:
    bg = (10, 10, 15)
    card = (20, 17, 26)
    pixels = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            i = (y * width + x) * 4
            pixels[i : i + 3] = bytes(bg)
            pixels[i + 3] = 255
    pad = int(min(width, height) * 0.08)
    for y in range(pad, height - pad):
        for x in range(pad, width - pad):
            i = (y * width + x) * 4
            pixels[i : i + 3] = bytes(card)
            pixels[i + 3] = 255
    icon_size = int(min(width, height) * 0.18)
    icon = _render_icon(icon_size)
    x = (width - icon_size) // 2
    y = (height - icon_size) // 2
    _blit_rgba(pixels, width, height, icon, icon_size, x, y)
    return bytes(pixels)


def _write_ico(path: Path, sizes: tuple[int, ...]) -> None:
    pngs = [_png_bytes(size, _render_icon(size)) for size in sizes]
    num = len(pngs)
    header = struct.pack("<HHH", 0, 1, num)
    entries = b""
    images = b""
    offset = 6 + 16 * num
    for size, png in zip(sizes, pngs, strict=True):
        w = size if size < 256 else 0
        h = w
        entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
        images += png
    path.write_bytes(header + entries + images)


def main() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    SPLASH.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)

    for px in PWA_SIZES:
        out = ICONS / f"pwa-{px}.png"
        _write_png(out, px, _render_icon(px))
        print(f"Wrote {out}")

    _write_png(ICONS / "apple-touch-icon.png", 180, _render_icon(180))
    print(f"Wrote {ICONS / 'apple-touch-icon.png'}")

    # iPad-specific touch icons
    _write_png(ICONS / "apple-touch-icon-120.png", 120, _render_icon(120))
    _write_png(ICONS / "apple-touch-icon-167.png", 167, _render_icon(167))
    print("Wrote apple-touch-icon-120.png and apple-touch-icon-167.png")

    maskable = ICONS / "pwa-512-maskable.png"
    _write_png(maskable, 512, _render_icon_maskable(512))
    print(f"Wrote {maskable}")

    for name, px in (("favicon-16.png", 16), ("favicon-32.png", 32)):
        out = PUBLIC / name
        _write_png(out, px, _render_icon(px))
        print(f"Wrote {out}")

    favicon_ico = PUBLIC / "favicon.ico"
    _write_ico(favicon_ico, (16, 32, 48))
    print(f"Wrote {favicon_ico}")

    for name, w, h in IOS_SPLASHES:
        out = SPLASH / name
        _write_png_rect(out, w, h, _render_splash(w, h))
        print(f"Wrote {out}")

    _write_png_rect(SCREENSHOTS / "screenshot-wide.png", 1280, 720, _render_screenshot(1280, 720))
    _write_png_rect(SCREENSHOTS / "screenshot-narrow.png", 720, 1280, _render_screenshot(720, 1280))
    print(f"Wrote {SCREENSHOTS / 'screenshot-wide.png'}")
    print(f"Wrote {SCREENSHOTS / 'screenshot-narrow.png'}")


if __name__ == "__main__":
    main()
