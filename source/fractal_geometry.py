"""Fractal Mono outline construction and optical-size geometry."""

from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program
import stroke_system


ADVANCE = 579
CAP_HEIGHT = 680
X_HEIGHT = 528
LOWERCASE_ASCENDER_HEIGHT = 728
LOWERCASE_DESCENDER = -195
DEFAULT_OPSZ = 14
TEXT_OPSZ = 9
DISPLAY_OPSZ = 72
REGULAR_STEM = 80


def _reference_paths() -> dict[str, str]:
    """Return the canonical Fractal drawing paths in compact design coordinates."""
    return {
        "J": (
            "M26.520 89.800C18.280 89.800 10.420 88.580 5.700 84.100"
            "C0.980 79.620 0.000 72.480 0.000 64.720L9.720 64.720"
            "C9.720 70.000 9.820 75.140 12.780 78.100"
            "C15.740 81.060 21.240 81.520 26.520 81.520"
            "C31.800 81.520 37.320 81.060 40.200 78.100"
            "C43.160 75.140 43.200 70.000 43.200 64.720L43.200 0.000"
            "L52.920 0.000L52.920 64.720"
            "C52.920 72.480 51.960 79.620 47.160 84.100"
            "C42.440 88.580 34.600 89.800 26.520 89.800Z"
        ),
        "j": (
            "M0.000 110.760L0.000 101.280L14.640 101.280"
            "C19.840 101.280 23.800 99.760 26.520 96.720"
            "C29.320 93.680 30.720 89.560 30.720 84.360L30.720 32.400"
            "L3.220 32.400L3.220 24.000L40.440 24.000L40.440 84.360"
            "C40.440 92.360 38.120 98.760 33.480 103.560"
            "C28.840 108.360 22.560 110.760 14.640 110.760Z"
            "M41.040 12.360L27.600 12.360L27.600 0.000L41.040 0.000Z"
        ),
        "K": (
            "M0.000 105.000L0.000 0.000L13.500 0.000L13.500 45.450"
            "C15.000 43.800 16.650 41.850 18.300 39.900L53.400 0.000"
            "L69.900 0.000L28.050 46.950L76.650 105.000L59.100 105.000"
            "L19.200 56.850L13.500 63.300L13.500 105.000Z"
        ),
        "R": (
            "M0.000 105.000L0.000 0.000L39.900 0.000"
            "C59.850 0.000 72.750 9.900 72.750 27.600"
            "C72.750 40.800 62.700 50.250 53.250 53.100"
            "C63.300 54.750 70.350 63.300 70.350 77.100L70.350 105.000"
            "L56.700 105.000L56.700 80.850"
            "C56.700 64.200 50.250 59.100 34.650 59.100L13.650 59.100"
            "L13.650 105.000L0.000 105.000Z"
            "M13.650 47.550L36.450 47.550"
            "C50.700 47.550 58.800 41.100 58.800 29.250"
            "C58.800 17.400 50.700 11.400 36.450 11.400L13.650 11.400Z"
        ),
        "r": (
            "M0.000 74.250L0.000 1.950L12.900 1.950L12.900 17.250"
            "C16.650 9.150 25.350 0.000 44.400 0.000"
            "C47.100 0.000 49.350 0.150 52.050 0.600L52.050 13.200"
            "C49.500 12.900 46.500 12.600 43.200 12.600"
            "C22.200 12.600 12.900 22.350 12.900 38.700L12.900 74.250Z"
        ),
        "M": (
            "M0.000 84.000L0.000 0.000L15.120 0.000L26.160 41.280"
            "C27.000 44.640 27.960 47.880 28.920 51.360"
            "C29.760 48.000 30.600 44.760 31.560 41.280L42.360 0.000"
            "L57.240 0.000L57.240 84.000L47.640 84.000L48.120 23.760"
            "C48.120 18.600 48.120 13.800 48.240 10.440L34.440 63.600"
            "L22.920 63.600L8.880 10.560"
            "C9.120 15.360 9.120 18.600 9.120 23.040L9.600 84.000Z"
        ),
        "W": (
            "M10.800 84.000L0.000 0.000L10.800 0.000L17.160 61.080"
            "C17.520 64.440 17.760 67.560 18.120 70.800"
            "C18.720 67.560 19.200 64.440 19.800 61.080L27.000 19.320"
            "L37.680 19.320L44.880 61.080"
            "C45.480 64.440 46.080 67.560 46.560 70.800"
            "C46.920 67.560 47.280 64.440 47.520 61.080L53.880 0.000"
            "L64.080 0.000L53.280 84.000L40.680 84.000L33.720 44.040"
            "C33.120 40.920 32.520 37.680 32.040 34.440"
            "C31.440 37.680 30.960 40.920 30.360 44.040L23.400 84.000Z"
        ),
        "S": (
            "M0.000 63.000L9.840 63.000"
            "C10.680 72.720 14.160 74.880 28.680 74.880"
            "C43.920 74.880 47.280 72.360 47.280 60.600"
            "C47.280 51.000 43.920 48.120 28.920 44.880"
            "C5.640 39.840 0.480 35.760 0.480 21.720"
            "C0.480 3.960 5.520 0.000 28.560 0.000"
            "C49.800 0.000 54.600 3.240 55.320 18.120L45.480 18.120"
            "C44.880 10.800 41.760 9.120 28.560 9.120"
            "C13.560 9.120 10.320 11.400 10.320 21.840"
            "C10.320 29.760 13.680 32.280 28.800 35.520"
            "C52.080 40.560 57.120 44.880 57.120 60.600"
            "C57.120 79.800 51.840 84.000 27.720 84.000"
            "C5.040 84.000 0.000 80.280 0.000 63.000Z"
        ),
        "exclam": (
            "M4.680 60.360L1.440 26.760L1.440 0.000L12.960 0.000"
            "L12.960 26.760L9.600 60.360Z"
            "M0.000 84.000L0.000 69.000L14.280 69.000L14.280 84.000Z"
        ),
        "question": (
            "M16.253 0.000C21.965 0.000 26.920 0.924 31.120 2.771"
            "C35.404 4.619 38.721 7.223 41.073 10.583"
            "C43.425 13.943 44.602 18.059 44.602 22.931"
            "C44.602 27.634 43.593 31.835 41.577 35.530"
            "C39.561 39.142 36.705 42.040 33.010 44.224"
            "C29.398 46.323 25.157 47.457 20.285 47.625L20.285 59.973"
            "L10.205 59.973L10.205 39.436L16.505 39.436"
            "C22.048 39.436 27.928 38.554 31.120 35.530"
            "C34.312 32.506 35.908 28.516 35.908 23.561"
            "C35.908 18.857 32.758 14.574 29.482 11.970"
            "C26.291 9.366 21.881 8.063 16.253 8.063L0.000 8.063"
            "L0.000 0.000Z"
            "M8.000 84.000L8.000 69.000L22.280 69.000L22.280 84.000Z"
        ),
        "asciicircum": (
            "M0.000 34.000L16.529 0.000L26.471 0.000L43.000 34.000"
            "L33.657 34.000L22.039 10.451L20.961 10.451L9.343 34.000Z"
        ),
        "colon": (
            "M0.000 16.080L0.000 0.000L16.080 0.000L16.080 16.080Z"
            "M0.000 56.160L0.000 40.080L16.080 40.080L16.080 56.160Z"
        ),
        "semicolon": (
            "M0.000 16.080L0.000 0.000L16.080 0.000L16.080 16.080Z"
            "M0.000 73.000L2.500 44.000L16.000 44.000L7.500 73.000Z"
        ),
        "asterisk": (
            "M16.010 48.359L8.748 44.068L18.485 28.223L0.000 28.388"
            "L0.000 19.971L18.485 20.136L8.748 4.291L16.010 0.000"
            "L25.583 16.505L34.825 0.000L42.252 4.291L32.515 20.136"
            "L51.000 19.971L51.000 28.388L32.515 28.223L42.252 44.068"
            "L34.825 48.359L25.583 31.854Z"
        ),
        "period": "M0.000 16.080L0.000 0.000L16.080 0.000L16.080 16.080Z",
    }


