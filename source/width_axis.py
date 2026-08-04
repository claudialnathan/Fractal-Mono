"""Compatible width-axis geometry for Fractal Mono.

The registered ``wdth`` axis changes the width of the text, so every spacing
glyph receives a width-dependent advance.  The outline treatment is deliberately
different from horizontal scaling:

* the advance and the reach of the drawing follow the width percentage;
* local horizontal compensation restores the perpendicular thickness that an
  anisotropic scale would otherwise remove from vertical and diagonal strokes;
* y coordinates never move, keeping the baseline, x-height, cap height,
  overshoots, and vertical metrics independent of width;
* composite offsets and GPOS mark anchors follow the same deformation field;
* programming-ligature drawings scale about the cell-grid origin so their
  negative placeholder-cell boundaries remain aligned.

Every operation moves existing points or components only.  Contour count, point
order, on/off-curve flags, and component structure therefore stay compatible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

import fitting
import fractal_geometry


WIDTH_MIN = 85.0
WIDTH_DEFAULT = 100.0
WIDTH_MAX = 115.0
WIDTH_MASTERS = (WIDTH_MIN, WIDTH_DEFAULT, WIDTH_MAX)

# Width is a percentage of the normal design.  The default cell is 579 units, so
# the registered values also describe line length exactly, apart from integer
# rounding at the individual cell.
NORMAL_ADVANCE = 579

# These outlines are made primarily from diagonal runs.  Translating each
# horizontal run as a unit moves its skeleton without scaling the ink inside
# that run. This is topology-safe and keeps their diagonals from becoming 20%
# heavier at the Expanded endpoint.
SCANLINE_BAND_GLYPHS = frozenset(
    {
        "K",
        "M",
        "N",
        "V",
        "W",
        "X",
        "asterisk",
        "k",
        "v",
        "w",
        "y",
    }
)

@dataclass(frozen=True)
class WidthReport:
    width: float
    advance: int
    simple_glyphs: int
    composite_glyphs: int
    anchors: int


def advance_at_width(advance: int, width: float) -> int:
    """Return an advance on the registered percentage scale."""
    if advance == 0:
        return 0
    return round(advance * width / WIDTH_DEFAULT)


def _contour_ranges(glyph) -> list[range]:
    ranges: list[range] = []
    start = 0
    for endpoint in glyph.endPtsOfContours:
        ranges.append(range(start, endpoint + 1))
        start = endpoint + 1
    return ranges


def _is_grid_ligature(glyph_name: str) -> bool:
    return ".liga" in glyph_name


def _base_shift(
    glyph_name: str,
    advance: int,
    centre: float,
    scale: float,
) -> float:
    """Affine x shift paired with ``x * scale`` for one glyph."""
    if advance:
        if _is_grid_ligature(glyph_name):
            return 0.0
        target_advance = round(advance * scale)
        return target_advance / 2 - scale * advance / 2
    # A zero-advance combining mark changes width about its own visual centre.
    return centre - scale * centre


def _scanline_band_deform(
    glyph,
    original,
    scale: float,
    shift: float,
    amount: float,
):
    contours = []
    start = 0
    for endpoint in glyph.endPtsOfContours:
        contours.append(
            [tuple(original[index]) for index in range(start, endpoint + 1)]
        )
        start = endpoint + 1

    transformed = GlyphCoordinates()
    for x, y in original:
        spans = fitting._spans(contours, y)
        if not spans:
            for offset in (0.25, -0.25, 1.0, -1.0):
                spans = fitting._spans(contours, y + offset)
                if spans:
                    break
        if not spans:
            transformed.append((round(x * scale + shift), y))
            continue

        def distance(span):
            if span[0] <= x <= span[1]:
                return 0.0
            return min(abs(x - span[0]), abs(x - span[1]))

        span = min(spans, key=distance)
        centre = (span[0] + span[1]) / 2
        affine_x = x * scale + shift
        run_shift = centre * scale + shift - centre
        band_x = x + run_shift
        transformed.append(
            (round(affine_x + (band_x - affine_x) * amount), y)
        )
    return transformed


def _deform_simple_glyph(
    glyph,
    glyf,
    glyph_name: str,
    scale: float,
    shift: float,
    stem: float,
    structural: bool,
    scanline_amount: float,
) -> None:
    original = GlyphCoordinates(glyph.coordinates)
    transformed = (
        _scanline_band_deform(
            glyph,
            original,
            scale,
            shift,
            scanline_amount,
        )
        if scanline_amount
        else GlyphCoordinates(
            [(round(x * scale + shift), y) for x, y in original]
        )
    )
    bands = (
        fitting._ink_bands(glyph, glyf)
        if structural and not scanline_amount
        else None
    )
    if bands is not None:
        left_start, left_end, right_start, right_end = bands
        if right_start - left_end > fitting.MIN_BAND_SEPARATION:
            shift_left = left_start * scale + shift - left_start
            shift_right = right_end * scale + shift - right_end

            def structural_x(x: float) -> float:
                if x <= left_end:
                    return x + shift_left
                if x >= right_start:
                    return x + shift_right
                fraction = (x - left_end) / (right_start - left_end)
                new_left = left_end + shift_left
                new_right = right_start + shift_right
                return new_left + (new_right - new_left) * fraction

            transformed = GlyphCoordinates(
                [(round(structural_x(x)), y) for x, y in original]
            )
        else:
            bands = None

    for indices in _contour_ranges(glyph):
        if len(indices) < 2:
            continue
        contour_xs = [original[index][0] for index in indices]
        contour_ys = [original[index][1] for index in indices]
        if bands is not None:
            left_start, left_end, right_start, right_end = bands
            # A centre dot or another isolated contour is not part of either
            # structural side. It is handled as a rigid small contour below.
            isolated_centre = (
                min(contour_xs) > left_end
                and max(contour_xs) < right_start
            )
            if not isolated_centre:
                continue
        if scanline_amount:
            continue
        contour_width = max(contour_xs) - min(contour_xs)
        contour_height = max(contour_ys) - min(contour_ys)
        # A thin vertical construction and a compact dot keep their drawn width
        # and simply travel with the width field. Every other unclassified
        # contour takes the safe affine draft; unlike independent point-normal
        # offsets, an affine contour cannot fold or self-intersect.
        rigid = (
            glyph_name in {"semicolon", "semicolon.case"}
            or contour_width <= stem * 1.6
            or (contour_width <= 140 and contour_height <= 140)
        )
        if rigid:
            contour_centre = (min(contour_xs) + max(contour_xs)) / 2
            mapped_centre = contour_centre * scale + shift
            contour_shift = mapped_centre - contour_centre
            for point_index in indices:
                x, y = original[point_index]
                transformed[point_index] = (
                    round(x + contour_shift),
                    y,
                )

    glyph.coordinates = transformed


def _glyph_centres(font) -> dict[str, float]:
    glyf = font["glyf"]
    centres: dict[str, float] = {}
    for glyph_name in font.getGlyphOrder():
        glyph = glyf[glyph_name]
        if glyph.numberOfContours > 0:
            glyph.recalcBounds(glyf)
            centres[glyph_name] = (glyph.xMin + glyph.xMax) / 2
        elif glyph.isComposite():
            glyph.recalcBounds(glyf)
            centres[glyph_name] = (glyph.xMin + glyph.xMax) / 2
        else:
            centres[glyph_name] = 0.0
    return centres


def _normal_line(first, second):
    delta_x = second[0] - first[0]
    delta_y = second[1] - first[1]
    length = math.hypot(delta_x, delta_y)
    if length < 0.5:
        raise ValueError("Cannot derive a width master from a zero-length edge")
    a = -delta_y / length
    b = delta_x / length
    return a, b, a * first[0] + b * first[1]


def _restore_a_edge(
    original,
    updated,
    outer: tuple[int, int],
    inner: tuple[int, int],
) -> None:
    """Keep one of A's declared inner edges at its approved distance."""
    original_line = _normal_line(original[outer[0]], original[outer[1]])
    signed_distances = [
        original_line[0] * original[index][0]
        + original_line[1] * original[index][1]
        - original_line[2]
        for index in inner
    ]
    target = sum(abs(value) for value in signed_distances) / len(
        signed_distances
    )
    side = 1.0 if sum(signed_distances) >= 0 else -1.0

    a, b, c = _normal_line(updated[outer[0]], updated[outer[1]])
    target_c = c + side * target
    if abs(a) < 0.08:
        return
    for index in inner:
        _, y = updated[index]
        updated[index] = ((target_c - b * y) / a, y)


