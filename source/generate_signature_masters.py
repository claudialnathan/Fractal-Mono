#!/usr/bin/env python3
"""Generate compatible CLN signature masters from canonical drawings.

Each drawing is exact at its measured reference weight. The other masters
transfer the deformation field from the last clean pre-redesign CLN release,
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
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.varLib.instancer import instantiateVariableFont

from cln_geometry import (
    REFERENCE_SPECS,
    _reference_glyph,
    offset_glyph_stable,
    stem_for_weight,
)


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive" / "CLNMono-v1.252.zip"
ARCHIVE_FONT = "fonts/desktop/CLNMono-Variable[wght].ttf"
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
CONTOUR_WEIGHT_NAMES = frozenset({"K", "R", "r"})
SQUARE_CONTOURS = {
    "j": (1,),
    "exclam": (1,),
    "question": (1,),
    "semicolon": (0,),
    "colon": (0, 1),
    "period": (0,),
}
SQUARE_SIZES = {100.0: 98.0, 400.0: 112.0, 800.0: 144.0}


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

    masters: dict[str, object] = {}
    for weight in weights:
        weight_key = _weight_key(weight)
        master: dict[str, object] = {}
        for name in CUSTOM_NAMES:
            anchor_weight = REFERENCE_SPECS[name].anchor_weight
            reference = _reference_glyph(name)
            coordinates = GlyphCoordinates(reference.coordinates)
            endpoints = list(reference.endPtsOfContours)
            flags = bytearray(reference.flags)

            if weight != anchor_weight and name in CONTOUR_WEIGHT_NAMES:
                weighted = offset_glyph_stable(
                    reference,
                    (
                        stem_for_weight(weight)
                        - REFERENCE_SPECS[name].reference_stem
                    )
                    / 2,
                    REFERENCE_SPECS[name].anchor_y,
                    (1, -1) if name == "R" else None,
                )
                coordinates = GlyphCoordinates(weighted.coordinates)
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
        _solve_reference_anchor(masters, weights, name)

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