REFERENCE_PATHS = _reference_paths()


@dataclass(frozen=True)
class ReferenceSpec:
    scale: float
    top: float
    reference_stem: float = REGULAR_STEM
    anchor_y: tuple[int, ...] = ()
    optical_x: bool = False
    anchor_weight: float = 400


CAP_SCALE = CAP_HEIGHT / 84
FIGMA_CAP_SCALE = CAP_HEIGHT / 105
FIGMA_LOWERCASE_SCALE = X_HEIGHT / 74.25
REFERENCE_SPECS = {
    "J": ReferenceSpec(CAP_SCALE, CAP_HEIGHT, 79, (-47, CAP_HEIGHT), True),
    "j": ReferenceSpec(25 / 3, LOWERCASE_ASCENDER_HEIGHT, 79, (), False),
    "K": ReferenceSpec(
        FIGMA_CAP_SCALE,
        CAP_HEIGHT,
        87,
        (0, CAP_HEIGHT),
        True,
        450,
    ),
    "R": ReferenceSpec(
        FIGMA_CAP_SCALE,
        CAP_HEIGHT,
        88,
        (0, CAP_HEIGHT),
        True,
        450,
    ),
    "r": ReferenceSpec(
        FIGMA_LOWERCASE_SCALE,
        X_HEIGHT,
        92,
        (0, X_HEIGHT),
        False,
        450,
    ),
    "M": ReferenceSpec(CAP_SCALE, CAP_HEIGHT, 78, (0, CAP_HEIGHT), True),
    "W": ReferenceSpec(CAP_SCALE, CAP_HEIGHT, 80, (0, CAP_HEIGHT), True),
    "S": ReferenceSpec(CAP_SCALE, CAP_HEIGHT, 80, (0, CAP_HEIGHT), True),
    "exclam": ReferenceSpec(CAP_SCALE, CAP_HEIGHT, 80, (CAP_HEIGHT,), False),
    "question": ReferenceSpec(CAP_SCALE, CAP_HEIGHT, 80, (CAP_HEIGHT,), False),
    "asciicircum": ReferenceSpec(CAP_SCALE, CAP_HEIGHT, 80, (CAP_HEIGHT,), False),
    "colon": ReferenceSpec(CAP_SCALE, 567, 80, (), False),
    "semicolon": ReferenceSpec(CAP_SCALE, 542, 80, (), False),
    "asterisk": ReferenceSpec(CAP_SCALE, 737, 68, (), True),
    "period": ReferenceSpec(CAP_SCALE, 130, 80, (), False),
}


CUSTOM_GLYPH_NAMES = frozenset(REFERENCE_SPECS)
PRESERVED_MASTER_GLYPH_NAMES = frozenset(
    {"t", "f", "l", "O", "o", "zero"}
)
SQUARE_MARK_NAMES = frozenset({"uni0307", "uni0308", "dotbelowcomb"})
SIGNATURE_MASTERS_PATH = Path(__file__).with_name("signature_masters.json")


