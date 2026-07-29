#!/usr/bin/env python3
"""Generate filled and stroked outline proofs for the signature glyph set."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


PROJECT = Path(__file__).resolve().parents[1]
FONT = PROJECT / "fonts" / "desktop" / "CLNMono-Variable.ttf"
OUTPUT = PROJECT / "specimens" / "CLNMono-outline-proof.svg"
GLYPHS = "JjKMWStij!?^;:*"
WEIGHTS = (100, 400, 800)
SCALE = 0.066
PANEL_X = (94, 820)


def glyph_path(font: TTFont, glyph_name: str) -> str:
    glyph_set = font.getGlyphSet()
    pen = SVGPathPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return pen.getCommands()


def row_paths(font: TTFont, x: float, baseline: float, mode: str) -> str:
    cmap = font.getBestCmap()
    advances = font["hmtx"].metrics
    paths: list[str] = []
    cursor = x
    for character in GLYPHS:
        glyph_name = cmap[ord(character)]
        path = glyph_path(font, glyph_name)
        style = (
            'fill="#111111"'
            if mode == "fill"
            else 'fill="none" stroke="#111111" stroke-width="1.8" '
            'stroke-linejoin="round" vector-effect="non-scaling-stroke"'
        )
        paths.append(
            f'<path d="{escape(path)}" transform="translate({cursor:.3f} {baseline:.3f}) '
            f'scale({SCALE:.4f} {-SCALE:.4f})" {style}/>'
        )
        cursor += advances[glyph_name][0] * SCALE
    return "\n".join(paths)


def main() -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    rows: list[str] = []
    for index, weight in enumerate(WEIGHTS):
        font = TTFont(FONT)
        instantiateVariableFont(
            font,
            {"wght": weight, "opsz": 14},
            inplace=True,
            optimize=True,
        )
        baseline = 245 + index * 178
        rows.append(
            f'<text x="36" y="{baseline - 28}" class="row-label">{weight}</text>'
        )
        rows.append(row_paths(font, PANEL_X[0], baseline, "fill"))
        rows.append(row_paths(font, PANEL_X[1], baseline, "stroke"))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="760" viewBox="0 0 1600 760">
  <rect width="1600" height="760" fill="#f5f4ef"/>
  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; fill: #111111; }}
    .title {{ font-size: 34px; font-weight: 600; }}
    .caption {{ font-size: 17px; fill: #66665f; }}
    .row-label {{ font-size: 16px; fill: #66665f; }}
  </style>
  <text x="36" y="54" class="title">CLN Mono 1.300 — outline integrity</text>
  <text x="94" y="108" class="caption">Filled</text>
  <text x="820" y="108" class="caption">Stroke / no fill</text>
  <path d="M760 92V708" stroke="#d3d2cc"/>
  {"".join(rows)}
</svg>
"""
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
