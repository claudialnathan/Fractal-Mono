"""Option, command and return key symbols.

Drawn by the designer as vectors at one weight each — option at wght 600,
command and return at wght 500, all at 120px with the baseline 120.2px down the
line box. Those drawings are the design authority for shape, position and stroke
proportion; everything here reconstructs them as stroke geometry so the same
drawing holds across the whole weight axis instead of only at the weight it was
made at.

Each symbol keeps its outer bounds fixed and grows its stroke inward, the way a
letter keeps its cap height and grows its stem. Reconstructing at the design
weight reproduces the supplied vector to within a unit, which
`verify_against_drawing` asserts.
"""

from __future__ import annotations

import math

from fontTools.misc.transform import Transform
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import parse_path

ADVANCE = 579
# 120px type on a 132% line box, so the baseline sits 1.01em below the box top.
DRAWING_FONT_SIZE = 120
DRAWING_BASELINE = 120.2
UNITS_PER_PIXEL = 1000 / DRAWING_FONT_SIZE

# Stroke thickness as a fraction of the family stem, taken from each drawing.
# Option was drawn at the family's horizontal-bar weight; return and command are
# deliberately lighter than the letters, which is how the earlier drawings read
# too.
OPTION_STROKE_RATIO = 92.77 / 109.55
RETURN_STROKE_RATIO = 59.72 / 93.00
COMMAND_STROKE_RATIO = 70.00 / 93.00

OPTION_DESIGN_STROKE = 92.77
RETURN_DESIGN_STROKE = 59.72
COMMAND_DESIGN_STROKE = 70.00


def _unit(vector):
    length = math.hypot(*vector)
    return vector[0] / length, vector[1] / length


def _line(start, end):
    direction = _unit((end[0] - start[0], end[1] - start[1]))
    a, b = -direction[1], direction[0]
    return a, b, a * start[0] + b * start[1]


def _intersect(first, second):
    a1, b1, c1 = first
    a2, b2, c2 = second
    determinant = a1 * b2 - a2 * b1
    if abs(determinant) < 1e-9:
        return None
    return (
        (c1 * b2 - c2 * b1) / determinant,
        (a1 * c2 - a2 * c1) / determinant,
    )


def mitred_polyline(points, thickness):
    """One closed contour around a polyline, with true mitres and square caps."""
    half = thickness / 2
    left, right = [], []
    for index in range(len(points) - 1):
        start, end = points[index], points[index + 1]
        a, b, c = _line(start, end)
        left.append((a, b, c + half))
        right.append((a, b, c - half))

    def side(lines, cap_start, cap_end):
        edge = []
        edge.append(_intersect(lines[0], cap_start))
        for first, second in zip(lines, lines[1:]):
            joint = _intersect(first, second)
            if joint is not None:
                edge.append(joint)
        edge.append(_intersect(lines[-1], cap_end))
        return edge

    start_cap = _line(points[0], points[1])
    start_cap = (-start_cap[1], start_cap[0], 0)
    start_cap = (
        start_cap[0],
        start_cap[1],
        start_cap[0] * points[0][0] + start_cap[1] * points[0][1],
    )
    end_cap = _line(points[-2], points[-1])
    end_cap = (-end_cap[1], end_cap[0], 0)
    end_cap = (
        end_cap[0],
        end_cap[1],
        end_cap[0] * points[-1][0] + end_cap[1] * points[-1][1],
    )

    outline = side(left, start_cap, end_cap)
    outline += list(reversed(side(right, start_cap, end_cap)))
    return outline


def _polygon(pen, points):
    pen.moveTo((round(points[0][0]), round(points[0][1])))
    for point in points[1:]:
        pen.lineTo((round(point[0]), round(point[1])))
    pen.closePath()


# --- option ----------------------------------------------------------------
# Outer bounds and the geometry that does not move with stroke weight. The two
# horizontal runs sit against the top and bottom of the box; the left, right and
# inner-bar ends are square caps, so they hold their x wherever the stroke goes.
OPTION_TOP = 591.47
OPTION_BOTTOM = 107.10
OPTION_LEFT = 50.78 - 11.53
OPTION_RIGHT = 551.28 - 11.53
OPTION_BAR_LEFT = 348.15 - 11.53
OPTION_CORNER_TOP_X = 190.92 - 11.53
OPTION_DIAGONAL_RUN = 195.81
OPTION_DIAGONAL_RISE = 391.60


