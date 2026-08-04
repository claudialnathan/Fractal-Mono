"""Read the ExtraBold shape references drawn in Paper into font coordinates.

These are shape specifications, not weight specifications. They were made by
expanding the Regular outline and adjusting the result by hand, so their stroke
thickness is a by-product of that expansion and carries no intent; what they
record is how each letter's design should look once it is heavy — apertures still
open, `M`'s middle V still deep, terminals still cut the way they are at Regular.

Two frames, each with its own drawing scale. A flat-topped glyph in each frame
fixes the cap height; the rounds in the same frame overshoot it, and that
overshoot is preserved rather than normalised away.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform
from fontTools.svgLib.path import parse_path
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

import fitting
import offset

CAP_HEIGHT = 680
ADVANCE = 579
DEFAULT_OPSZ = 14
TEXT_OPSZ = 9
DISPLAY_OPSZ = 72
EXTRABOLD_STEM = 150.0
DATA = Path(__file__).with_name("drawings_extrabold.json")

# The flat-topped glyph in each frame, whose drawn height is the cap height.
FRAME_CAP = {
    frozenset({"S", "M"}): ("M", 377.96),
    frozenset({"G", "N", "C"}): ("N", 327.2),
}

# The drawings are silhouette specifications. Their stroke widths only record
# how much ink the expand-outline operation happened to add in Paper. They are
# measured here so the targets can be rebuilt at Fractal's intended weight.
# S did not retain a stroke attribute in the Paper export; its median straight
# section measures 119.5 units after conversion to the 1000 UPM design.
DRAWN_STROKES = {
    "S": 119.5,
    "M": 124.58810456132923,
    "G": 122.41039119804401,
    "N": 124.7317848410758,
    "C": 114.73960880195598,
}
ROUND_GLYPHS = frozenset({"C", "G", "S"})
ROUND_STROKE_RATIO = 1.03

# The curve silhouettes have substantially more source points than Fractal's
# compatible masters. The thin-plate fit is useful for the bowls, but it cannot
# infer which straight sections are typographic hard zones. These point roles
# are stable in every master and keep those sections structural instead of
# letting a spatial fit rotate them through the counter.
CURVE_HORIZONTAL_PAIRS = {
    "C": ((13, 14), (27, 28)),
    "G": ((13, 14), (27, 32), (28, 29), (30, 31)),
}
S_TERMINAL_PAIRS = ((0, 1), (31, 32))
S_TERMINAL_CONTROLS = ((2, 1, 1), (33, 32, -1))
S_TERMINAL_CONTROL_RUN = 4
S_HARD_ZONE_POINTS = (24, 25, 26, 27, 28, 54, 55, 56, 57, 58)

# Current-compatible point roles for the two straight-sided drawings. Values
# pair an index in Fractal's established outline topology with the equivalent
# index in the normalized Paper target. Intermediate controls are placed along
# the adjoining target segment, retaining their original on/off-curve flags.
POLYGON_ANCHORS = {
    "M": (
        (0, 14),
        (1, 13),
        (2, 12),
        (6, 11),
        (10, 10),
        (11, 9),
        (12, 8),
        (13, 7),
        (17, 6),
        (18, 5),
        (19, 4),
        (20, 3),
        (23, 1),
        (24, 0),
    ),
    "N": (
        (0, 0),
        (1, 26),
        (2, 25),
        (3, 20),
        (8, 19),
        (9, 18),
        (10, 13),
        (11, 12),
        (12, 2),
        (17, 1),
    ),
}


def _frame_scale(name: str, data: dict) -> float:
    for names, (_, cap) in FRAME_CAP.items():
        if name in names:
            return CAP_HEIGHT / cap
    raise KeyError(f"No frame scale recorded for {name}")


def load() -> dict[str, dict]:
    """Return each drawing as recorded pen commands in font coordinates.

    Paper exports SVG with y increasing downward and the drawing's own top at
    zero, so the transform flips y and puts the baseline at zero. Degenerate
    cubic segments — Figma writes straight lines as curves whose controls sit on
    the endpoints — are collapsed to lines, because a curve with coincident
    control points carries no information and only adds points to interpolate.
    """
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for name, entry in raw["glyphs"].items():
        scale = _frame_scale(name, raw)
        width, height = entry["viewBox"]
        # y_font = (height - y_svg) * scale, then shift so the baseline is 0.
        # A round glyph overshoots below the baseline, so the shift comes from the
        # frame's flat glyph, not from this glyph's own bounding box.
        overshoot = (height - _flat_height(name)) / 2
        transform = Transform(scale, 0, 0, -scale, 0, (height - overshoot) * scale)

        recording = RecordingPen()
        parse_path(entry["path"], TransformPen(recording, transform))
        commands = _collapse_degenerate(recording.value)
        out[name] = {
            "commands": commands,
            "drawn_stroke": (entry["drawn_stroke"] or 0) * scale,
            "scale": scale,
        }
    return out


def _flat_height(name: str) -> float:
    for names, (_, cap) in FRAME_CAP.items():
        if name in names:
            return cap
    raise KeyError(name)


def _collapse_degenerate(commands, tolerance: float = 0.6):
    """Turn Figma's zero-curvature cubics back into the lines they represent."""
    out = []
    current = None
    for operator, args in commands:
        if operator == "curveTo" and current is not None:
            c1, c2, end = args
            if (_near(c1, current, tolerance) or _near(c1, end, tolerance)) and (
                _near(c2, current, tolerance) or _near(c2, end, tolerance)
            ):
                out.append(("lineTo", (end,)))
                current = end
                continue
        out.append((operator, args))
        if args:
            current = args[-1]
    return out