def _restore_a_diagonals(glyph, original) -> None:
    """Restate A's four diagonal edge pairs after changing its reach.

    A is the one source-derived diagonal whose counter crosses the structural
    deformation zone.  A generic point-normal correction makes its upper
    diagonals 31% lighter at Condensed and 21% heavier at Expanded.  These
    explicit compatible edges retain the approved master thickness instead.
    """
    if len(glyph.coordinates) != 17 or glyph.endPtsOfContours != [7, 16]:
        return
    before = [tuple(point) for point in glyph.coordinates]
    updated = list(before)
    for outer, inner in (
        ((0, 1), (8, 16)),
        ((2, 3), (9, 10)),
        ((0, 1), (7, 6)),
        ((2, 3), (4, 5)),
    ):
        _restore_a_edge(original, updated, outer, inner)

    # Carry the counter's quadratic handles with the corrected lower endpoints
    # while leaving its approved apex at point 13 on the cell centre.
    for start, end, controls in (
        (10, 13, (11, 12)),
        (13, 16, (14, 15)),
    ):
        start_delta = (
            updated[start][0] - before[start][0],
            updated[start][1] - before[start][1],
        )
        end_delta = (
            updated[end][0] - before[end][0],
            updated[end][1] - before[end][1],
        )
        for step, index in enumerate(controls, start=1):
            fraction = step / (len(controls) + 1)
            updated[index] = (
                before[index][0]
                + start_delta[0]
                + (end_delta[0] - start_delta[0]) * fraction,
                before[index][1]
                + start_delta[1]
                + (end_delta[1] - start_delta[1]) * fraction,
            )
    # The two apex controls must stay on their own side of the meeting point.
    # At the expanded endpoint the large counter correction can otherwise put
    # both just across the apex and make the quadratic curve double back.
    updated[12] = (
        max(updated[12][0], updated[13][0] + 1),
        updated[12][1],
    )
    updated[14] = (
        min(updated[14][0], updated[13][0] - 1),
        updated[14][1],
    )
    glyph.coordinates = GlyphCoordinates(
        [(round(x), round(y)) for x, y in updated]
    )


