"""Renderuje ikonę produktu sklepowego (Play In-app product) z Pillow.

Bez zależności od cairosvg — rysuje grafikę liniową zaworu dekompresyjnego
w stylu ikony aplikacji (gradient granat→błękit, jasne linie).

Wynik: 1024×1024 PNG, 32-bit RGBA — zgodny ze specyfikacją Google Play
(format 1:1, boki 512–1080 px, 32-bitowy PNG, do 8 MB, bez tekstu/marki).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).with_name("product-module_valves.png")

VIEW = 512          # przestrzeń projektowa (jak icon.svg)
SIZE = 1024         # docelowy rozmiar PNG (w zakresie 512–1080)
SS = 4              # supersampling dla gładkich krawędzi
CANVAS = SIZE * SS
SCALE = CANVAS / VIEW

TOP = (0x23, 0x45, 0x75)
BOTTOM = (0x36, 0xa8, 0xdf)
LINE = (0xea, 0xf6, 0xff, 0xff)
STROKE = 16         # grubość linii w przestrzeni 512 (jak icon.svg)


def _s(v: float) -> float:
    return v * SCALE


def _gradient() -> Image.Image:
    img = Image.new("RGBA", (CANVAS, CANVAS))
    px = img.load()
    for y in range(CANVAS):
        t = y / (CANVAS - 1)
        r = round(TOP[0] + (BOTTOM[0] - TOP[0]) * t)
        g = round(TOP[1] + (BOTTOM[1] - TOP[1]) * t)
        b = round(TOP[2] + (BOTTOM[2] - TOP[2]) * t)
        for x in range(CANVAS):
            px[x, y] = (r, g, b, 255)
    return img


def _dot(draw: ImageDraw.ImageDraw, x: float, y: float, rad: float) -> None:
    draw.ellipse([x - rad, y - rad, x + rad, y + rad], fill=LINE)


def _polyline(draw, pts, closed=False) -> None:
    w = _s(STROKE)
    rad = w / 2
    p = [(_s(x), _s(y)) for x, y in pts]
    if closed:
        p = p + [p[0]]
    for (x1, y1), (x2, y2) in zip(p, p[1:]):
        draw.line([x1, y1, x2, y2], fill=LINE, width=round(w))
    for x, y in p:                      # zaokrąglone łączenia/zakończenia
        _dot(draw, x, y, rad)


def _circle(draw, cx, cy, r) -> None:
    w = _s(STROKE)
    cx, cy, r = _s(cx), _s(cy), _s(r)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=LINE, width=round(w))


def main() -> None:
    img = _gradient()
    d = ImageDraw.Draw(img)

    # rura
    _polyline(d, [(64, 322), (448, 322)])
    # korpus zaworu (kokarda / globe valve)
    _polyline(d, [(188, 282), (188, 362), (256, 322), (324, 362), (324, 282), (256, 322)], closed=True)
    # trzpień
    _polyline(d, [(256, 322), (256, 172)])
    # pokrętło
    _circle(d, 256, 150, 48)
    _polyline(d, [(208, 150), (304, 150)])
    # strzałki odprężania (dekompresja)
    _polyline(d, [(150, 250), (150, 150)])
    _polyline(d, [(132, 176), (150, 150), (168, 176)])
    _polyline(d, [(362, 250), (362, 150)])
    _polyline(d, [(344, 176), (362, 150), (380, 176)])

    out = img.resize((SIZE, SIZE), Image.LANCZOS)
    out.save(OUT, "PNG")
    print(f"zapisano {OUT} ({out.size[0]}x{out.size[1]}, mode={out.mode})")


if __name__ == "__main__":
    main()
