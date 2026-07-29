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
GLYPHS = "JjKMWStfilrOo0!?^;:*"
WEIGHTS = (100, 200, 300, 400, 450, 500, 600, 700, 800)
OPTICAL_SIZES = (
    (9, "Text"),
    (14, "Auto"),
    (72, "Display"),
)
SCALE = 0.057
PANEL_X = (100, 960)


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
    section_height = 1060
    for optical_index, (opsz, optical_label) in enumerate(OPTICAL_SIZES):
        section_y = 110 + optical_index * section_height
        rows.append(
            f'<text x="36" y="{section_y}" class="section-title">'
            f'{optical_label} · opsz {opsz}</text>'
        )
        rows.append(
            f'<text x="{PANEL_X[0]}" y="{section_y + 44}" class="caption">'
            "Filled</text>"
        )
        rows.append(
            f'<text x="{PANEL_X[1]}" y="{section_y + 44}" class="caption">'
            "Stroke / no fill</text>"
        )
        for weight_index, weight in enumerate(WEIGHTS):
            font = TTFont(FONT)
            instantiateVariableFont(
                font,
                {"wght": weight, "opsz": opsz},
                inplace=True,
                optimize=True,
            )
            baseline = section_y + 134 + weight_index * 98
            rows.append(
                f'<text x="36" y="{baseline - 14}" class="row-label">'
                f"{weight}</text>"
            )
            rows.append(row_paths(font, PANEL_X[0], baseline, "fill"))
            rows.append(row_paths(font, PANEL_X[1], baseline, "stroke"))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="3310" viewBox="0 0 1800 3310">
  <rect width="1800" height="3310" fill="#f5f4ef"/>
  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; fill: #111111; }}
    .title {{ font-size: 34px; font-weight: 600; }}
    .section-title {{ font-size: 22px; font-weight: 600; }}
    .caption {{ font-size: 17px; fill: #66665f; }}
    .row-label {{ font-size: 16px; fill: #66665f; }}
  </style>
  <text x="36" y="54" class="title">CLN Mono 1.303 — complete design-space outline proof</text>
  <path d="M900 92V3270" stroke="#d3d2cc"/>
  <path d="M36 1135H1764M36 2195H1764" stroke="#d3d2cc"/>
  {"".join(rows)}
</svg>
"""
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