def stem_for_weight(weight: float) -> float:
    if weight <= 400:
        return 50 + (weight - 100) * (30 / 300)
    return 80 + (weight - 400) * (70 / 400)


def _axis_fraction(value: float, start: float, default: float, end: float) -> float:
    if value == default:
        return 0
    if value < default:
        return (value - default) / (default - start)
    return (value - default) / (end - default)


def optical_value(opsz: float, text: float, default: float, display: float) -> float:
    factor = _axis_fraction(opsz, TEXT_OPSZ, DEFAULT_OPSZ, DISPLAY_OPSZ)
    if factor < 0:
        return default + (default - text) * factor
    return default + (display - default) * factor


def _path_bounds(path: str) -> tuple[float, float, float, float]:
    pen = BoundsPen(None)
    parse_path(path, pen)
    assert pen.bounds is not None
    return pen.bounds


def _reference_glyph(name: str):
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
    pen = TTGlyphPen(None)
    quadratic = Cu2QuPen(pen, max_err=0.55, reverse_direction=False)
    parse_path(path, TransformPen(quadratic, transform))
    return pen.glyph()


def _contour_ranges(glyph) -> list[range]:
    starts = [0, *(endpoint + 1 for endpoint in glyph.endPtsOfContours[:-1])]
    return [
        range(start, endpoint + 1)
        for start, endpoint in zip(starts, glyph.endPtsOfContours)
    ]


def _signed_area(coordinates, indices: range) -> float:
    points = [coordinates[index] for index in indices]
    return sum(
        x * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * y
        for index, (x, y) in enumerate(points)
    )


def _nearest_distinct(coordinates, indices: list[int], position: int, step: int):
    origin = coordinates[indices[position]]
    for distance in range(1, len(indices)):
        candidate = coordinates[indices[(position + distance * step) % len(indices)]]
        if candidate != origin:
            return candidate
    return origin


def offset_glyph_stable(
    glyph,
    amount: float,
    anchor_y: tuple[int, ...],
    contour_multipliers: tuple[float, ...] | None = None,
):
    """Offset explicit on-curve points and carry their movement into controls.

    Moving every quadratic control along its own local normal can reverse short
    handles at joins and terminals. Compatible masters instead move the
    explicit outline points first, then interpolate that displacement through
    each intervening off-curve chain. This preserves compatible curves while
    still adding or removing weight.
    """
    if not amount:
        return glyph
    coordinates = list(glyph.coordinates)
    expanded = list(coordinates)
    for contour_index, contour_range in enumerate(_contour_ranges(glyph)):
        contour_amount = amount
        if contour_multipliers is not None:
            contour_amount *= contour_multipliers[contour_index]
        indices = list(contour_range)
        area = _signed_area(coordinates, contour_range)
        outward_sign = 1 if area > 0 else -1
        on_curve_positions = [
            position
            for position, index in enumerate(indices)
            if glyph.flags[index] & 1
        ]
        if not on_curve_positions:
            continue

        displacements: dict[int, tuple[float, float]] = {}
        for position in on_curve_positions:
            index = indices[position]
            x, y = coordinates[index]
            previous = _nearest_distinct(coordinates, indices, position, -1)
            following = _nearest_distinct(coordinates, indices, position, 1)
            tangent_x = following[0] - previous[0]
            tangent_y = following[1] - previous[1]
            length = math.hypot(tangent_x, tangent_y)
            if not length:
                continue
            normal_x = outward_sign * tangent_y / length
            normal_y = outward_sign * -tangent_x / length
            delta_x = normal_x * contour_amount
            delta_y = normal_y * contour_amount
            if any(abs(y - anchor) <= 1 for anchor in anchor_y):
                delta_y = 0
            displacements[position] = (delta_x, delta_y)
            expanded[index] = (
                round(x + delta_x),
                round(y + delta_y),
            )

        contour_length = len(indices)
        for start_position, next_position in zip(
            on_curve_positions,
            [*on_curve_positions[1:], on_curve_positions[0] + contour_length],
        ):
            span = next_position - start_position
            if span <= 1:
                continue
            start_delta = displacements[start_position]
            end_delta = displacements[next_position % contour_length]
            for offset in range(1, span):
                position = (start_position + offset) % contour_length
                index = indices[position]
                fraction = offset / span
                delta_x = start_delta[0] + (
                    end_delta[0] - start_delta[0]
                ) * fraction
                delta_y = start_delta[1] + (
                    end_delta[1] - start_delta[1]
                ) * fraction
                x, y = coordinates[index]
                expanded[index] = (
                    round(x + delta_x),
                    round(y + delta_y),
                )

    glyph.coordinates = type(glyph.coordinates)(expanded)
    return glyph


def _scale_x(glyph, factor: float):
    if factor == 1:
        return glyph
    glyph.coordinates = type(glyph.coordinates)(
        [
            (round(ADVANCE / 2 + (x - ADVANCE / 2) * factor), y)
            for x, y in glyph.coordinates
        ]
    )
    return glyph


