#!/usr/bin/env python3
"""Gera PNGs PWA a partir do favicon.svg (requer pillow + cairosvg ou renderização manual)."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "apps" / "motopay-frontend" / "public" / "favicon.svg"
OUT = ROOT / "apps" / "motopay-frontend" / "public" / "icons"


def _chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _write_png(path: Path, size: int, pixels: bytes) -> None:
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
    path.write_bytes(png)


def _blend(fg: tuple[int, int, int, int], bg: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b, a = fg
    if a >= 255:
        return (r, g, b)
    af = a / 255.0
    return (
        int(r * af + bg[0] * (1 - af)),
        int(g * af + bg[1] * (1 - af)),
        int(b * af + bg[2] * (1 - af)),
    )


def _render_icon(size: int) -> bytes:
    """Raster simples inspirado no favicon.svg (sem deps externas)."""
    bg = (2, 6, 23)
    primary = (99, 102, 241)
    accent = (16, 185, 129)
    card = (15, 23, 42)
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, px in (("pwa-192.png", 192), ("pwa-512.png", 512), ("apple-touch-icon.png", 180)):
        out = OUT / name
        _write_png(out, px, _render_icon(px))
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
