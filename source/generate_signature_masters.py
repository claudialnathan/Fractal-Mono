#!/usr/bin/env python3
"""Generate compatible Fractal signature masters from canonical drawings.

Each drawing is exact at its measured reference weight. The other masters
transfer the deformation field from the last clean pre-redesign Fractal release,
so weight changes follow an established type design instead of a mechanical
outline offset.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from fontTools.cu2qu.cu2qu import curves_to_quadratic
from fontTools.misc.transform import Transform
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.varLib.instancer import instantiateVariableFont

from fractal_geometry import (
    ADVANCE,
    REFERENCE_PATHS,
    REFERENCE_SPECS,
    _path_bounds,
    _reference_glyph,
)


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive" / "FractalMono-v1.252.zip"
ARCHIVE_FONT = "fonts/desktop/FractalMono-Variable[wght].ttf"
OUTPUT = Path(__file__).with_name("signature_masters.json")

CUSTOM_NAMES = (
    "J",
    "j",
    "K",
    "R",
    "r",
    "M",
    "W",
    "S",
    "exclam",
    "question",
    "asciicircum",
    "semicolon",
    "colon",
    "asterisk",
    "period",
)
PRESERVED_NAMES = ("t", "f", "l", "O", "o", "zero")
EXPLICIT_CUBIC_NAMES = frozenset({"K", "R", "r"})
SQUARE_CONTOURS = {
    "j": (1,),
    "exclam": (1,),
    "question": (1,),
    "semicolon": (0,),
    "colon": (0, 1),
    "period": (0,),
}
SQUARE_SIZES = {100.0: 98.0, 400.0: 112.0, 800.0: 144.0}


def _extreme_cubic_commands() -> dict[str, dict[float, list[tuple[str, tuple]]]]:
    """Return hand-authored Thin and ExtraBold drawings in font coordinates.

    These are genuine endpoint masters, not offsets from the supplied Book
    drawing. Every flat, vertical, curve tangent, and join has the same
    semantic role at both extremes.
    """
    return {
        "K": {
            100.0: [
                ("moveTo", ((58, 0),)),
                ("lineTo", ((58, 680),)),
                ("lineTo", ((110, 680),)),
                ("lineTo", ((110, 386),)),
                ("curveTo", ((117, 395), (129, 412), (140, 424))),
                ("lineTo", ((397, 680),)),
                ("lineTo", ((477, 680),)),
                ("lineTo", ((204, 376),)),
                ("lineTo", ((521, 0),)),
                ("lineTo", ((435, 0),)),
                ("lineTo", ((177, 326),)),
                ("lineTo", ((110, 272),)),
                ("lineTo", ((110, 0),)),
                ("lineTo", ((58, 0),)),
                ("closePath", ()),
            ],
            800.0: [
                ("moveTo", ((18, 0),)),
                ("lineTo", ((18, 680),)),
                ("lineTo", ((164, 680),)),
                ("lineTo", ((164, 386),)),
                ("curveTo", ((174, 398), (192, 424), (207, 440))),
                ("lineTo", ((368, 680),)),
                ("lineTo", ((518, 680),)),
                ("lineTo", ((256, 378),)),
                ("lineTo", ((561, 0),)),
                ("lineTo", ((403, 0),)),
                ("lineTo", ((190, 294),)),
                ("lineTo", ((164, 266),)),
                ("lineTo", ((164, 0),)),
                ("lineTo", ((18, 0),)),
                ("closePath", ()),
            ],
        },
        "R": {
            100.0: [
                ("moveTo", ((72, 0),)),
                ("lineTo", ((72, 680),)),
                ("lineTo", ((312, 680),)),
                ("curveTo", ((430, 680), (506, 625), (506, 505))),
                ("curveTo", ((506, 420), (451, 345), (390, 322))),
                ("curveTo", ((452, 312), (492, 250), (492, 181))),
                ("lineTo", ((492, 0),)),
                ("lineTo", ((440, 0),)),
                ("lineTo", ((440, 156),)),
                ("curveTo", ((440, 250), (382, 282), (278, 282))),
                ("lineTo", ((124, 282),)),
                ("lineTo", ((124, 0),)),
                ("lineTo", ((72, 0),)),
                ("closePath", ()),
                ("moveTo", ((124, 358),)),
                ("lineTo", ((290, 358),)),
                ("curveTo", ((390, 358), (454, 407), (454, 491))),
                ("curveTo", ((454, 575), (390, 626), (290, 626))),
                ("lineTo", ((124, 626),)),
                ("lineTo", ((124, 358),)),
                ("closePath", ()),
            ],
            800.0: [
                ("moveTo", ((23, 0),)),
                ("lineTo", ((23, 680),)),
                ("lineTo", ((312, 680),)),
                ("curveTo", ((464, 680), (556, 610), (556, 491))),
                ("curveTo", ((556, 410), (495, 362), (414, 360))),
                ("curveTo", ((484, 344), (538, 275), (538, 190))),
                ("lineTo", ((538, 0),)),
                ("lineTo", ((392, 0),)),
                ("lineTo", ((392, 145),)),
                ("curveTo", ((392, 230), (354, 266), (278, 266))),
                ("lineTo", ((172, 266),)),
                ("lineTo", ((172, 0),)),
                ("lineTo", ((23, 0),)),
                ("closePath", ()),
                ("moveTo", ((172, 414),)),
                ("lineTo", ((290, 414),)),
                ("curveTo", ((356, 414), (406, 444), (406, 491))),
                ("curveTo", ((406, 538), (356, 558), (290, 558))),
                ("lineTo", ((172, 558),)),
                ("lineTo", ((172, 414),)),
                ("closePath", ()),
            ],
        },
        "r": {
            100.0: [
                ("moveTo", ((125, 0),)),
                ("lineTo", ((125, 514),)),
                ("lineTo", ((176, 514),)),
                ("lineTo", ((176, 420),)),
                ("curveTo", ((202, 477), (280, 528), (420, 528))),
                ("curveTo", ((438, 528), (455, 527), (473, 524))),
                ("lineTo", ((473, 468),)),
                ("curveTo", ((456, 470), (436, 472), (412, 472))),
                ("curveTo", ((274, 472), (176, 408), (176, 302))),
                ("lineTo", ((176, 0),)),
                ("lineTo", ((125, 0),)),
                ("closePath", ()),
            ],
            800.0: [
                ("moveTo", ((75, 0),)),
                ("lineTo", ((75, 514),)),
                ("lineTo", ((223, 514),)),
                ("lineTo", ((223, 365),)),
                ("curveTo", ((260, 451), (334, 528), (430, 528))),
                ("curveTo", ((464, 528), (490, 526), (513, 522))),
                ("lineTo", ((513, 372),)),
                ("curveTo", ((483, 376), (449, 380), (412, 380))),
                ("curveTo", ((306, 380), (223, 325), (223, 175))),
                ("lineTo", ((223, 0),)),
                ("lineTo", ((75, 0),)),
                ("closePath", ()),
            ],
        },
    }


def _canonical_cubic_commands(name: str) -> list[tuple[str, tuple]]:
    path = REFERENCE_PATHS[name]
    spec = REFERENCE_SPECS[name]
    x_min, y_min, x_max, _ = _path_bounds(path)
    center_x = (x_min + x_max) / 2
    transform = Transform(
        spec.scale,
        0,
        0,
        -spec.scale,
        ADVANCE / 2 - center_x * spec.scale,
        spec.top + y_min * spec.scale,
    )
    pen = RecordingPen()
    parse_path(path, TransformPen(pen, transform))
    return pen.value


def _interpolate_commands(
    name: str,
    weight: float,
) -> list[tuple[str, tuple]]:
    extremes = _extreme_cubic_commands()[name]
    authored = {
        100.0: extremes[100.0],
        450.0: _canonical_cubic_commands(name),
        800.0: extremes[800.0],
    }
    if weight in authored:
        return authored[weight]

    lower, upper = next(
        (lower, upper)
        for lower, upper in zip(sorted(authored), sorted(authored)[1:])
        if lower < weight < upper
    )
    fraction = (weight - lower) / (upper - lower)
    lower_commands = authored[lower]
    upper_commands = authored[upper]
    if len(lower_commands) != len(upper_commands):
        raise ValueError(f"Incompatible cubic command counts for {name}")

    result: list[tuple[str, tuple]] = []
    for (lower_op, lower_args), (upper_op, upper_args) in zip(
        lower_commands,
        upper_commands,
    ):
        if lower_op != upper_op or len(lower_args) != len(upper_args):
            raise ValueError(f"Incompatible cubic commands for {name}")
        args = tuple(
            (
                lower_point[0]
                + (upper_point[0] - lower_point[0]) * fraction,
                lower_point[1]
                + (upper_point[1] - lower_point[1]) * fraction,
            )
            for lower_point, upper_point in zip(lower_args, upper_args)
        )
        result.append((lower_op, args))
    return result


def _commands_to_compatible_quadratics(
    commands_by_weight: dict[float, list[tuple[str, tuple]]],
) -> dict[float, object]:
    """Convert corresponding cubic curves as one compatibility batch."""
    weights = sorted(commands_by_weight)
    pens = {weight: TTGlyphPen(None) for weight in weights}
    current_points: dict[float, tuple[float, float] | None] = {
        weight: None for weight in weights
    }
    command_count = len(commands_by_weight[weights[0]])
    if any(len(commands_by_weight[weight]) != command_count for weight in weights):
        raise ValueError("Incompatible cubic command counts")

    for command_index in range(command_count):
        operations = {
            commands_by_weight[weight][command_index][0] for weight in weights
        }
        if len(operations) != 1:
            raise ValueError("Incompatible cubic operation order")
        operation = operations.pop()
        arguments = {
            weight: commands_by_weight[weight][command_index][1]
            for weight in weights
        }

        if operation in {"moveTo", "lineTo"}:
            for weight in weights:
                point = arguments[weight][0]
                getattr(pens[weight], operation)(point)
                current_points[weight] = point
        elif operation == "curveTo":
            curves = []
            for weight in weights:
                current = current_points[weight]
                if current is None:
                    raise ValueError("Cubic segment has no current point")
                curves.append([current, *arguments[weight]])
            quadratics = curves_to_quadratic(
                curves,
                [0.55] * len(curves),
                all_quadratic=True,
            )
            for weight, quadratic in zip(weights, quadratics):
                pens[weight].qCurveTo(*quadratic[1:])
                current_points[weight] = arguments[weight][-1]
        elif operation == "closePath":
            for weight in weights:
                pens[weight].closePath()
                current_points[weight] = None
        else:
            raise ValueError(f"Unsupported cubic operation: {operation}")

    glyphs = {weight: pens[weight].glyph() for weight in weights}
    for glyph in glyphs.values():
        glyph.coordinates = GlyphCoordinates(
            [(round(x), round(y)) for x, y in glyph.coordinates]
        )
    return glyphs


def _explicit_cubic_glyphs(
    weights: list[float],
) -> dict[float, dict[str, object]]:
    result = {weight: {} for weight in weights}
    for name in sorted(EXPLICIT_CUBIC_NAMES):
        commands = {
            weight: _interpolate_commands(name, weight)
            for weight in weights
        }
        glyphs = _commands_to_compatible_quadratics(commands)
        for weight, glyph in glyphs.items():
            result[weight][name] = glyph
    return result


def _inverse_piecewise(points: dict[float, float], target: float) -> float:
    ordered = sorted(points.items())
    for (input_a, output_a), (input_b, output_b) in zip(ordered, ordered[1:]):
        if output_a <= target <= output_b:
            if output_a == output_b:
                return input_a
            fraction = (target - output_a) / (output_b - output_a)
            return input_a + (input_b - input_a) * fraction
    raise ValueError(f"Unable to invert variation map at {target}")


def _user_weight(normalized: float) -> float:
    if normalized < 0:
        return 400 + normalized * 300
    return 400 + normalized * 400


def _master_weights(font: TTFont) -> list[float]:
    positive_peaks: dict[float, int] = defaultdict(int)
    for variations in font["gvar"].variations.values():
        for variation in variations:
            support = variation.axes.get("wght")
            if support is None:
                continue
            peak = float(support[1])
            if 0 < peak < 1:
                positive_peaks[peak] += 1

    weights = [100.0, 400.0, 800.0]
    if positive_peaks:
        peak = max(positive_peaks, key=positive_peaks.get)
        input_normalized = _inverse_piecewise(
            font["avar"].segments["wght"],
            peak,
        )
        weights.insert(2, _user_weight(input_normalized))
    return weights


def _simple_outline(font: TTFont, name: str):
    glyph = font["glyf"][name]
    if glyph.isComposite():
        coordinates, endpoints, flags = glyph.getCoordinates(font["glyf"])
    else:
        coordinates = GlyphCoordinates(glyph.coordinates)
        endpoints = list(glyph.endPtsOfContours)
        flags = bytearray(glyph.flags)
    return coordinates, list(endpoints), bytearray(flags)


def _deduplicated_controls(
    regular: GlyphCoordinates,
    master: GlyphCoordinates,
) -> tuple[np.ndarray, np.ndarray]:
    if len(regular) != len(master):
        raise ValueError("Archived master topology is incompatible")

    grouped: dict[tuple[float, float], list[tuple[float, float]]] = defaultdict(list)
    for (regular_x, regular_y), (master_x, master_y) in zip(regular, master):
        grouped[(float(regular_x), float(regular_y))].append(
            (float(master_x - regular_x), float(master_y - regular_y))
        )

    controls = []
    deltas = []
    for point, movements in grouped.items():
        controls.append(point)
        deltas.append(
            (
                sum(x for x, _ in movements) / len(movements),
                sum(y for _, y in movements) / len(movements),
            )
        )
    return np.asarray(controls), np.asarray(deltas)


def _kernel(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    difference = left[:, None, :] - right[None, :, :]
    radius_squared = np.sum(difference * difference, axis=2)
    result = np.zeros_like(radius_squared)
    nonzero = radius_squared > 0
    result[nonzero] = radius_squared[nonzero] * np.log(
        np.sqrt(radius_squared[nonzero])
    )
    return result


def _fit_deformation(
    regular: GlyphCoordinates,
    master: GlyphCoordinates,
):
    controls, deltas = _deduplicated_controls(regular, master)
    count = len(controls)
    affine = np.column_stack((np.ones(count), controls))
    system = np.block(
        [
            [_kernel(controls, controls) + np.eye(count) * 1e-6, affine],
            [affine.T, np.zeros((3, 3))],
        ]
    )
    targets = np.vstack((deltas, np.zeros((3, 2))))
    return controls, np.linalg.solve(system, targets)


def _apply_deformation(
    coordinates: GlyphCoordinates,
    controls: np.ndarray,
    coefficients: np.ndarray,
) -> GlyphCoordinates:
    targets = np.asarray(coordinates, dtype=float)
    basis = np.column_stack(
        (
            _kernel(targets, controls),
            np.ones(len(targets)),
            targets,
        )
    )
    movement = basis @ coefficients
    return GlyphCoordinates(
        [
            (round(x + delta_x), round(y + delta_y))
            for (x, y), (delta_x, delta_y) in zip(targets, movement)
        ]
    )


def _contour_ranges(endpoints: list[int]) -> list[range]:
    starts = [0, *(endpoint + 1 for endpoint in endpoints[:-1])]
    return [
        range(start, endpoint + 1)
        for start, endpoint in zip(starts, endpoints)
    ]


def _square_size(weight: float) -> float:
    anchors = sorted(SQUARE_SIZES)
    if weight <= anchors[0]:
        return SQUARE_SIZES[anchors[0]]
    if weight >= anchors[-1]:
        return SQUARE_SIZES[anchors[-1]]
    for lower, upper in zip(anchors, anchors[1:]):
        if lower <= weight <= upper:
            fraction = (weight - lower) / (upper - lower)
            return (
                SQUARE_SIZES[lower]
                + (SQUARE_SIZES[upper] - SQUARE_SIZES[lower]) * fraction
            )
    raise AssertionError("Unreachable square interpolation")


def _replace_square_contour(
    coordinates: GlyphCoordinates,
    endpoints: list[int],
    flags: bytearray,
    contour_index: int,
    size: float,
) -> tuple[GlyphCoordinates, list[int], bytearray]:
    contours = _contour_ranges(endpoints)
    target = list(contours[contour_index])
    points = [coordinates[index] for index in target]
    center_x = (min(x for x, _ in points) + max(x for x, _ in points)) / 2
    center_y = (min(y for _, y in points) + max(y for _, y in points)) / 2
    target = round(size)
    left = round(center_x - target / 2)
    right = left + target
    bottom = round(center_y - target / 2)
    top = bottom + target

    area = sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )
    if area < 0:
        square = [
            (left, top),
            (right, top),
            (right, bottom),
            (left, bottom),
        ]
    else:
        square = [
            (left, bottom),
            (right, bottom),
            (right, top),
            (left, top),
        ]

    rebuilt_coordinates: list[tuple[int, int]] = []
    rebuilt_flags = bytearray()
    rebuilt_endpoints = []
    for index, contour in enumerate(contours):
        if index == contour_index:
            rebuilt_coordinates.extend(square)
            rebuilt_flags.extend([1] * 4)
        else:
            rebuilt_coordinates.extend(coordinates[point] for point in contour)
            rebuilt_flags.extend(flags[point] for point in contour)
        rebuilt_endpoints.append(len(rebuilt_coordinates) - 1)
    return (
        GlyphCoordinates(rebuilt_coordinates),
        rebuilt_endpoints,
        rebuilt_flags,
    )


def _anchor_reference_y(
    name: str,
    original: GlyphCoordinates,
    deformed: GlyphCoordinates,
) -> None:
    for index, ((_, original_y), (x, y)) in enumerate(zip(original, deformed)):
        if any(
            math.isclose(original_y, anchor, abs_tol=1)
            for anchor in REFERENCE_SPECS[name].anchor_y
        ):
            deformed[index] = (x, original_y)


def _serialize_outline(
    coordinates: GlyphCoordinates,
    endpoints: list[int],
    flags: bytearray,
) -> dict[str, object]:
    return {
        "coordinates": [[int(x), int(y)] for x, y in coordinates],
        "endPtsOfContours": endpoints,
        "flags": list(flags),
    }


def _weight_key(weight: float) -> str:
    return f"{weight:.6f}".rstrip("0").rstrip(".")


def _solve_reference_anchor(
    masters: dict[str, object],
    weights: list[float],
    name: str,
    reference=None,
) -> None:
    """Make interpolation land exactly on an in-between reference drawing."""
    anchor_weight = REFERENCE_SPECS[name].anchor_weight
    if anchor_weight in weights:
        return

    lower, upper = next(
        (lower, upper)
        for lower, upper in zip(weights, weights[1:])
        if lower < anchor_weight < upper
    )
    fraction = (anchor_weight - lower) / (upper - lower)
    if reference is None:
        reference = _reference_glyph(name)
    target = list(reference.coordinates)
    lower_outline = masters[_weight_key(lower)][name]
    upper_outline = masters[_weight_key(upper)][name]
    if len(target) != len(lower_outline["coordinates"]):
        raise ValueError(f"Reference topology differs at anchor for {name}")

    upper_outline["coordinates"] = [
        [
            round((target_x - (1 - fraction) * lower_x) / fraction),
            round((target_y - (1 - fraction) * lower_y) / fraction),
        ]
        for (target_x, target_y), (lower_x, lower_y) in zip(
            target,
            lower_outline["coordinates"],
        )
    ]


def generate() -> dict[str, object]:
    archive_bytes = ARCHIVE.read_bytes()
    with ZipFile(BytesIO(archive_bytes)) as archive:
        variable_bytes = archive.read(ARCHIVE_FONT)
    variable = TTFont(
        BytesIO(variable_bytes),
        recalcBBoxes=False,
        recalcTimestamp=False,
    )
    weights = _master_weights(variable)
    reference_weights = {
        spec.anchor_weight
        for name, spec in REFERENCE_SPECS.items()
        if name in CUSTOM_NAMES
    }
    archived = {
        weight: instantiateVariableFont(
            variable,
            {"wght": weight},
            inplace=False,
            optimize=True,
        )
        for weight in sorted(set(weights) | reference_weights)
    }
    explicit_cubic_glyphs = _explicit_cubic_glyphs(
        sorted(set(weights) | {450.0})
    )

    masters: dict[str, object] = {}
    for weight in weights:
        weight_key = _weight_key(weight)
        master: dict[str, object] = {}
        for name in CUSTOM_NAMES:
            anchor_weight = REFERENCE_SPECS[name].anchor_weight
            reference = explicit_cubic_glyphs[450.0].get(
                name,
                _reference_glyph(name),
            )
            coordinates = GlyphCoordinates(reference.coordinates)
            endpoints = list(reference.endPtsOfContours)
            flags = bytearray(reference.flags)

            if name in EXPLICIT_CUBIC_NAMES:
                explicit = explicit_cubic_glyphs[weight][name]
                coordinates = GlyphCoordinates(explicit.coordinates)
                endpoints = list(explicit.endPtsOfContours)
                flags = bytearray(explicit.flags)
            elif weight != anchor_weight and name != "period":
                old_reference, _, _ = _simple_outline(
                    archived[anchor_weight],
                    name,
                )
                old_master, _, _ = _simple_outline(archived[weight], name)
                controls, coefficients = _fit_deformation(
                    old_reference,
                    old_master,
                )
                coordinates = _apply_deformation(
                    coordinates,
                    controls,
                    coefficients,
                )
                _anchor_reference_y(
                    name,
                    reference.coordinates,
                    coordinates,
                )

            for contour_index in sorted(
                SQUARE_CONTOURS.get(name, ()),
                reverse=True,
            ):
                coordinates, endpoints, flags = _replace_square_contour(
                    coordinates,
                    endpoints,
                    flags,
                    contour_index,
                    _square_size(weight),
                )
            master[name] = _serialize_outline(coordinates, endpoints, flags)

        for name in PRESERVED_NAMES:
            coordinates, endpoints, flags = _simple_outline(
                archived[weight],
                name,
            )
            if name in {"O", "o", "zero"}:
                coordinates, endpoints, flags = _replace_square_contour(
                    coordinates,
                    endpoints,
                    flags,
                    len(endpoints) - 1,
                    _square_size(weight)
                    * (0.72 if name == "o" else 0.95),
                )
            master[name] = _serialize_outline(coordinates, endpoints, flags)
        masters[weight_key] = master

    for name in CUSTOM_NAMES:
        _solve_reference_anchor(
            masters,
            weights,
            name,
            (
                explicit_cubic_glyphs[450.0][name]
                if name in EXPLICIT_CUBIC_NAMES
                else None
            ),
        )

    names = (*CUSTOM_NAMES, *PRESERVED_NAMES)
    first = masters[next(iter(masters))]
    for name in names:
        topology = (
            first[name]["endPtsOfContours"],
            first[name]["flags"],
        )
        for master in masters.values():
            candidate = (
                master[name]["endPtsOfContours"],
                master[name]["flags"],
            )
            if candidate != topology:
                raise ValueError(f"Incompatible generated topology for {name}")

    return {
        "format": 1,
        "source": {
            "archive": str(ARCHIVE.relative_to(ROOT)),
            "archiveSha256": hashlib.sha256(archive_bytes).hexdigest(),
            "font": ARCHIVE_FONT,
        },
        "weights": weights,
        "masters": masters,
    }


def main() -> None:
    data = generate()
    OUTPUT.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