def _reshape_square_contour(
    glyph,
    contour_index: int,
    *,
    size: float | None = None,
    top: float | None = None,
) -> None:
    contour = list(_contour_ranges(glyph)[contour_index])
    if len(contour) != 4:
        return
    points = [glyph.coordinates[index] for index in contour]
    x_min = min(x for x, _ in points)
    x_max = max(x for x, _ in points)
    y_min = min(y for _, y in points)
    y_max = max(y for _, y in points)
    target = round(
        size if size is not None else max(x_max - x_min, y_max - y_min)
    )
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    if top is not None:
        center_y = top - target / 2
    left = round(center_x - target / 2)
    right = left + target
    bottom = round(center_y - target / 2)
    target_top = bottom + target
    clockwise = _signed_area(glyph.coordinates, range(contour[0], contour[-1] + 1)) < 0
    if clockwise:
        points = [
            (left, target_top),
            (right, target_top),
            (right, bottom),
            (left, bottom),
        ]
    else:
        points = [
            (left, bottom),
            (right, bottom),
            (right, target_top),
            (left, target_top),
        ]
    for index, point in zip(contour, points):
        glyph.coordinates[index] = point
        glyph.flags[index] |= 1


@lru_cache(maxsize=1)
def _signature_master_data() -> dict[str, object]:
    return json.loads(SIGNATURE_MASTERS_PATH.read_text(encoding="utf-8"))


def _master_outline(name: str, weight: float):
    data = _signature_master_data()
    weights = [float(value) for value in data["weights"]]
    masters = data["masters"]

    if weight <= weights[0]:
        lower = upper = weights[0]
        fraction = 0
    elif weight >= weights[-1]:
        lower = upper = weights[-1]
        fraction = 0
    else:
        lower = weights[0]
        upper = weights[-1]
        for candidate_lower, candidate_upper in zip(weights, weights[1:]):
            if candidate_lower <= weight <= candidate_upper:
                lower = candidate_lower
                upper = candidate_upper
                break
        fraction = 0 if lower == upper else (weight - lower) / (upper - lower)

    def key(value: float) -> str:
        return f"{value:.6f}".rstrip("0").rstrip(".")

    lower_outline = masters[key(lower)][name]
    upper_outline = masters[key(upper)][name]
    if (
        lower_outline["endPtsOfContours"] != upper_outline["endPtsOfContours"]
        or lower_outline["flags"] != upper_outline["flags"]
    ):
        raise ValueError(f"Incompatible signature masters for {name}")

    coordinates = [
        (
            round(lower_x + (upper_x - lower_x) * fraction),
            round(lower_y + (upper_y - lower_y) * fraction),
        )
        for (lower_x, lower_y), (upper_x, upper_y) in zip(
            lower_outline["coordinates"],
            upper_outline["coordinates"],
        )
    ]
    glyph = Glyph()
    glyph.numberOfContours = len(lower_outline["endPtsOfContours"])
    glyph.coordinates = GlyphCoordinates(coordinates)
    glyph.endPtsOfContours = list(lower_outline["endPtsOfContours"])
    glyph.flags = bytearray(lower_outline["flags"])
    glyph.program = Program()
    return glyph


def _contour_square_size(glyph, contour_index: int) -> float:
    contour = list(_contour_ranges(glyph)[contour_index])
    points = [glyph.coordinates[index] for index in contour]
    return max(
        max(x for x, _ in points) - min(x for x, _ in points),
        max(y for _, y in points) - min(y for _, y in points),
    )


def _apply_signature_optical_geometry(
    name: str,
    glyph,
    opsz: float,
    weight: float,
) -> None:
    if opsz == DEFAULT_OPSZ:
        return

    if name in {"J", "K", "M", "R", "W", "S", "O"}:
        x_factor = optical_value(opsz, 1.005, 1, 0.975)
    elif name in {"j", "t", "f", "l", "r", "o"}:
        x_factor = optical_value(opsz, 1.010, 1, 0.980)
    elif name == "zero":
        x_factor = optical_value(opsz, 1.008, 1, 0.985)
    elif REFERENCE_SPECS.get(name, ReferenceSpec(1, 0)).optical_x:
        x_factor = optical_value(opsz, 1.006, 1, 0.975)
    else:
        x_factor = 1

    transformed = []
    rigid_ascender_details = {
        "f": frozenset(range(5, 15)),
        "l": frozenset(range(3, 7)),
    }.get(name, frozenset())
    for index, (x, y) in enumerate(glyph.coordinates):
        x = ADVANCE / 2 + (x - ADVANCE / 2) * x_factor
        if name in {"j", "t", "f", "l", "r", "o"}:
            if index not in rigid_ascender_details:
                y = _lowercase_y(y, opsz)
        transformed.append((round(x), round(y)))
    glyph.coordinates = GlyphCoordinates(transformed)

    # Free-standing dots all share one size, so they stay identical to the i and
    # j tittles built from the shared mark. Taking each one from its own already
    # optically-scaled bounding box is what left j's tittle 13% oversized at
    # Display.
    shared_dot_contours = {
        "j": (1,),
        "exclam": (1,),
        "question": (1,),
        "colon": (0, 1),
        "semicolon": (0,),
        "period": (0,),
    }.get(name, ())
    for contour_index in shared_dot_contours:
        _reshape_square_contour(
            glyph,
            contour_index,
            size=square_size(stem_for_weight(weight), opsz),
            top=LOWERCASE_ASCENDER_HEIGHT if name == "j" else None,
        )

    # The counter dots are deliberately their own sizes, so they keep their own
    # measurement and only take the optical scale.
    optical_square_scale = optical_value(opsz, 1.06, 1, 0.90)
    for contour_index in {"O": (-1,), "o": (-1,), "zero": (-1,)}.get(name, ()):
        _reshape_square_contour(
            glyph,
            contour_index,
            size=_contour_square_size(glyph, contour_index) * optical_square_scale,
        )


def square_size(stem: float, opsz: float, *, scale: float = 1) -> float:
    base = 112 + (stem - REGULAR_STEM) * 0.45
    optical = optical_value(opsz, 1.06, 1, 0.90)
    return max(64, base * optical * scale)