def build_option(stem: float):
    thickness = OPTION_STROKE_RATIO * stem
    top = OPTION_TOP - thickness / 2
    bottom = OPTION_BOTTOM + thickness / 2
    slope = OPTION_DIAGONAL_RUN / OPTION_DIAGONAL_RISE
    # The diagonal keeps the angle it was drawn at; its corners follow the two
    # horizontal centre lines.
    corner_top = (OPTION_CORNER_TOP_X, top)
    corner_bottom = (
        OPTION_CORNER_TOP_X + (top - bottom) * slope,
        bottom,
    )
    pen = TTGlyphPen(None)
    _polygon(
        pen,
        mitred_polyline(
            [(OPTION_LEFT, top), corner_top, corner_bottom, (OPTION_RIGHT, bottom)],
            thickness,
        ),
    )
    _polygon(
        pen,
        mitred_polyline([(OPTION_BAR_LEFT, top), (OPTION_RIGHT, top)], thickness),
    )
    return pen.glyph()


# --- return ----------------------------------------------------------------
# Outer bounds, held fixed while the stroke thickens inward.
RETURN_TIP_X = 9.26
RETURN_RIGHT_X = 566.67
RETURN_SHAFT_Y = 330.83
RETURN_RISER_TOP = 480.14
RETURN_BARB_REACH = 179.17
# The barbs keep the 45.1-degree angle they were drawn at.
RETURN_BARB_RUN = 0.7010
RETURN_BARB_RISE = 0.7133


def build_return(stem: float):
    thickness = RETURN_STROKE_RATIO * stem
    half = thickness / 2
    # The tip is a mitre, so the vertex sits back from the fixed outer point by
    # the mitre length; the riser's centre sits in from the fixed right edge.
    vertex = (RETURN_TIP_X + half / RETURN_BARB_RISE, RETURN_SHAFT_Y)
    riser_x = RETURN_RIGHT_X - half
    # Each barb's square cap reaches past its centre line by half a stroke, so the
    # centre line stops short of the fixed outer top and bottom.
    reach = RETURN_BARB_REACH - half * RETURN_BARB_RUN
    run = reach / RETURN_BARB_RISE * RETURN_BARB_RUN
    upper = (vertex[0] + run, RETURN_SHAFT_Y + reach)
    lower = (vertex[0] + run, RETURN_SHAFT_Y - reach)

    pen = TTGlyphPen(None)
    _polygon(pen, mitred_polyline([upper, vertex, lower], thickness))
    # Shaft and riser as one mitred L, starting inside the chevron's ink so the
    # two contours union cleanly under the nonzero winding rule.
    _polygon(
        pen,
        mitred_polyline(
            [vertex, (riser_x, RETURN_SHAFT_Y), (riser_x, RETURN_RISER_TOP)],
            thickness,
        ),
    )
    return pen.glyph()