def _move_anchor(anchor, glyph_name: str, scale: float, shifts) -> bool:
    if anchor is None:
        return False
    anchor.XCoordinate = round(
        anchor.XCoordinate * scale + shifts[glyph_name]
    )
    return True


def _deform_gpos_anchors(font, scale: float, shifts) -> int:
    if "GPOS" not in font:
        return 0
    count = 0
    for lookup in font["GPOS"].table.LookupList.Lookup:
        lookup_type = lookup.LookupType
        subtables = lookup.SubTable
        if lookup_type == 9:
            lookup_type = subtables[0].ExtensionLookupType
            subtables = [item.ExtSubTable for item in subtables]

        if lookup_type == 4:  # MarkToBase attachment
            for subtable in subtables:
                for glyph_name, record in zip(
                    subtable.MarkCoverage.glyphs,
                    subtable.MarkArray.MarkRecord,
                ):
                    count += _move_anchor(
                        record.MarkAnchor, glyph_name, scale, shifts
                    )
                for glyph_name, record in zip(
                    subtable.BaseCoverage.glyphs,
                    subtable.BaseArray.BaseRecord,
                ):
                    for anchor in record.BaseAnchor:
                        count += _move_anchor(
                            anchor, glyph_name, scale, shifts
                        )
        elif lookup_type == 6:  # MarkToMark attachment
            for subtable in subtables:
                for glyph_name, record in zip(
                    subtable.Mark1Coverage.glyphs,
                    subtable.Mark1Array.MarkRecord,
                ):
                    count += _move_anchor(
                        record.MarkAnchor, glyph_name, scale, shifts
                    )
                for glyph_name, record in zip(
                    subtable.Mark2Coverage.glyphs,
                    subtable.Mark2Array.Mark2Record,
                ):
                    for anchor in record.Mark2Anchor:
                        count += _move_anchor(
                            anchor, glyph_name, scale, shifts
                        )
    return count