def build_reference_glyph(name: str, weight: float, opsz: float):
    glyph = _master_outline(name, weight)
    if name in stroke_system.STROKE_PLANS:
        reference = _master_outline(name, 400.0)
        stroke_system.apply(
            glyph,
            name,
            stem=stem_for_weight(weight),
            reference=reference,
            reference_stem=stroke_system.reference_stem(reference, name),
        )
    _apply_signature_optical_geometry(name, glyph, opsz, weight)
    return glyph


def _replace_contours(glyph, contours: list[list[tuple[int, int]]]) -> None:
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    from fontTools.ttLib.tables.ttProgram import Program

    coordinates: list[tuple[int, int]] = []
    endpoints: list[int] = []
    for contour in contours:
        coordinates.extend(contour)
        endpoints.append(len(coordinates) - 1)
    glyph.coordinates = GlyphCoordinates(coordinates)
    glyph.endPtsOfContours = endpoints
    glyph.flags = bytearray([1] * len(coordinates))
    glyph.numberOfContours = len(contours)
    glyph.program = Program()


def _clockwise_square(
    center_x: float,
    center_y: float,
    size: float,
) -> list[tuple[int, int]]:
    # Both extents come from one integer edge plus one integer size. Rounding the
    # four coordinates independently from a fractional centre lets the width and
    # height land a unit apart, which is how the i tittle stopped being square.
    target = round(size)
    left = round(center_x - target / 2)
    bottom = round(center_y - target / 2)
    return [
        (left, bottom + target),
        (left + target, bottom + target),
        (left + target, bottom),
        (left, bottom),
    ]


def install_square_marks(font, weight: float, opsz: float) -> None:
    glyphs = font["glyf"]
    size = square_size(stem_for_weight(weight), opsz)

    mark_specs = {
        "uni0307": [(-300, LOWERCASE_ASCENDER_HEIGHT - size / 2)],
        "uni0308": [
            (-410, LOWERCASE_ASCENDER_HEIGHT - 63),
            (-190, LOWERCASE_ASCENDER_HEIGHT - 63),
        ],
        "dotbelowcomb": [(-300, -144)],
    }
    for glyph_name, centers in mark_specs.items():
        glyph = glyphs[glyph_name]
        _replace_contours(
            glyph,
            [_clockwise_square(x, y, size) for x, y in centers],
        )
        glyph.recalcBounds(glyphs)
        font["hmtx"].metrics[glyph_name] = (
            font["hmtx"].metrics[glyph_name][0],
            glyph.xMin,
        )


def install_square_ellipsis(font, weight: float, opsz: float) -> None:
    glyphs = font["glyf"]
    glyph = glyphs["ellipsis"]
    size = min(square_size(stem_for_weight(weight), opsz) * 0.82, 104)
    gap = 45
    total = size * 3 + gap * 2
    left = (ADVANCE - total) / 2
    center_y = size / 2
    contours = [
        _clockwise_square(left + size / 2 + index * (size + gap), center_y, size)
        for index in range(3)
    ]
    _replace_contours(glyph, contours)
    glyph.recalcBounds(glyphs)
    font["hmtx"].metrics["ellipsis"] = (ADVANCE, glyph.xMin)


# Beyond this a glyph is colliding with its neighbours rather than bleeding on
# purpose. Box-drawing, block elements and the joined programming drawings are
# meant to reach the cell edges and must not be moved, so only letters and their
# accented composites are eligible.
CELL_TOLERANCE = 12
# Fitted to a tighter bound than the gate allows, so that interpolating between
# two fitted masters cannot overshoot it.
CELL_FIT_TARGET = 6
CELL_FIT_EXTRA = frozenset(
    {"percent", "perthousand", "onehalf", "onequarter", "threequarters", "ampersand"}
)


def _cell_fit_candidates(font) -> frozenset[str]:
    letters = set()
    for codepoint, glyph_name in font.getBestCmap().items():
        if unicodedata.category(chr(codepoint)).startswith("L"):
            letters.add(glyph_name)
    glyphs = font["glyf"]
    # An accented composite is eligible when its base is.
    for _ in range(3):
        for glyph_name in font.getGlyphOrder():
            glyph = glyphs[glyph_name]
            if glyph_name in letters or not glyph.isComposite():
                continue
            if any(c.glyphName in letters for c in glyph.components):
                letters.add(glyph_name)
    return frozenset(letters | CELL_FIT_EXTRA)


def fit_glyphs_to_cell(
    font,
    tolerance: float = CELL_TOLERANCE,
    target: float = CELL_FIT_TARGET,
) -> list[str]:
    """Pull letter ink back inside the monospaced cell.

    Accented composites drift out of the cell at heavy weights - the circumflex
    on h reached 74 units past the left edge - because the mark keeps its own
    position while the base grows. Centring the assembly costs nothing: the
    advance is fixed either way.
    """
    glyphs = font["glyf"]
    candidates = _cell_fit_candidates(font)
    adjusted: list[str] = []
    for glyph_name in font.getGlyphOrder():
        if glyph_name not in candidates:
            continue
        glyph = glyphs[glyph_name]
        if glyph.numberOfContours == 0:
            continue
        if font["hmtx"].metrics[glyph_name][0] != ADVANCE:
            continue
        coordinates, _, _ = glyph.getCoordinates(glyphs)
        if not len(coordinates):
            continue
        xs = [x for x, _ in coordinates]
        x_min, x_max = min(xs), max(xs)
        if x_min >= -tolerance and x_max <= ADVANCE + tolerance:
            continue
        shift = round((ADVANCE - (x_min + x_max)) / 2)
        if glyph.isComposite():
            # A composite cannot be compressed without decomposing it, so it is
            # only recentred; any residual overhang ends up symmetric.
            for component in glyph.components:
                component.x += shift
        else:
            width = x_max - x_min
            allowed = ADVANCE + 2 * target
            factor = min(1.0, allowed / width) if width else 1.0
            centre = ADVANCE / 2
            glyph.coordinates = GlyphCoordinates(
                [
                    (round(centre + (x + shift - centre) * factor), y)
                    for x, y in glyph.coordinates
                ]
            )
        glyph.recalcBounds(glyphs)
        font["hmtx"].metrics[glyph_name] = (ADVANCE, glyph.xMin)
        adjusted.append(glyph_name)
    return adjusted


