"""Add ink to an outline without changing the shape it is an outline of.

This is what a weight axis should do: keep the skeleton, the proportions, the
apertures and the angles a terminal is cut at, and change only how much ink hangs
off them. Fractal's heavy masters were instead computed as "the approved Regular
drawing, moved by however the archived source moved between its own Regular and
its own ExtraBold" — so the further from Regular you went, the more the shape
became the archive's and the less it stayed the design. That is why `C`, `G` and
`M` read as a different typeface at the heavy end.

The operation is the one a designer does by hand in a vector editor: stroke the
outline and union the result back onto the shape. Skia does the stroking and the
boolean, which matters because a naive per-segment offset folds into a loop
wherever a curve turns tighter than the offset distance — that produced spikes at
`B`'s waist, `R`'s leg junction and `W`'s vertices, and resolving those folds
correctly is a boolean problem, not a geometry-by-hand problem.
"""

from __future__ import annotations

import pathops
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

# A mitre join keeps a corner a corner. The limit stops an acute vertex growing an
# arbitrarily long spike; beyond it Skia bevels, which is what a punchcutter does.
MITRE_LIMIT = 4.0
CURVE_TOLERANCE = 0.35  # font units allowed when refitting cubics to quadratics


def _to_path(glyph, glyf) -> pathops.Path:
    path = pathops.Path()
    glyph.draw(path.getPen(), glyf)
    return path


def _boundary_band(path: pathops.Path, half_width: float) -> pathops.Path:
    """A band of ink `half_width` either side of the outline's boundary."""
    band = pathops.Path(path)
    band.stroke(
        half_width * 2,        # Skia strokes centred, so half lands either side
        pathops.LineCap.BUTT_CAP,
        pathops.LineJoin.MITER_JOIN,
        MITRE_LIMIT,
    )
    return band


def _expanded(path: pathops.Path, distance: float) -> pathops.Path:
    """Add `distance` of ink on every side, or remove it when negative.

    Adding is the shape unioned with a band straddling its boundary; removing is
    the same band subtracted. Erosion is not optional — the light half of the axis
    needs its masters thinned out of Regular exactly as the heavy half needs them
    thickened, and a stroke width cannot be negative, so the sign has to change the
    operation rather than the number.
    """
    band = _boundary_band(path, abs(distance))
    operation = pathops.PathOp.UNION if distance > 0 else pathops.PathOp.DIFFERENCE
    # `pathops.union(contours, pen)` de-overlaps the contours of one glyph; combining
    # two separate paths is `op`. Using the former returns the hollow stroke ring.
    result = pathops.op(path, band, operation)
    result.simplify(fix_winding=True, keep_starting_points=False)
    return result


def restore_extremes(coordinates: GlyphCoordinates, low: float, high: float) -> GlyphCoordinates:
    """Put the vertical extremes back where they were before ink was added.

    Growing an outline grows it in every direction, but cap height, baseline,
    x-height and the overshoot on rounds are family constants a weight change must
    not move. Mapping the new vertical extent onto the old one is affine, so it
    keeps overshoot in proportion and, unlike clamping, does not press the top of a
    curve into a flat. It also leaves horizontals thinner than verticals by the
    same ratio, which is the correction they need anyway.
    """
    ys = [y for _, y in coordinates]
    if not ys:
        return coordinates
    new_low, new_high = min(ys), max(ys)
    span = new_high - new_low
    if span < 1e-6:
        return coordinates
    scale = (high - low) / span
    return GlyphCoordinates(
        [(x, low + (y - new_low) * scale) for x, y in coordinates]
    )


def offset_glyph(glyph, glyf, distance: float, keep_height: bool = True):
    """Return a new glyph with `distance` units of ink added on every side."""
    if glyph.numberOfContours == 0 or distance == 0:
        return glyph
    coordinates, _, _ = glyph.getCoordinates(glyf)
    original_ys = [y for _, y in coordinates] if len(coordinates) else []

    grown = _expanded(_to_path(glyph, glyf), distance)

    # Skia works in cubics; the glyf table wants quadratics.
    recording = RecordingPen()
    grown.draw(recording)
    pen = TTGlyphPen(None)
    from fontTools.pens.cu2quPen import Cu2QuPen

    recording.replay(Cu2QuPen(pen, CURVE_TOLERANCE, reverse_direction=False))
    result = pen.glyph()

    if keep_height and original_ys and len(result.coordinates):
        result.coordinates = restore_extremes(
            result.coordinates, min(original_ys), max(original_ys)
        )
        result.recalcBounds(glyf)
    return result