# --- command ---------------------------------------------------------------
# The command symbol is four interlocking loops, so it is carried as the supplied
# outline and offset along its own normals for other weights. That is safe here
# because every join in it is a smooth curve rather than a corner.
COMMAND_PATH = (
    "M18.360 86.400C12.760 86.400 8.280 84.760 4.920 81.480"
    "C1.640 78.200 0.000 73.800 0.000 68.280C0.000 62.440 1.720 57.920 5.160 54.720"
    "C8.680 51.440 13.840 49.800 20.640 49.800L27.720 49.800L27.720 36.600"
    "L20.640 36.600C13.840 36.600 8.680 35.000 5.160 31.800"
    "C1.720 28.520 0.000 23.960 0.000 18.120C0.000 12.600 1.640 8.200 4.920 4.920"
    "C8.280 1.640 12.760 0.000 18.360 0.000C22.840 0.000 26.360 0.840 28.920 2.520"
    "C31.560 4.200 33.400 6.440 34.440 9.240C35.560 12.040 36.120 15.120 36.120 18.480"
    "L36.120 28.440L49.320 28.440L49.320 18.480"
    "C49.320 15.120 49.840 12.040 50.880 9.240C52.000 6.440 53.840 4.200 56.400 2.520"
    "C59.040 0.840 62.600 0.000 67.080 0.000C72.680 0.000 77.120 1.640 80.400 4.920"
    "C83.760 8.200 85.440 12.600 85.440 18.120C85.440 23.960 83.720 28.520 80.280 31.800"
    "C76.840 35.000 71.680 36.600 64.800 36.600L57.720 36.600L57.720 49.800"
    "L64.800 49.800C71.680 49.800 76.840 51.440 80.280 54.720"
    "C83.720 57.920 85.440 62.440 85.440 68.280C85.440 73.800 83.760 78.200 80.400 81.480"
    "C77.120 84.760 72.680 86.400 67.080 86.400C62.600 86.400 59.040 85.560 56.400 83.880"
    "C53.840 82.200 52.000 79.960 50.880 77.160C49.840 74.360 49.320 71.280 49.320 67.920"
    "L49.320 57.960L36.120 57.960L36.120 67.920"
    "C36.120 71.280 35.560 74.360 34.440 77.160C33.400 79.960 31.560 82.200 28.920 83.880"
    "C26.360 85.560 22.840 86.400 18.360 86.400Z"
    "M57.720 18.240L57.720 28.440L64.800 28.440"
    "C69.040 28.440 72.120 27.600 74.040 25.920C75.960 24.160 76.920 21.560 76.920 18.120"
    "C76.920 14.600 75.960 12.080 74.040 10.560C72.200 9.040 69.880 8.280 67.080 8.280"
    "C63.960 8.280 61.600 9.200 60.000 11.040C58.480 12.800 57.720 15.200 57.720 18.240Z"
    "M20.640 28.440L27.720 28.440L27.720 18.240"
    "C27.720 15.200 26.920 12.800 25.320 11.040C23.800 9.200 21.480 8.280 18.360 8.280"
    "C15.560 8.280 13.200 9.040 11.280 10.560C9.440 12.080 8.520 14.600 8.520 18.120"
    "C8.520 21.560 9.480 24.160 11.400 25.920C13.320 27.600 16.400 28.440 20.640 28.440Z"
    "M36.120 49.800L49.320 49.800L49.320 36.600L36.120 36.600L36.120 49.800Z"
    "M18.360 78.120C21.480 78.120 23.800 77.240 25.320 75.480"
    "C26.920 73.640 27.720 71.200 27.720 68.160L27.720 57.960L20.640 57.960"
    "C16.400 57.960 13.320 58.840 11.400 60.600C9.480 62.280 8.520 64.840 8.520 68.280"
    "C8.520 71.800 9.440 74.320 11.280 75.840C13.200 77.360 15.560 78.120 18.360 78.120Z"
    "M57.720 68.160C57.720 71.200 58.480 73.640 60.000 75.480"
    "C61.600 77.240 63.960 78.120 67.080 78.120C69.880 78.120 72.200 77.360 74.040 75.840"
    "C75.960 74.320 76.920 71.800 76.920 68.280C76.920 64.840 75.960 62.280 74.040 60.600"
    "C72.120 58.840 69.040 57.960 64.800 57.960L57.720 57.960L57.720 68.160Z"
)
COMMAND_DRAWING_ORIGIN = (6.12, 35.6)
COMMAND_INK_WIDTH = 85.44 * UNITS_PER_PIXEL


def command_design_glyph():
    """The supplied drawing, in font units, centred in the cell."""
    _, origin_y = COMMAND_DRAWING_ORIGIN
    # The path's own x starts at 0, so the drawing origin only fixes the vertical
    # position; the horizontal position comes from centring in the cell.
    transform = Transform(
        UNITS_PER_PIXEL,
        0,
        0,
        -UNITS_PER_PIXEL,
        (ADVANCE - COMMAND_INK_WIDTH) / 2,
        (DRAWING_BASELINE - origin_y) * UNITS_PER_PIXEL,
    )
    pen = TTGlyphPen(None)
    quadratic = Cu2QuPen(pen, max_err=0.4, reverse_direction=False)
    parse_path(COMMAND_PATH, TransformPen(quadratic, transform))
    return pen.glyph()


COMMAND_INK_HEIGHT = 86.4 * UNITS_PER_PIXEL
COMMAND_CENTRE_Y = (705.0 + -15.0) / 2
# Contour 0 is the outer boundary; the rest are the loop counters and the central
# square, which have to close toward the ink as the stroke grows.
COMMAND_CONTOUR_SIGNS = (1, -1, -1, -1, -1, -1)