DOTTED_COUNTER_NAMES = frozenset({"O", "o", "zero"})

# A circle of diameter d carries pi/4 of the ink of a d-wide square, so the
# diameter grows to keep the dot's weight where the square pass had calibrated it.
# At Regular this lands on 119 units, the width the dot was drawn at originally.
ROUND_DOT_SCALE = 1.12
# Two quadratic segments per quarter, with the implied on-curve point falling on
# the circle. 0.4477 is the offset that minimises radial error.
ROUND_DOT_CONTROL = 0.4477


def _circle_contour(center_x: float, center_y: float, radius: float, clockwise: bool):
    """Twelve points: four on-curve extremes and two controls per quarter."""
    control = radius * ROUND_DOT_CONTROL
    points = [
        ((center_x, center_y - radius), True),
        ((center_x - control, center_y - radius), False),
        ((center_x - radius, center_y - control), False),
        ((center_x - radius, center_y), True),
        ((center_x - radius, center_y + control), False),
        ((center_x - control, center_y + radius), False),
        ((center_x, center_y + radius), True),
        ((center_x + control, center_y + radius), False),
        ((center_x + radius, center_y + control), False),
        ((center_x + radius, center_y), True),
        ((center_x + radius, center_y - control), False),
        ((center_x + control, center_y - radius), False),
    ]
    if not clockwise:
        points = [points[0], *reversed(points[1:])]
    return [((round(x), round(y)), on_curve) for (x, y), on_curve in points]


def round_counter_dot(glyph) -> None:
    """Draw the counter dot in O, o and zero as a circle, centred in its counter.

    The free-standing dots and tittles stay square; only these three counters are
    round, which is how they were drawn before the square pass generalised to
    every dot-like mark.
    """
    ranges = _contour_ranges(glyph)
    if len(ranges) < 3:
        return
    order = sorted(
        range(len(ranges)),
        key=lambda index: abs(_signed_area(glyph.coordinates, ranges[index])),
    )
    dot_index, counter_index = order[0], order[-2]
    dot = ranges[dot_index]
    dot_points = [glyph.coordinates[index] for index in dot]
    counter_points = [glyph.coordinates[index] for index in ranges[counter_index]]

    def extent(points):
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        return min(xs), max(xs), min(ys), max(ys)

    x_min, x_max, y_min, y_max = extent(dot_points)
    radius = max(x_max - x_min, y_max - y_min) * ROUND_DOT_SCALE / 2
    counter_x0, counter_x1, counter_y0, counter_y1 = extent(counter_points)
    clockwise = _signed_area(glyph.coordinates, dot) < 0
    circle = _circle_contour(
        (counter_x0 + counter_x1) / 2,
        (counter_y0 + counter_y1) / 2,
        radius,
        clockwise,
    )

    coordinates = list(glyph.coordinates)
    flags = list(glyph.flags)
    head_coords, head_flags = coordinates[: dot.start], flags[: dot.start]
    tail_coords, tail_flags = coordinates[dot.stop :], flags[dot.stop :]
    glyph.coordinates = GlyphCoordinates(
        head_coords + [point for point, _ in circle] + tail_coords
    )
    glyph.flags = bytearray(
        list(head_flags)
        + [1 if on_curve else 0 for _, on_curve in circle]
        + list(tail_flags)
    )
    shift = len(circle) - len(dot)
    glyph.endPtsOfContours = [
        endpoint + (shift if index >= dot_index else 0)
        for index, endpoint in enumerate(glyph.endPtsOfContours)
    ]


def invert_glyph(source, *, center_y: float = CAP_HEIGHT / 2):
    from copy import deepcopy

    glyph = deepcopy(source)
    if glyph.isComposite():
        raise ValueError("Only simple glyphs can be inverted")
    glyph.coordinates = type(glyph.coordinates)(
        [
            (
                round(ADVANCE - x),
                round(center_y * 2 - y),
            )
            for x, y in glyph.coordinates
        ]
    )
    return glyph


def install_reference_glyphs(font, weight: float, opsz: float) -> None:
    glyphs = font["glyf"]
    for glyph_name in REFERENCE_SPECS:
        glyph = build_reference_glyph(glyph_name, weight, opsz)
        if glyph_name == "j":
            _stabilize_reference_j(font, glyph)
        _stabilize_reference_shape(glyph_name, glyph)
        glyph.recalcBounds(glyphs)
        glyphs[glyph_name] = glyph
        font["hmtx"].metrics[glyph_name] = (ADVANCE, glyph.xMin)

    for inverted, source in (("exclamdown", "exclam"), ("questiondown", "question")):
        glyph = invert_glyph(glyphs[source])
        glyph.recalcBounds(glyphs)
        glyphs[inverted] = glyph
        font["hmtx"].metrics[inverted] = (ADVANCE, glyph.xMin)