def _near(a, b, tolerance):
    return abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance


def polygons(commands, steps: int = 24):
    """Flatten to closed polylines for measurement and drawing."""
    polys, current, start = [], [], (0.0, 0.0)
    for operator, args in commands:
        if operator == "moveTo":
            if len(current) > 2:
                polys.append(current)
            start = args[0]
            current = [start]
        elif operator == "lineTo":
            current.append(args[0])
        elif operator == "curveTo":
            p0 = current[-1]
            c1, c2, end = args
            for step in range(1, steps + 1):
                t = step / steps
                u = 1 - t
                current.append(
                    (
                        u**3 * p0[0] + 3 * u * u * t * c1[0]
                        + 3 * u * t * t * c2[0] + t**3 * end[0],
                        u**3 * p0[1] + 3 * u * u * t * c1[1]
                        + 3 * u * t * t * c2[1] + t**3 * end[1],
                    )
                )
        elif operator == "closePath":
            if len(current) > 2:
                polys.append(current)
            current = []
    if len(current) > 2:
        polys.append(current)
    return polys


def _optical_value(opsz: float, text: float, default: float, display: float) -> float:
    if opsz == default:
        return default
    if opsz < default:
        factor = (opsz - default) / (default - TEXT_OPSZ)
        return default + (default - text) * factor
    factor = (opsz - default) / (DISPLAY_OPSZ - default)
    return default + (display - default) * factor


