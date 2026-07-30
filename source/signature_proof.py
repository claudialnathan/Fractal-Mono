#!/usr/bin/env python3
"""Generate a large proof for CLN Mono's R, r, and K drawings."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


PROJECT = Path(__file__).resolve().parents[1]
FONT = PROJECT / "fonts" / "desktop" / "CLNMono-Variable.ttf"
OUTPUT = PROJECT / "specimens" / "CLNMono-RrK-proof.svg"
GLYPHS = "RrK"
WEIGHTS = (100, 200, 300, 400, 450, 500, 600, 700, 800)
OPTICAL_SIZES = ((9, "Text"), (14, "Auto"), (72, "Display"))
SCALE = 0.125
ADVANCE = 579


def glyph_path(font: TTFont, glyph_name: str) -> str:
    glyph_set = font.getGlyphSet()
    pen = SVGPathPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return pen.getCommands()


def glyph_run(
    font: TTFont,
    x: float,
    baseline: float,
    *,
    stroke: bool,
) -> str:
    cmap = font.getBestCmap()
    paths: list[str] = []
    for index, character in enumerate(GLYPHS):
        glyph_name = cmap[ord(character)]
        style = (
            'fill="none" stroke="#111111" stroke-width="1.6" '
            'stroke-linejoin="round" vector-effect="non-scaling-stroke"'
            if stroke
            else 'fill="#111111"'
        )
        paths.append(
            f'<path d="{escape(glyph_path(font, glyph_name))}" '
            f'transform="translate({x + index * ADVANCE * SCALE:.3f} '
            f'{baseline:.3f}) scale({SCALE:.4f} {-SCALE:.4f})" {style}/>'
        )
    return "\n".join(paths)


def main() -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    rows: list[str] = []
    columns = (50, 630, 1210)
    for column_x, (opsz, label) in zip(columns, OPTICAL_SIZES):
        rows.append(
            f'<text x="{column_x}" y="105" class="section">{label} · opsz {opsz}</text>'
        )
        rows.append(
            f'<text x="{column_x + 58}" y="145" class="caption">Filled</text>'
        )
        rows.append(
            f'<text x="{column_x + 330}" y="145" class="caption">Stroke / no fill</text>'
        )
        for row, weight in enumerate(WEIGHTS):
            font = TTFont(FONT)
            instantiateVariableFont(
                font,
                {"wght": weight, "opsz": opsz},
                inplace=True,
                optimize=True,
            )
            baseline = 245 + row * 180
            rows.append(
                f'<text x="{column_x}" y="{baseline - 48}" class="weight">{weight}</text>'
            )
            rows.append(glyph_run(font, column_x + 58, baseline, stroke=False))
            rows.append(glyph_run(font, column_x + 330, baseline, stroke=True))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1800" viewBox="0 0 1800 1800">
  <rect width="1800" height="1800" fill="#f5f4ef"/>
  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; fill: #111111; }}
    .title {{ font-size: 34px; font-weight: 600; }}
    .section {{ font-size: 22px; font-weight: 600; }}
    .caption, .weight {{ font-size: 16px; fill: #66665f; }}
  </style>
  <text x="36" y="54" class="title">CLN Mono 1.305 — R/r/K master proof</text>
  <path d="M600 80V1764M1180 80V1764" stroke="#d3d2cc"/>
  {"".join(rows)}
</svg>
"""
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