def _h_strokes(font) -> tuple[int, int]:
    h_glyph = font["glyf"]["H"]
    coordinates, _, _ = h_glyph.getCoordinates(font["glyf"])
    vertical = round(abs(coordinates[2][0] - coordinates[1][0]))
    y_values = sorted({round(y) for _, y in coordinates})
    horizontal = y_values[-2] - y_values[1]
    return vertical, horizontal


def _stabilize_preserved_t(font, glyph) -> None:
    vertical_stem, horizontal_stroke = _h_strokes(font)
    points = glyph.coordinates

    center_x = sum(points[index][0] for index in (7, 8, 9, 10)) / 4
    left = round(center_x - vertical_stem / 2)
    right = round(center_x + vertical_stem / 2)
    for index in (7, 8):
        points[index] = (left, points[index][1])
    for index in (9, 10):
        points[index] = (right, points[index][1])

    cap_y = round((points[8][1] + points[9][1]) / 2)
    points[8] = (points[8][0], cap_y)
    points[9] = (points[9][0], cap_y)

    crossbar_top = round(
        sum(points[index][1] for index in (6, 7, 10, 11)) / 4
    )
    for index in (6, 7, 10, 11):
        points[index] = (points[index][0], crossbar_top)
    crossbar_bottom = crossbar_top - horizontal_stroke
    for index in (4, 5, 12, 13):
        points[index] = (points[index][0], crossbar_bottom)

    for index in (16, 17, 18):
        points[index] = (points[index][0], horizontal_stroke)
    terminal_x = round((points[18][0] + points[19][0]) / 2)
    points[18] = (terminal_x, horizontal_stroke)
    points[19] = (terminal_x, 0)


def _stabilize_preserved_r(font, glyph) -> None:
    vertical_stem, _ = _h_strokes(font)
    points = glyph.coordinates

    cap_y = max(points[index][1] for index in (4, 5))
    points[0] = (points[0][0], cap_y)
    points[1] = (points[1][0], cap_y)
    departure_x = points[1][0] + max(6, round(vertical_stem * 0.12))
    points[2] = (departure_x, cap_y)
    points[3] = (max(points[3][0], departure_x + 1), cap_y)

    terminal_inner = points[10]
    shoulder_inner = points[14]
    for index, fraction in zip((11, 12, 13), (0.25, 0.5, 0.75)):
        points[index] = (
            round(
                terminal_inner[0]
                + (shoulder_inner[0] - terminal_inner[0]) * fraction
            ),
            round(
                terminal_inner[1]
                + (shoulder_inner[1] - terminal_inner[1]) * fraction
            ),
        )


def _stabilize_preserved_ascender(font, name: str, glyph) -> None:
    _, horizontal_stroke = _h_strokes(font)
    points = glyph.coordinates

    if name == "f":
        top = round(sum(points[index][1] for index in (7, 8, 9)) / 3)
        bottom = top - horizontal_stroke
        for index in (7, 8, 9):
            points[index] = (points[index][0], top)
        for index in (10, 11, 12):
            points[index] = (points[index][0], bottom)
    elif name == "l":
        top = round((points[5][1] + points[6][1]) / 2)
        bottom = top - horizontal_stroke
        for index in (5, 6):
            points[index] = (points[index][0], top)
        for index in (3, 4):
            points[index] = (points[index][0], bottom)


def _stabilize_reference_j(font, glyph) -> None:
    _, horizontal_stroke = _h_strokes(font)
    points = glyph.coordinates

    bar_top = round((points[9][1] + points[10][1]) / 2)
    bar_bottom = bar_top - horizontal_stroke
    points[7] = (points[6][0], bar_bottom)
    points[8] = (points[8][0], bar_bottom)
    points[9] = (points[8][0], bar_top)
    right_edge = round((points[10][0] + points[11][0]) / 2)
    points[10] = (right_edge, bar_top)
    points[11] = (right_edge, points[11][1])

    terminal_bottom = round((points[0][1] + points[15][1]) / 2)
    terminal_top = round((points[1][1] + points[2][1]) / 2)
    points[0] = (points[0][0], terminal_bottom)
    points[15] = (points[15][0], terminal_bottom)
    points[1] = (points[1][0], terminal_top)
    points[2] = (points[2][0], terminal_top)
    _reshape_square_contour(
        glyph,
        1,
        size=_contour_square_size(glyph, 1),
        top=LOWERCASE_ASCENDER_HEIGHT,
    )