def _normalized_target(name: str, reference_font, opsz: float):
    """Build the designer's ExtraBold silhouette at Fractal's optical weight.

    This is a generator-time operation. The resulting outline is converted into
    compatible point deltas before it reaches the variable font; no path offset
    runs in a renderer or between variable-font locations.
    """
    entry = load()[name]
    recording = RecordingPen()
    recording.value = entry["commands"]
    pen = TTGlyphPen(None)
    recording.replay(Cu2QuPen(pen, 0.4, reverse_direction=False))
    glyph = pen.glyph()

    target_stroke = EXTRABOLD_STEM * (
        ROUND_STROKE_RATIO if name in ROUND_GLYPHS else 1.0
    )
    glyph = offset.offset_glyph(
        glyph,
        reference_font["glyf"],
        (target_stroke - DRAWN_STROKES[name]) / 2,
    )
    glyph.recalcBounds(reference_font["glyf"])

    center_shift = ADVANCE / 2 - (glyph.xMin + glyph.xMax) / 2
    optical_x = _optical_value(opsz, 1.005, 1.0, 0.975)
    glyph.coordinates = GlyphCoordinates(
        [
            (
                ADVANCE / 2
                + (x + center_shift - ADVANCE / 2) * optical_x,
                y,
            )
            for x, y in glyph.coordinates
        ]
    )
    glyph.recalcBounds(reference_font["glyf"])

    # Claudia explicitly marked the drawings' widths as approximate. C/G/S take
    # the established round sidebearing from the already-fitted ExtraBold master;
    # refit moves their outer ink bands and leaves the normalized curve stroke
    # untouched.
    if name in ROUND_GLYPHS:
        reference = reference_font["glyf"][name]
        sidebearing = (
            reference.xMin + ADVANCE - reference.xMax
        ) / 2
        fitting.refit(glyph, reference_font["glyf"], sidebearing)
        glyph.recalcBounds(reference_font["glyf"])
    return glyph


class _Flatten(BasePen):
    def __init__(self, steps: int = 12):
        super().__init__(None)
        self.steps = steps
        self.contours: list[list[tuple[float, float]]] = []
        self.current: list[tuple[float, float]] | None = None

    def _moveTo(self, point):
        self.current = [point]

    def _lineTo(self, point):
        assert self.current is not None
        self.current.append(point)

    def _curveToOne(self, first, second, end):
        assert self.current is not None
        start = self.current[-1]
        for index in range(1, self.steps + 1):
            t = index / self.steps
            u = 1 - t
            self.current.append(
                (
                    u**3 * start[0]
                    + 3 * u * u * t * first[0]
                    + 3 * u * t * t * second[0]
                    + t**3 * end[0],
                    u**3 * start[1]
                    + 3 * u * u * t * first[1]
                    + 3 * u * t * t * second[1]
                    + t**3 * end[1],
                )
            )

    def _qCurveToOne(self, control, end):
        assert self.current is not None
        start = self.current[-1]
        for index in range(1, self.steps + 1):
            t = index / self.steps
            u = 1 - t
            self.current.append(
                (
                    u * u * start[0] + 2 * u * t * control[0] + t * t * end[0],
                    u * u * start[1] + 2 * u * t * control[1] + t * t * end[1],
                )
            )

    def _closePath(self):
        if self.current:
            self.contours.append(self.current)
            self.current = None

    _endPath = _closePath


def _flattened(glyph, glyf) -> list[tuple[float, float]]:
    pen = _Flatten()
    glyph.draw(pen, glyf)
    pen._closePath()
    if len(pen.contours) != 1:
        raise ValueError("Drawing corrections require one-contour glyphs")
    return pen.contours[0]