def _flatten(glyph, steps=12):
    from fontTools.pens.recordingPen import RecordingPen

    class _Pen:
        def __init__(self):
            self.contours = []
            self._current = None

        def moveTo(self, pt):
            self._current = [pt]

        def lineTo(self, pt):
            self._current.append(pt)

        def qCurveTo(self, *points):
            on_curve = points[-1]
            controls = points[:-1]
            previous = self._current[-1]
            implied = []
            for index, control in enumerate(controls):
                following = (
                    controls[index + 1]
                    if index + 1 < len(controls)
                    else on_curve
                )
                end = (
                    ((control[0] + following[0]) / 2, (control[1] + following[1]) / 2)
                    if index + 1 < len(controls)
                    else on_curve
                )
                implied.append((previous, control, end))
                previous = end
            for start, control, end in implied:
                for step in range(1, steps + 1):
                    t = step / steps
                    u = 1 - t
                    self._current.append(
                        (
                            u * u * start[0] + 2 * u * t * control[0] + t * t * end[0],
                            u * u * start[1] + 2 * u * t * control[1] + t * t * end[1],
                        )
                    )

        def curveTo(self, *points):
            self.lineTo(points[-1])

        def closePath(self):
            if self._current:
                self.contours.append(self._current)
                self._current = None

        endPath = closePath

        def addComponent(self, *args, **kwargs):
            pass

    recording = RecordingPen()
    glyph.draw(recording, None)
    pen = _Pen()
    recording.replay(pen)
    pen.closePath()
    return pen.contours


def _ink_spans(contours, y):
    """Ink spans at height y under the nonzero winding rule."""
    crossings = []
    for contour in contours:
        count = len(contour)
        for index in range(count):
            x0, y0 = contour[index]
            x1, y1 = contour[(index + 1) % count]
            if y0 == y1:
                continue
            if min(y0, y1) <= y < max(y0, y1):
                t = (y - y0) / (y1 - y0)
                crossings.append((x0 + t * (x1 - x0), 1 if y1 > y0 else -1))
    crossings.sort()
    spans, winding, start = [], 0, None
    for x, direction in crossings:
        previous = winding
        winding += direction
        if previous == 0 and winding != 0:
            start = x
        elif previous != 0 and winding == 0:
            spans.append((start, x))
    return spans


def _command_at_offset(delta, offset_glyph_stable):
    """Offset the drawing, then scale it back to the size it was drawn at."""
    glyph = command_design_glyph()
    if delta:
        offset_glyph_stable(glyph, delta, (), COMMAND_CONTOUR_SIGNS)
    xs = [x for x, _ in glyph.coordinates]
    width = max(xs) - min(xs)
    factor = COMMAND_INK_WIDTH / width if width else 1.0
    centre_x = ADVANCE / 2
    glyph.coordinates = type(glyph.coordinates)(
        [
            (
                round(centre_x + (x - centre_x) * factor),
                round(COMMAND_CENTRE_Y + (y - COMMAND_CENTRE_Y) * factor),
            )
            for x, y in glyph.coordinates
        ]
    )
    return glyph


def _command_stroke(glyph):
    spans = _ink_spans(_flatten(glyph), COMMAND_CENTRE_Y)
    return spans[0][1] - spans[0][0] if spans else 0.0


def build_command(stem: float, offset_glyph_stable):
    """Offset the drawing to the target stroke, then hold its outer size.

    Offsetting alone would grow the symbol with weight, where a letter would hold
    its cap height, so the result is scaled back to the drawn width. The offset a
    given thickness needs is not linear across four interlocking loops, so it is
    solved against the measured stroke rather than computed.
    """
    target = COMMAND_STROKE_RATIO * stem
    low, high = -26.0, 70.0
    for _ in range(28):
        middle = (low + high) / 2
        if _command_stroke(_command_at_offset(middle, offset_glyph_stable)) < target:
            low = middle
        else:
            high = middle
    return _command_at_offset((low + high) / 2, offset_glyph_stable)


SYMBOL_BUILDERS = {
    "uni2325": build_option,
    "uni23CE": build_return,
}
