"""Build a review-only static from the Regular master by adding ink.

Installs under its own family name so it sits alongside the real family instead of
replacing it: the point is to compare the two on screen, not to ship. Nothing here
touches the release build.

    python3 source/lab_build.py --weight 800 --install
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from fontTools.ttLib import TTFont

import offset

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fonts" / "desktop" / "FractalMono-Regular.ttf"
OUT = ROOT / "build" / "lab"

REGULAR_STEM = 80.0
FAMILY = "Fractal Lab"


ANCHORS = (32.0, 80.0, 150.0)


def stem_for(weight: float) -> float:
    """Linear in both halves, so every named step is the same absolute change."""
    if weight <= 400:
        return ANCHORS[0] + (weight - 100) * (ANCHORS[1] - ANCHORS[0]) / 300.0
    return ANCHORS[1] + (weight - 400) * (ANCHORS[2] - ANCHORS[1]) / 400.0


def build(weight: float) -> TTFont:
    font = TTFont(SOURCE, lazy=False)
    glyf = font["glyf"]
    distance = (stem_for(weight) - REGULAR_STEM) / 2
    hmtx = font["hmtx"].metrics

    if distance == 0:
        _rename(font, weight)
        font["OS/2"].usWeightClass = int(weight)
        return font

    for name in font.getGlyphOrder():
        glyph = glyf[name]
        # A composite carries no coordinates of its own; it is offset by way of
        # the outline its components draw, and comes back simple.
        if glyph.numberOfContours == 0:
            continue
        advance = hmtx[name][0]
        try:
            grown = offset.offset_glyph(glyph, glyf, distance)
        except Exception:
            continue                      # leave anything Skia refuses untouched
        if grown.numberOfContours <= 0 or not len(grown.coordinates):
            continue
        glyf[name] = grown
        grown.recalcBounds(glyf)
        hmtx[name] = (advance, grown.xMin)

    _rename(font, weight)
    font["OS/2"].usWeightClass = int(weight)
    font["head"].fontRevision = 1.0
    return font


def _rename(font: TTFont, weight: float) -> None:
    style = {
        100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular",
        450: "Book", 500: "Medium", 600: "SemiBold", 700: "Bold",
        800: "ExtraBold",
    }.get(int(weight), f"W{int(weight)}")
    full = f"{FAMILY} {style}"
    postscript = f"{FAMILY.replace(' ', '')}-{style}"
    legacy_style = style if style in {"Regular", "Bold", "Italic"} else "Regular"
    legacy_family = FAMILY if style in {"Regular", "Bold"} else full

    name = font["name"]
    for record in list(name.names):
        if record.nameID in {1, 2, 3, 4, 6, 16, 17}:
            name.removeNames(record.nameID, record.platformID,
                             record.platEncID, record.langID)
    for name_id, value in (
        (1, legacy_family), (2, legacy_style), (3, f"{postscript};lab"),
        (4, full), (6, postscript), (16, FAMILY), (17, style),
    ):
        name.setName(value, name_id, 3, 1, 0x409)
        name.setName(value, name_id, 1, 0, 0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", type=float, default=800)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    font = build(args.weight)
    style = font["name"].getDebugName(17)
    path = OUT / f"FractalLab-{style}.ttf"
    font.save(path)
    print(f"wrote {path}")

    if args.install:
        target = Path.home() / "Library" / "Fonts" / path.name
        shutil.copy2(path, target)
        print(f"installed {target}")


if __name__ == "__main__":
    main()