def _resample(points, count: int = 96) -> np.ndarray:
    polygon = np.asarray(points, dtype=float)
    polygon = np.vstack((polygon, polygon[0]))
    lengths = np.linalg.norm(np.diff(polygon, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    positions = np.linspace(0, cumulative[-1], count, endpoint=False)
    result = []
    for position in positions:
        segment = min(
            np.searchsorted(cumulative, position, side="right") - 1,
            len(lengths) - 1,
        )
        fraction = (
            (position - cumulative[segment]) / lengths[segment]
            if lengths[segment] > 1e-9
            else 0
        )
        result.append(
            polygon[segment]
            + fraction * (polygon[segment + 1] - polygon[segment])
        )
    return np.asarray(result)


def _signed_area(points: np.ndarray) -> float:
    following = np.roll(points, -1, axis=0)
    return float(
        np.sum(points[:, 0] * following[:, 1] - following[:, 0] * points[:, 1])
        / 2
    )


def _align_samples(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    if _signed_area(source) * _signed_area(target) < 0:
        target = target[::-1]
    return min(
        (np.roll(target, shift, axis=0) for shift in range(len(target))),
        key=lambda candidate: float(np.mean(np.sum((source - candidate) ** 2, axis=1))),
    )


def _kernel(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    difference = left[:, None, :] - right[None, :, :]
    radius_squared = np.sum(difference * difference, axis=2)
    result = np.zeros_like(radius_squared)
    nonzero = radius_squared > 0
    result[nonzero] = radius_squared[nonzero] * np.log(
        np.sqrt(radius_squared[nonzero])
    )
    return result


def _curve_target(reference, target, glyf) -> GlyphCoordinates:
    """Fit the curved parts of C/G/S to the drawn endpoint silhouette."""
    source_samples = _resample(_flattened(reference, glyf))
    target_samples = _align_samples(
        source_samples,
        _resample(_flattened(target, glyf)),
    )
    controls = source_samples[::2]
    destinations = target_samples[::2]
    count = len(controls)
    affine = np.column_stack((np.ones(count), controls))
    system = np.block(
        [
            [_kernel(controls, controls) + np.eye(count) * 1e-5, affine],
            [affine.T, np.zeros((3, 3))],
        ]
    )
    coefficients = np.linalg.solve(
        system,
        np.vstack((destinations - controls, np.zeros((3, 2)))),
    )
    coordinates = np.asarray(reference.coordinates, dtype=float)
    basis = np.column_stack(
        (
            _kernel(coordinates, controls),
            np.ones(len(coordinates)),
            coordinates,
        )
    )
    return GlyphCoordinates(
        [
            (round(x), round(y))
            for x, y in coordinates + basis @ coefficients
        ]
    )


def _constrain_curve_target(
    name: str,
    reference,
    endpoint: GlyphCoordinates,
) -> GlyphCoordinates:
    """Restore semantic hard zones after fitting the compatible curve points.

    A global spatial fit sees only proximity. It can therefore rotate G's bar
    and C's terminals, or pull one S overshoot control away from its zone, even
    though the sampled silhouette itself is clean. Keeping these established
    point roles explicit gives the endpoint a valid typographic construction
    while retaining the fitted bowl and spine everywhere else.
    """
    constrained = GlyphCoordinates(endpoint)

    for first, second in CURVE_HORIZONTAL_PAIRS.get(name, ()):
        y = round((constrained[first][1] + constrained[second][1]) / 2)
        constrained[first] = (constrained[first][0], y)
        constrained[second] = (constrained[second][0], y)

    if name == "S":
        for first, second in S_TERMINAL_PAIRS:
            y = round(
                (reference.coordinates[first][1] + reference.coordinates[second][1])
                / 2
            )
            constrained[first] = (constrained[first][0], y)
            constrained[second] = (constrained[second][0], y)
        for control, terminal, direction in S_TERMINAL_CONTROLS:
            control_x = constrained[control][0]
            minimum_x = (
                constrained[terminal][0]
                + direction * S_TERMINAL_CONTROL_RUN
            )
            if direction > 0:
                control_x = max(control_x, minimum_x)
            else:
                control_x = min(control_x, minimum_x)
            constrained[control] = (
                control_x,
                constrained[terminal][1],
            )
        for index in S_HARD_ZONE_POINTS:
            constrained[index] = (
                constrained[index][0],
                reference.coordinates[index][1],
            )

    return constrained


def _polygon_target(reference, target, name: str) -> GlyphCoordinates:
    """Map the established M/N point roles onto Claudia's straight-sided target."""
    coordinates = list(reference.coordinates)
    anchors = POLYGON_ANCHORS[name]
    expected = max(target_index for _, target_index in anchors) + 1
    if len(target.coordinates) < expected:
        raise ValueError(
            f"{name} target changed topology: {len(target.coordinates)} < {expected}"
        )
    for (source_a, target_a), (source_b, target_b) in zip(anchors, anchors[1:]):
        start = target.coordinates[target_a]
        end = target.coordinates[target_b]
        for index in range(source_a, source_b + 1):
            fraction = (
                (index - source_a) / (source_b - source_a)
                if source_b > source_a
                else 0
            )
            coordinates[index] = (
                round(start[0] + (end[0] - start[0]) * fraction),
                round(start[1] + (end[1] - start[1]) * fraction),
            )
    return GlyphCoordinates(coordinates)


def correction_deltas(reference_font, opsz: float) -> dict[str, GlyphCoordinates]:
    """Return compatible ExtraBold corrections from the pre-correction master."""
    glyf = reference_font["glyf"]
    corrections: dict[str, GlyphCoordinates] = {}
    for name in sorted(DRAWN_STROKES):
        reference = glyf[name]
        target = _normalized_target(name, reference_font, opsz)
        if name in POLYGON_ANCHORS:
            endpoint = _polygon_target(reference, target, name)
        else:
            endpoint = _curve_target(reference, target, glyf)
            endpoint = _constrain_curve_target(name, reference, endpoint)
        if len(endpoint) != len(reference.coordinates):
            raise ValueError(f"{name} correction changed compatible point count")
        corrections[name] = GlyphCoordinates(
            [
                (target_x - source_x, target_y - source_y)
                for (source_x, source_y), (target_x, target_y) in zip(
                    reference.coordinates,
                    endpoint,
                )
            ]
        )
    return corrections


def apply_corrections(font, weight: float, corrections) -> set[str]:
    """Blend endpoint drawing corrections above the approved 500 master."""
    if weight <= 500:
        return set()
    factor = min(1.0, (weight - 500) / 300)
    glyf = font["glyf"]
    applied = set()
    for name, deltas in corrections.items():
        glyph = glyf[name]
        if len(glyph.coordinates) != len(deltas):
            raise ValueError(f"{name} master lost compatible topology")
        glyph.coordinates = GlyphCoordinates(
            [
                (
                    round(x + delta_x * factor),
                    round(y + delta_y * factor),
                )
                for (x, y), (delta_x, delta_y) in zip(
                    glyph.coordinates,
                    deltas,
                )
            ]
        )
        if name == "S":
            # Apply the terminal-control relationship to every corrected master,
            # not only the ExtraBold endpoint. This prevents the intermediate
            # 620 master from reintroducing a cusp before interpolation reaches
            # the final endpoint.
            for control, terminal, direction in S_TERMINAL_CONTROLS:
                control_x = glyph.coordinates[control][0]
                minimum_x = (
                    glyph.coordinates[terminal][0]
                    + direction * S_TERMINAL_CONTROL_RUN
                )
                if direction > 0:
                    control_x = max(control_x, minimum_x)
                else:
                    control_x = min(control_x, minimum_x)
                glyph.coordinates[control] = (
                    control_x,
                    glyph.coordinates[terminal][1],
                )
        glyph.recalcBounds(glyf)
        font["hmtx"].metrics[name] = (ADVANCE, glyph.xMin)
        applied.add(name)
    return applied


if __name__ == "__main__":
    for name, entry in sorted(load().items()):
        polys = polygons(entry["commands"])
        xs = [p[0] for poly in polys for p in poly]
        ys = [p[1] for poly in polys for p in poly]
        ops = [operator for operator, _ in entry["commands"]]
        print(
            f"{name}: x {min(xs):7.1f}..{max(xs):7.1f}  y {min(ys):7.1f}..{max(ys):7.1f}"
            f"  width {max(xs)-min(xs):6.1f}  drawn stroke {entry['drawn_stroke']:5.1f}"
            f"  {len(ops)} ops, {ops.count('curveTo')} curves"
        )