def apply_width_master(font, width: float, stem: float) -> WidthReport:
    """Turn a normal-width static master into a compatible width master."""
    if width == WIDTH_DEFAULT:
        return WidthReport(
            width=width,
            advance=NORMAL_ADVANCE,
            simple_glyphs=0,
            composite_glyphs=0,
            anchors=0,
        )
    if not WIDTH_MIN <= width <= WIDTH_MAX:
        raise ValueError(
            f"Width {width:g} is outside {WIDTH_MIN:g}–{WIDTH_MAX:g}"
        )

    scale = width / WIDTH_DEFAULT
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    centres = _glyph_centres(font)
    advances = {
        glyph_name: hmtx.metrics[glyph_name][0]
        for glyph_name in font.getGlyphOrder()
    }
    shifts = {
        glyph_name: _base_shift(
            glyph_name,
            advances[glyph_name],
            centres[glyph_name],
            scale,
        )
        for glyph_name in font.getGlyphOrder()
    }

    simple_count = 0
    composite_count = 0
    cmap = font.getBestCmap()
    structural_names = {
        glyph_name
        for codepoint, glyph_name in cmap.items()
        if (
            chr(codepoint) in fitting.SHAPE_CLASS
            or glyph_name in fitting.SHAPE_CLASS
            or glyph_name.split(".", 1)[0] == "zero"
        )
        and glyph_name not in fitting.EXCLUDED
    }
    structural_names.update(
        glyph_name
        for glyph_name in font.getGlyphOrder()
        if (
            glyph_name.split(".", 1)[0] in fitting.SHAPE_CLASS
            or glyph_name.split(".", 1)[0] == "zero"
        )
        and glyph_name.split(".", 1)[0] not in fitting.EXCLUDED
    )
    for glyph_name in font.getGlyphOrder():
        glyph = glyf[glyph_name]
        if glyph.numberOfContours > 0:
            original = GlyphCoordinates(glyph.coordinates)
            thin_expanded_w = (
                scale > 1 and glyph_name == "W" and stem < 45
            )
            scanline_amount = (
                0.9
                if thin_expanded_w
                else float(
                    scale > 1
                    and glyph_name in SCANLINE_BAND_GLYPHS
                )
            )
            _deform_simple_glyph(
                glyph,
                glyf,
                glyph_name,
                scale,
                shifts[glyph_name],
                stem,
                glyph_name in structural_names,
                scanline_amount,
            )
            if thin_expanded_w:
                # At Thin, even a partial scanline translation makes W's
                # microscopic lower vertex cuts cross after grid rounding.
                # The family's existing vertex clamp restores the cut using
                # x-only movement, so the width axis does not disturb y.
                fractal_geometry._stabilize_thin_w(glyph)
            if glyph_name == "A" and scale > 1:
                _restore_a_diagonals(glyph, original)
            simple_count += 1

    for glyph_name in font.getGlyphOrder():
        glyph = glyf[glyph_name]
        if not glyph.isComposite():
            continue
        parent_shift = shifts[glyph_name]
        for component in glyph.components:
            child_shift = shifts[component.glyphName]
            component.x = round(
                component.x * scale + parent_shift - child_shift
            )
        composite_count += 1

    for glyph_name in font.getGlyphOrder():
        glyph = glyf[glyph_name]
        if glyph.numberOfContours > 0 or glyph.isComposite():
            glyph.recalcBounds(glyf)
            left_sidebearing = glyph.xMin
        else:
            left_sidebearing = 0
        hmtx.metrics[glyph_name] = (
            advance_at_width(advances[glyph_name], width),
            left_sidebearing,
        )

    anchor_count = _deform_gpos_anchors(font, scale, shifts)
    font.recalcBBoxes = True
    return WidthReport(
        width=width,
        advance=advance_at_width(NORMAL_ADVANCE, width),
        simple_glyphs=simple_count,
        composite_glyphs=composite_count,
        anchors=anchor_count,
    )