def _stabilize_reference_shape(name: str, glyph) -> None:
    points = glyph.coordinates

    if name == "K":
        # Fit the cell by pulling in the arm and leg reach only. Scaling the whole
        # glyph would thin the stem with it, and the stem is the one measurement
        # that has to agree with H at every weight.
        target_min = 18
        target_max = ADVANCE - 18
        x_min = min(x for x, _ in points)
        stem_right = max(
            x for index, (x, y) in enumerate(points) if index in {2, 3, 13, 14}
        )
        shift = max(0, target_min - x_min)
        if shift:
            points_shifted = [(x + shift, y) for x, y in points]
            for index, point in enumerate(points_shifted):
                points[index] = point
            stem_right += shift
        x_max = max(x for x, _ in points)
        if x_max > target_max and x_max > stem_right:
            factor = (target_max - stem_right) / (x_max - stem_right)
            for index, (x, y) in enumerate(points):
                if x > stem_right:
                    points[index] = (round(stem_right + (x - stem_right) * factor), y)

    elif name == "J":
        terminal_y = round((points[6][1] + points[7][1]) / 2)
        points[6] = (points[6][0], terminal_y)
        points[7] = (points[7][0], terminal_y)
        control_min = min(points[8][0], points[10][0])
        control_max = max(points[8][0], points[10][0])
        points[9] = (
            min(control_max, max(control_min, points[9][0])),
            points[9][1],
        )

    elif name == "S":
        bottom_terminal = round((points[0][1] + points[1][1]) / 2)
        top_terminal = round((points[31][1] + points[32][1]) / 2)
        points[0] = (points[0][0], bottom_terminal)
        points[1] = (points[1][0], bottom_terminal)
        points[31] = (points[31][0], top_terminal)
        points[32] = (points[32][0], top_terminal)
        for index in (24, 25, 27, 28):
            points[index] = (points[index][0], min(CAP_HEIGHT, points[index][1]))
        for index in (54, 55, 57, 58):
            points[index] = (points[index][0], max(0, points[index][1]))

    elif name == "semicolon":
        tail = list(_contour_ranges(glyph)[1])
        lower_y = round((points[tail[0]][1] + points[tail[3]][1]) / 2)
        upper_y = round((points[tail[1]][1] + points[tail[2]][1]) / 2)
        for index in (tail[0], tail[3]):
            points[index] = (points[index][0], lower_y)
        for index in (tail[1], tail[2]):
            points[index] = (points[index][0], upper_y)


def install_preserved_master_glyphs(
    font,
    weight: float,
    opsz: float,
) -> None:
    glyphs = font["glyf"]
    for glyph_name in PRESERVED_MASTER_GLYPH_NAMES:
        glyph = _master_outline(glyph_name, weight)
        _apply_signature_optical_geometry(glyph_name, glyph, opsz, weight)
        if glyph_name in DOTTED_COUNTER_NAMES:
            round_counter_dot(glyph)
        if glyph_name == "t":
            _stabilize_preserved_t(font, glyph)
        elif glyph_name in {"f", "l"}:
            _stabilize_preserved_ascender(font, glyph_name, glyph)
        glyph.recalcBounds(glyphs)
        glyphs[glyph_name] = glyph
        font["hmtx"].metrics[glyph_name] = (ADVANCE, glyph.xMin)


def _representative_chars(font) -> dict[str, str]:
    result: dict[str, str] = {}
    for codepoint, glyph_name in font.getBestCmap().items():
        result.setdefault(glyph_name, chr(codepoint))
    for glyph_name in font.getGlyphOrder():
        if glyph_name in result:
            continue
        base_name = glyph_name.split(".", 1)[0]
        if base_name in result:
            result[glyph_name] = result[base_name]
    return result


def _lowercase_y(y: float, opsz: float) -> float:
    target_x_height = optical_value(opsz, 540, X_HEIGHT, 500)
    if 0 <= y <= X_HEIGHT:
        return y * target_x_height / X_HEIGHT
    if X_HEIGHT < y <= LOWERCASE_ASCENDER_HEIGHT:
        return target_x_height + (
            (y - X_HEIGHT)
            * (LOWERCASE_ASCENDER_HEIGHT - target_x_height)
            / (LOWERCASE_ASCENDER_HEIGHT - X_HEIGHT)
        )
    if y < 0:
        target_descender = optical_value(
            opsz,
            -202,
            LOWERCASE_DESCENDER,
            -188,
        )
        return y * target_descender / LOWERCASE_DESCENDER
    return y


def apply_optical_geometry(
    font,
    opsz: float,
    *,
    excluded: frozenset[str] = frozenset(),
) -> None:
    """Apply the family-wide Text-to-Display optical-size design."""
    if opsz == DEFAULT_OPSZ:
        return
    glyphs = font["glyf"]
    hmtx = font["hmtx"]
    representative = _representative_chars(font)

    for glyph_name in font.getGlyphOrder():
        if (
            glyph_name in excluded
            or glyph_name in SQUARE_MARK_NAMES
            or ".liga" in glyph_name
            or hmtx.metrics[glyph_name][0] != ADVANCE
        ):
            continue
        char = representative.get(glyph_name)
        if char:
            category = unicodedata.category(char)
            codepoint = ord(char)
            if 0x2500 <= codepoint <= 0x259F:
                continue
        else:
            category = ""

        glyph = glyphs[glyph_name]
        if glyph.isComposite():
            # Base components receive optical geometry through their own
            # outlines. Only zero-advance marks need their attachment offset
            # adjusted with the cell.
            for component in glyph.components:
                if hmtx.metrics[component.glyphName][0] == 0:
                    factor = optical_value(opsz, 1.008, 1, 0.985)
                    component.x = round(
                        ADVANCE / 2 + (component.x - ADVANCE / 2) * factor
                    )
            continue
        if glyph.numberOfContours <= 0:
            continue

        if category == "Ll":
            x_factor = optical_value(opsz, 1.010, 1, 0.980)
        elif category == "Lu":
            x_factor = optical_value(opsz, 1.005, 1, 0.975)
        elif category.startswith("N"):
            x_factor = optical_value(opsz, 1.008, 1, 0.985)
        else:
            x_factor = optical_value(opsz, 1.003, 1, 0.985)

        coordinates = []
        for x, y in glyph.coordinates:
            x = ADVANCE / 2 + (x - ADVANCE / 2) * x_factor
            if category == "Ll":
                y = _lowercase_y(y, opsz)
            coordinates.append((round(x), round(y)))
        glyph.coordinates = type(glyph.coordinates)(coordinates)
        glyph.recalcBounds(glyphs)
        hmtx.metrics[glyph_name] = (ADVANCE, glyph.xMin)
