#!/usr/bin/env python3
"""Render R/r/K node correspondence at the sensitive weight extremes."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


PROJECT = Path(__file__).resolve().parents[1]
FONT = PROJECT / "fonts" / "desktop" / "FractalMono-Variable.ttf"
OUTPUT = PROJECT / "specimens" / "FractalMono-RrK-nodes.svg"
GLYPHS = ("R", "r", "K")
WEIGHTS = (100, 200, 450, 700, 800)
SCALE = 0.20
PANEL_WIDTH = 240
PANEL_HEIGHT = 320


def glyph_path(font: TTFont, name: str) -> str:
    glyph_set = font.getGlyphSet()
    pen = SVGPathPen(glyph_set)
    glyph_set[name].draw(pen)
    return pen.getCommands()


def contour_ranges(glyph) -> list[range]:
    starts = [0, *(endpoint + 1 for endpoint in glyph.endPtsOfContours[:-1])]
    return [
        range(start, endpoint + 1)
        for start, endpoint in zip(starts, glyph.endPtsOfContours)
    ]


def diagnostic_glyph(
    font: TTFont,
    name: str,
    x: float,
    baseline: float,
) -> str:
    glyph = font["glyf"][name]
    elements = [
        f'<path d="{escape(glyph_path(font, name))}" '
        f'transform="translate({x} {baseline}) scale({SCALE} {-SCALE})" '
        'fill="none" stroke="#111111" stroke-width="1.6" '
        'vector-effect="non-scaling-stroke"/>'
    ]

    for contour in contour_ranges(glyph):
        points = [glyph.coordinates[index] for index in contour]
        transformed = [
            (x + point_x * SCALE, baseline - point_y * SCALE)
            for point_x, point_y in points
        ]
        polyline = " ".join(
            f"{point_x:.2f},{point_y:.2f}"
            for point_x, point_y in (*transformed, transformed[0])
        )
        elements.append(
            f'<polyline points="{polyline}" fill="none" stroke="#4f7cff" '
            'stroke-width="0.8" opacity="0.55"/>'
        )
        for index, (point_x, point_y) in zip(contour, transformed):
            on_curve = bool(glyph.flags[index] & 1)
            elements.append(
                f'<circle cx="{point_x:.2f}" cy="{point_y:.2f}" '
                f'r="{3.1 if on_curve else 2.7}" '
                f'fill="{"#4f7cff" if on_curve else "#f5f4ef"}" '
                'stroke="#4f7cff" stroke-width="1"/>'
            )
    return "".join(elements)


def main() -> None:
    width = PANEL_WIDTH * len(WEIGHTS)
    height = 165 + PANEL_HEIGHT * len(GLYPHS)
    elements: list[str] = []
    for column, weight in enumerate(WEIGHTS):
        font = TTFont(FONT)
        instantiateVariableFont(
            font,
            {"wght": weight, "opsz": 14},
            inplace=True,
            optimize=True,
        )
        x = column * PANEL_WIDTH + 56
        elements.append(
            f'<text x="{column * PANEL_WIDTH + 24}" y="120" '
            f'class="weight">wght {weight}</text>'
        )
        for row, name in enumerate(GLYPHS):
            baseline = 350 + row * PANEL_HEIGHT
            elements.append(
                f'<text x="{column * PANEL_WIDTH + 24}" '
                f'y="{baseline - 205}" class="glyph">{name}</text>'
            )
            elements.append(diagnostic_glyph(font, name, x, baseline))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#f5f4ef"/>
  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; fill: #111111; }}
    .title {{ font-size: 26px; font-weight: 600; }}
    .weight {{ font-size: 16px; fill: #555550; }}
    .glyph {{ font-size: 15px; font-weight: 600; }}
  </style>
  <text x="24" y="42" class="title">Fractal Mono R/r/K — compatible node correspondence</text>
  <text x="24" y="68" class="weight">Filled nodes are on-curve; open nodes are quadratic controls.</text>
  {"".join(elements)}
</svg>
"""
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
