#!/usr/bin/env python3
"""Release gates for Fractal Mono's registered width axis.

The normal-width geometry suite proves the established design. This companion
suite proves that ``wdth`` changes line length without stretching stroke weight,
moving vertical geometry, breaking monospacing, or introducing outline defects
between the authored masters.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

import validate_geometry as geometry
from width_axis import (
    WIDTH_DEFAULT,
    WIDTH_MAX,
    WIDTH_MIN,
    advance_at_width,
)


PROJECT = Path(__file__).resolve().parents[1]
VARIABLE = PROJECT / "fonts" / "desktop" / "FractalMono-Variable.ttf"

WEIGHT_SAMPLES = (
    100,
    150,
    200,
    250,
    300,
    350,
    400,
    450,
    461,
    500,
    550,
    600,
    620,
    700,
    800,
)
OPTICAL_SAMPLES = (9, 14, 72)
WIDTH_SAMPLES = (85, 90, 95, 100, 105, 110, 115)
DOT_GLYPHS = (
    "period",
    "colon",
    "colon.case",
    "exclam",
    "question",
    "i",
    "j",
    "semicolon",
    "semicolon.case",
)
REACH_PROBES = ("A", "H", "M", "O", "W", "n", "o", "r", "zero")

# Multi-contour punctuation and letters can carry a detached dot, slash, or
# ogonek to the cell edge. They receive the same tolerance already granted to
# composite accents; the primary one-contour drawing retains the tighter gate.
MULTI_CONTOUR_CELL_TOLERANCE = geometry.COMPOSITE_CELL_TOLERANCE


def instance(path: str, weight: float, optical: float, width: float) -> TTFont:
    return instantiateVariableFont(
        TTFont(path),
        {
            "wght": weight,
            "wdth": width,
            "opsz": optical,
        },
        inplace=True,
        optimize=True,
    )


def encoded_latin(font: TTFont) -> list[str]:
    cmap = font.getBestCmap()
    return sorted(
        {
            cmap[codepoint]
            for codepoint in (
                *range(0x21, 0x7F),
                *range(0xA1, 0x180),
            )
            if codepoint in cmap
        }
    )


def vertical_signature(font: TTFont, glyph_name: str) -> tuple[float, ...]:
    coordinates, _, _ = font["glyf"][glyph_name].getCoordinates(font["glyf"])
    return tuple(round(y, 3) for _, y in coordinates)


def vertical_metrics(font: TTFont) -> tuple[int, ...]:
    return (
        font["hhea"].ascent,
        font["hhea"].descent,
        font["hhea"].lineGap,
        font["OS/2"].sTypoAscender,
        font["OS/2"].sTypoDescender,
        font["OS/2"].sTypoLineGap,
        font["OS/2"].usWinAscent,
        font["OS/2"].usWinDescent,
    )


def diagonal_ratios(font: TTFont) -> dict[str, float]:
    stem = geometry.measure_stem(font)
    x_height = font["OS/2"].sxHeight
    ratios = {}
    for glyph_name, (low, high, index) in geometry.DIAGONAL_PROBES.items():
        base_height = (
            x_height
            if glyph_name in geometry.LOWERCASE_PROBES
            else geometry.CAP_HEIGHT
        )
        thickness = geometry.diagonal_thickness(
            font,
            glyph_name,
            low,
            high,
            index,
            base_height,
        )
        if thickness is not None:
            ratios[glyph_name] = thickness / stem
    return ratios


def check_plane(task: tuple[str, float, float]) -> tuple[list[str], list[str]]:
    path, weight, optical = task
    failures: list[str] = []
    accepted_overlaps: list[str] = []

    normal = instance(path, weight, optical, WIDTH_DEFAULT)
    glyph_names = encoded_latin(normal)
    normal_shapes = {
        glyph_name: geometry.contours_of(normal, glyph_name)
        for glyph_name in glyph_names
    }
    normal_intersections = {
        glyph_name: geometry.self_intersections(shapes)
        for glyph_name, shapes in normal_shapes.items()
        if shapes
    }
    normal_y = {
        glyph_name: vertical_signature(normal, glyph_name)
        for glyph_name in glyph_names
    }
    normal_stem = geometry.measure_stem(normal)
    normal_diagonals = diagonal_ratios(normal)
    normal_vertical_metrics = vertical_metrics(normal)
    reaches = {glyph_name: [] for glyph_name in REACH_PROBES}

    for width in WIDTH_SAMPLES:
        font = (
            normal
            if width == WIDTH_DEFAULT
            else instance(path, weight, optical, width)
        )
        expected_cell = advance_at_width(geometry.ADVANCE, width)
        stem = geometry.measure_stem(font)
        if abs(stem - normal_stem) > 1.1:
            failures.append(
                f"H stem moves at wght {weight:g} opsz {optical:g} "
                f"wdth {width:g}: {stem:.2f} versus {normal_stem:.2f}"
            )
        if vertical_metrics(font) != normal_vertical_metrics:
            failures.append(
                f"vertical metrics move at wght {weight:g} "
                f"opsz {optical:g} wdth {width:g}"
            )

        for glyph_name in glyph_names:
            shapes = (
                normal_shapes[glyph_name]
                if width == WIDTH_DEFAULT
                else geometry.contours_of(font, glyph_name)
            )
            if not shapes:
                continue

            count = (
                normal_intersections.get(glyph_name, 0)
                if width == WIDTH_DEFAULT
                else geometry.self_intersections(shapes)
            )
            normal_count = normal_intersections.get(glyph_name, 0)
            if count != normal_count:
                message = (
                    f"{glyph_name} overlap count changes at wght {weight:g} "
                    f"opsz {optical:g} wdth {width:g}: "
                    f"{normal_count}->{count}"
                )
                if glyph_name in geometry.ACCEPTED_OVERLAP_GLYPHS:
                    accepted_overlaps.append(message)
                else:
                    failures.append(message)

            if vertical_signature(font, glyph_name) != normal_y[glyph_name]:
                failures.append(
                    f"{glyph_name} moves vertically at wght {weight:g} "
                    f"opsz {optical:g} wdth {width:g}"
                )

            normal_advance = normal["hmtx"][glyph_name][0]
            expected_advance = advance_at_width(normal_advance, width)
            actual_advance = font["hmtx"][glyph_name][0]
            if actual_advance != expected_advance:
                failures.append(
                    f"{glyph_name} advance is {actual_advance} at "
                    f"wght {weight:g} opsz {optical:g} wdth {width:g}; "
                    f"expected {expected_advance}"
                )

            if normal_advance:
                box = geometry.bounds(shapes)
                glyph = font["glyf"][glyph_name]
                limit = (
                    geometry.COMPOSITE_CELL_TOLERANCE
                    if glyph.isComposite()
                    else (
                        MULTI_CONTOUR_CELL_TOLERANCE
                        if glyph.numberOfContours > 1
                        else geometry.CELL_TOLERANCE
                    )
                )
                overhang = max(0, -box[0], box[2] - expected_cell)
                if overhang > limit:
                    failures.append(
                        f"{glyph_name} leaves the wdth {width:g} cell at "
                        f"wght {weight:g} opsz {optical:g}: "
                        f"x {box[0]:.0f}..{box[2]:.0f}, "
                        f"cell 0..{expected_cell}"
                    )
                if glyph_name in reaches:
                    reaches[glyph_name].append(box[2] - box[0])

        for glyph_name, ratio in diagonal_ratios(font).items():
            normal_ratio = normal_diagonals[glyph_name]
            low = min(geometry.DIAGONAL_BAND[0], normal_ratio - 0.01)
            high = max(geometry.DIAGONAL_BAND[1], normal_ratio + 0.01)
            if not low <= ratio <= high:
                failures.append(
                    f"{glyph_name} diagonal is {ratio:.3f}x the stem at "
                    f"wght {weight:g} opsz {optical:g} wdth {width:g}; "
                    f"normal width is {normal_ratio:.3f}x"
                )

        dot_sizes = {}
        for glyph_name in DOT_GLYPHS:
            shapes = geometry.contours_of(font, glyph_name)
            dot = min(shapes, key=lambda contour: abs(geometry._area(contour)))
            box = geometry.bounds([dot])
            dot_width = box[2] - box[0]
            dot_height = box[3] - box[1]
            if abs(dot_width - dot_height) > 2.1:
                failures.append(
                    f"{glyph_name} dot is {dot_width:.1f}x{dot_height:.1f} "
                    f"at wght {weight:g} opsz {optical:g} wdth {width:g}"
                )
            dot_sizes[glyph_name] = round(dot_width)
        if max(dot_sizes.values()) - min(dot_sizes.values()) > 2:
            failures.append(
                f"dot sizes disagree at wght {weight:g} "
                f"opsz {optical:g} wdth {width:g}: {dot_sizes}"
            )

    for glyph_name, series in reaches.items():
        if any(
            following < current - 1
            for current, following in zip(series, series[1:])
        ):
            failures.append(
                f"{glyph_name} ink reach is not monotonic at "
                f"wght {weight:g} opsz {optical:g}: "
                + ", ".join(f"{value:.1f}" for value in series)
            )

    return failures, accepted_overlaps


def assert_metadata(path: Path) -> TTFont:
    font = TTFont(path)
    axes = {axis.axisTag: axis for axis in font["fvar"].axes}
    assert set(axes) == {"wght", "wdth", "opsz"}, set(axes)
    assert (
        axes["wdth"].minValue,
        axes["wdth"].defaultValue,
        axes["wdth"].maxValue,
    ) == (WIDTH_MIN, WIDTH_DEFAULT, WIDTH_MAX)
    assert axes["wdth"].defaultValue == 100
    assert "gvar" in font and "HVAR" in font and "STAT" in font
    assert font["OS/2"].usWidthClass == 5
    assert font["OS/2"].xAvgCharWidth == geometry.ADVANCE
    assert font["post"].isFixedPitch == 1

    stat_axes = font["STAT"].table.DesignAxisRecord.Axis
    assert [record.AxisTag for record in stat_axes] == [
        "wght",
        "wdth",
        "opsz",
    ]
    assert all(
        instance.coordinates["wdth"] == WIDTH_DEFAULT
        for instance in font["fvar"].instances
    )
    assert {
        round(instance.coordinates["wght"])
        for instance in font["fvar"].instances
    } == {100, 200, 300, 400, 450, 500, 600, 700, 800}
    return font


def shape(
    path: Path,
    text: str,
    weight: int,
    width: int,
    features: str | None = None,
) -> str:
    harfbuzz = shutil.which("hb-shape")
    assert harfbuzz, "hb-shape is required for width-axis validation"
    command = [
        harfbuzz,
        str(path),
        f"--variations=wght={weight},wdth={width},opsz=14",
    ]
    if features:
        command.append(f"--features={features}")
    command.extend(["--", text])
    return subprocess.check_output(command, text=True).strip()


def advances(shaping: str) -> list[int]:
    return [int(value) for value in re.findall(r"\+(-?\d+)", shaping)]


def assert_shaping(path: Path) -> None:
    sample = "mono MONO 0123"
    for weight in (100, 400, 800):
        for width in (WIDTH_MIN, WIDTH_DEFAULT, WIDTH_MAX):
            expected = advance_at_width(geometry.ADVANCE, width)
            literal = shape(path, sample, weight, int(width))
            assert advances(literal) == [expected] * len(sample), (
                weight,
                width,
                literal,
            )

            ligature = shape(path, "->", weight, int(width), "dlig=1")
            assert "hyphen_greater.liga" in ligature, ligature
            assert advances(ligature) == [expected, expected], (
                weight,
                width,
                ligature,
            )

            marked = shape(path, "x\u0301", weight, int(width))
            assert "acutecomb" in marked, marked
            assert advances(marked) == [expected, 0], (
                weight,
                width,
                marked,
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", type=Path, default=VARIABLE)
    args = parser.parse_args()
    path = args.font.resolve()
    if not path.exists():
        print(f"FAIL: missing {path}")
        return 1

    try:
        font = assert_metadata(path)
        font.close()
        assert_shaping(path)
    except (AssertionError, subprocess.CalledProcessError) as error:
        print(f"FAIL: width metadata or shaping: {error}")
        return 1

    tasks = [
        (str(path), weight, optical)
        for weight in WEIGHT_SAMPLES
        for optical in OPTICAL_SAMPLES
    ]
    workers = min(8, os.cpu_count() or 1)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(check_plane, tasks))

    failures = [
        failure
        for plane_failures, _ in results
        for failure in plane_failures
    ]
    overlap_notes = [
        note
        for _, plane_notes in results
        for note in plane_notes
    ]
    overlap_glyphs = Counter(note.split(" ", 1)[0] for note in overlap_notes)

    print(
        f"checked {len(tasks) * len(WIDTH_SAMPLES)} compiled instances "
        f"across {len(WEIGHT_SAMPLES)} weights, "
        f"{len(OPTICAL_SAMPLES)} optical sizes, and "
        f"{len(WIDTH_SAMPLES)} widths"
    )
    if overlap_glyphs:
        print(
            "  NOTE: inherited nonzero-fill joins vary with width: "
            + ", ".join(
                f"{glyph_name} ({count})"
                for glyph_name, count in sorted(overlap_glyphs.items())
            )
        )
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for failure in failures[:60]:
            print(f"  - {failure}")
        if len(failures) > 60:
            print(f"  ... and {len(failures) - 60} more")
        return 1

    print(
        "PASS: wdth preserves stroke authority, vertical geometry, "
        "monospacing, shaping, and outline topology"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
