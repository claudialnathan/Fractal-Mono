"""CLN Mono outline construction and optical-size geometry."""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import parse_path


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
    """Return the canonical CLN drawing paths in compact design coordinates."""
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
            "M0.000 84.000L0.000 0.000L10.800 0.000L10.800 36.360"
            "C12.000 35.040 13.320 33.480 14.640 31.920L42.720 0.000"
            "L55.920 0.000L22.440 37.560L61.320 84.000L47.280 84.000"
            "L15.360 45.480L10.800 50.640L10.800 84.000Z"
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


CAP_SCALE = CAP_HEIGHT / 84
REFERENCE_SPECS = {
    "J": ReferenceSpec(CAP_SCALE, CAP_HEIGHT, 79, (-47, CAP_HEIGHT), True),
    "j": ReferenceSpec(25 / 3, LOWERCASE_ASCENDER_HEIGHT, 79, (), False),
    "K": ReferenceSpec(CAP_SCALE, CAP_HEIGHT, 87, (0, CAP_HEIGHT), True),
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
SQUARE_MARK_NAMES = frozenset({"uni0307", "uni0308", "dotbelowcomb"})


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


def _offset_glyph(glyph, amount: float, anchor_y: tuple[int, ...]):
    if not amount:
        return glyph
    coordinates = list(glyph.coordinates)
    expanded = list(coordinates)
    for contour_range in _contour_ranges(glyph):
        indices = list(contour_range)
        area = _signed_area(coordinates, contour_range)
        outward_sign = 1 if area > 0 else -1
        for position, index in enumerate(indices):
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
            moved_y = y + normal_y * amount
            if any(abs(y - anchor) <= 1 for anchor in anchor_y):
                moved_y = y
            expanded[index] = (
                round(x + normal_x * amount),
                round(moved_y),
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
    target = size if size is not None else max(x_max - x_min, y_max - y_min)
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    if top is not None:
        center_y = top - target / 2
    clockwise = _signed_area(glyph.coordinates, range(contour[0], contour[-1] + 1)) < 0
    if clockwise:
        points = [
            (center_x - target / 2, center_y + target / 2),
            (center_x + target / 2, center_y + target / 2),
            (center_x + target / 2, center_y - target / 2),
            (center_x - target / 2, center_y - target / 2),
        ]
    else:
        points = [
            (center_x - target / 2, center_y - target / 2),
            (center_x + target / 2, center_y - target / 2),
            (center_x + target / 2, center_y + target / 2),
            (center_x - target / 2, center_y + target / 2),
        ]
    for index, point in zip(contour, points):
        glyph.coordinates[index] = tuple(round(value) for value in point)
        glyph.flags[index] |= 1


def square_size(stem: float, opsz: float, *, scale: float = 1) -> float:
    base = 112 + (stem - REGULAR_STEM) * 0.45
    optical = optical_value(opsz, 1.06, 1, 0.90)
    return max(64, base * optical * scale)


def build_reference_glyph(name: str, weight: float, opsz: float):
    spec = REFERENCE_SPECS[name]
    stem = stem_for_weight(weight)
    heavy_correction = {
        "J": 0.06,
        "j": 0.10,
        "K": 0.08,
        "M": 0.16,
        "W": 0.16,
        "S": 0.10,
        "question": 0.10,
        "asciicircum": 0.15,
    }.get(name, 0)
    heavy_fraction = max(0, weight - 500) / 300
    target_stem = stem * (1 - heavy_fraction * heavy_correction)
    if name == "asterisk":
        target_stem *= 0.85
    glyph = _reference_glyph(name)
    glyph = _offset_glyph(
        glyph,
        (target_stem - spec.reference_stem) / 2,
        spec.anchor_y,
    )

    if spec.optical_x:
        extreme_fit = 1 - max(0, weight - 500) / 300 * 0.03
        glyph = _scale_x(
            glyph,
            optical_value(opsz, 1.006, 1, 0.975) * extreme_fit,
        )

    if name == "asciicircum":
        # Preserve the inner apex order as the two strokes thicken. A generic
        # contour offset can otherwise invert these two points above Medium.
        right_apex = glyph.coordinates[5]
        left_apex = glyph.coordinates[6]
        if right_apex[0] <= left_apex[0]:
            glyph.coordinates[5] = (left_apex[0], right_apex[1])
            glyph.coordinates[6] = (right_apex[0], left_apex[1])

    if name == "j":
        ranges = _contour_ranges(glyph)
        body = ranges[0]
        target_x_height = optical_value(opsz, 540, X_HEIGHT, 500)
        for index in body:
            x, y = glyph.coordinates[index]
            if 0 <= y <= X_HEIGHT:
                y = y * target_x_height / X_HEIGHT
            elif X_HEIGHT < y <= LOWERCASE_ASCENDER_HEIGHT:
                y = target_x_height + (
                    (y - X_HEIGHT)
                    * (LOWERCASE_ASCENDER_HEIGHT - target_x_height)
                    / (LOWERCASE_ASCENDER_HEIGHT - X_HEIGHT)
                )
            elif y < 0:
                descender_target = optical_value(
                    opsz,
                    -202,
                    LOWERCASE_DESCENDER,
                    -188,
                )
                y = y * descender_target / LOWERCASE_DESCENDER
            glyph.coordinates[index] = (x, round(y))
        if weight > 500:
            glyph = _scale_x(glyph, 1 - (weight - 500) / 300 * 0.02)
        _reshape_square_contour(
            glyph,
            1,
            size=square_size(stem, opsz),
            top=LOWERCASE_ASCENDER_HEIGHT,
        )
    elif name in {"period", "exclam", "question", "colon", "semicolon"}:
        for contour_index, contour in enumerate(_contour_ranges(glyph)):
            if len(contour) == 4 and all(glyph.flags[index] & 1 for index in contour):
                pin_top = None
                if name in {"exclam", "question"} and contour_index == 1:
                    pin_top = None
                _reshape_square_contour(glyph, contour_index, top=pin_top)

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
    half = size / 2
    return [
        (round(center_x - half), round(center_y + half)),
        (round(center_x + half), round(center_y + half)),
        (round(center_x + half), round(center_y - half)),
        (round(center_x - half), round(center_y - half)),
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


def _last_contour_center(glyph) -> tuple[float, float]:
    contour = list(_contour_ranges(glyph)[-1])
    coordinates = [glyph.coordinates[index] for index in contour]
    return (
        (min(x for x, _ in coordinates) + max(x for x, _ in coordinates)) / 2,
        (min(y for _, y in coordinates) + max(y for _, y in coordinates)) / 2,
    )


def replace_final_contour_with_square(
    font,
    glyph_name: str,
    weight: float,
    opsz: float,
    *,
    scale: float = 1,
) -> None:
    glyphs = font["glyf"]
    glyph = glyphs[glyph_name]
    assert not glyph.isComposite() and glyph.numberOfContours > 0
    ranges = _contour_ranges(glyph)
    center_x, center_y = _last_contour_center(glyph)
    contours = [
        [glyph.coordinates[index] for index in contour]
        for contour in ranges[:-1]
    ]
    contours.append(
        _clockwise_square(
            center_x,
            center_y,
            square_size(stem_for_weight(weight), opsz, scale=scale),
        )
    )
    _replace_contours(glyph, contours)
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
        glyph.recalcBounds(glyphs)
        glyphs[glyph_name] = glyph
        font["hmtx"].metrics[glyph_name] = (ADVANCE, glyph.xMin)

    for inverted, source in (("exclamdown", "exclam"), ("questiondown", "question")):
        glyph = invert_glyph(glyphs[source])
        glyph.recalcBounds(glyphs)
        glyphs[inverted] = glyph
        font["hmtx"].metrics[inverted] = (ADVANCE, glyph.xMin)


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


def stabilize_lowercase_t(font, weight: float, opsz: float) -> None:
    """Keep the t ascender rectangular at the light end of the axis."""
    glyphs = font["glyf"]
    glyph = glyphs["t"]
    assert not glyph.isComposite()
    assert len(glyph.coordinates) == 20
    center_x = (
        glyph.coordinates[8][0] + glyph.coordinates[9][0]
    ) / 2
    width = stem_for_weight(weight) * optical_value(
        opsz,
        1.010,
        1,
        0.980,
    )
    left = round(center_x - width / 2)
    right = round(center_x + width / 2)
    for index in (7, 8):
        glyph.coordinates[index] = (left, glyph.coordinates[index][1])
    for index in (9, 10):
        glyph.coordinates[index] = (right, glyph.coordinates[index][1])
    glyph.recalcBounds(glyphs)
    font["hmtx"].metrics["t"] = (ADVANCE, glyph.xMin)
