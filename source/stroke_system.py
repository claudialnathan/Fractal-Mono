"""Enforce the family stroke system on the straight-stroke letters.

The weight masters for these glyphs were produced by geometric transfer from an
earlier release. That transfer moves points, so it reproduces vertical stems
correctly but cannot infer how thick a diagonal should be: measured against the
stem, K's diagonals ran from 1.40x at Thin to 0.63x at ExtraBold, and W's and
M's behaved the same way. No reference family leaves that band, and every one of
them converges each stroke toward the stem at the thin extreme, where there is
no room for optical differentiation.

This pass restates each declared stroke from the approved Regular direction and
the family's target thickness, then rebuilds every affected vertex as a true
intersection of the adjoining edges. Applied at Regular with the Regular
thickness it reproduces the approved outline exactly, which is what
`verify_identity` asserts.

A flat that cuts a vertex is clamped to the mitre: where the two stroke edges
would meet past the cut, the cut moves to the meeting point instead of crossing
it. That crossing is what made the lowercase w self-intersect from wght 300 up.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

MIN_FLAT_WIDTH = 2.0


@dataclass(frozen=True)
class Diagonal:
    """Two opposite edges of one straight stroke, named by on-curve indices."""

    first: tuple[int, int]
    second: tuple[int, int]


@dataclass(frozen=True)
class VerticalStem:
    left: tuple[int, ...]
    right: tuple[int, ...]


@dataclass(frozen=True)
class Junction:
    """A curve handing over between two straight stroke edges.

    Covers both a pointed apex, as in W and M, and a stem-to-diagonal
    transition. The whole assembly belongs at the two edges' meeting point: left
    where it is while the strokes thicken, the edges run past their own joins and
    the outline crosses itself.

    `min_y` holds the meeting point off a baseline it must not dip below.
    """

    first: tuple[int, int]
    second: tuple[int, int]
    min_y: float | None = None


@dataclass(frozen=True)
class StrokePlan:
    diagonals: tuple[Diagonal, ...] = ()
    stems: tuple[VerticalStem, ...] = ()
    junctions: tuple[Junction, ...] = ()


# Point indices are stable because every master shares one compatible topology.
STROKE_PLANS: dict[str, StrokePlan] = {
    "K": StrokePlan(
        diagonals=(Diagonal((6, 7), (8, 9)), Diagonal((9, 10), (11, 12))),
        stems=(VerticalStem(left=(0, 1), right=(2, 3, 13, 14)),),
    ),
    "M": StrokePlan(
        diagonals=(Diagonal((2, 3), (19, 20)), Diagonal((9, 10), (17, 18))),
        stems=(
            VerticalStem(left=(0, 1), right=(23, 24)),
            VerticalStem(left=(13, 14), right=(11, 12)),
        ),
        junctions=(
            Junction((2, 3), (9, 10)),
            Junction((13, 14), (17, 18)),
            Junction((19, 20), (23, 24)),
        ),
    ),
    "W": StrokePlan(
        diagonals=(
            Diagonal((0, 1), (2, 3)),
            Diagonal((9, 10), (29, 30)),
            Diagonal((11, 12), (22, 23)),
            Diagonal((18, 19), (20, 21)),
        ),
        junctions=(
            Junction((2, 3), (9, 10), min_y=0),
            Junction((11, 12), (18, 19), min_y=0),
            Junction((22, 23), (29, 30)),
        ),
    ),
    # Six arms, each bounded by the edges either side of its flat tip. The
    # transferred masters had the arms running backwards - 76 units at Thin down
    # to 64 at ExtraBold - so the asterisk gained 6% of ink across an axis where
    # everything else gained 200%.
    "asterisk": StrokePlan(
        diagonals=(
            Diagonal((17, 0), (1, 2)),
            Diagonal((2, 3), (4, 5)),
            Diagonal((5, 6), (7, 8)),
            Diagonal((8, 9), (10, 11)),
            Diagonal((11, 12), (13, 14)),
            Diagonal((14, 15), (16, 17)),
        ),
    ),
    # k and w are drawn from the compact construction diagrams, so their point
    # order is the diagram's, not the signature masters'.
    "k": StrokePlan(
        diagonals=(Diagonal((5, 6), (7, 4)), Diagonal((10, 11), (8, 9))),
        stems=(VerticalStem(left=(0, 1), right=(2, 3)),),
    ),
    "w": StrokePlan(
        diagonals=(
            Diagonal((0, 1), (2, 3)),
            Diagonal((4, 5), (14, 15)),
            Diagonal((6, 7), (12, 13)),
            Diagonal((8, 9), (10, 11)),
        ),
    ),
}

# No audited reference family draws a diagonal heavier than its stem at any
# weight, and one that is reads as an error rather than as compensation.
MAX_DIAGONAL_RATIO = 1.0


def diagonal_ratio(regular_ratio: float, design_weight: float) -> float:
    """Target diagonal thickness as a fraction of the stem.

    The approved Regular proportion is preserved. Toward Thin the stroke
    converges most of the way to the stem, matching every audited reference;
    toward ExtraBold it takes a small uniform relief where density grows.
    """
    if design_weight <= 400:
        ratio = regular_ratio + (1 - regular_ratio) * 0.55 * (400 - design_weight) / 300
    else:
        ratio = regular_ratio - 0.05 * (design_weight - 400) / 400
    return min(MAX_DIAGONAL_RATIO, ratio)


def _unit(vector: tuple[float, float]) -> tuple[float, float]:
    length = math.hypot(*vector)
    if not length:
        raise ValueError("Zero-length stroke edge")
    return vector[0] / length, vector[1] / length


def _line(start, end) -> tuple[float, float, float]:
    """a*x + b*y = c with (a, b) a unit normal."""
    direction = _unit((end[0] - start[0], end[1] - start[1]))
    a, b = -direction[1], direction[0]
    return a, b, a * start[0] + b * start[1]


def _offset_line(line, distance: float):
    a, b, c = line
    return a, b, c + distance


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


def _project(line, point):
    a, b, c = line
    distance = a * point[0] + b * point[1] - c
    return point[0] - a * distance, point[1] - b * distance


# Below this sine of the angle between two edges the join is a smooth
# continuation rather than a corner - a straight diagonal flowing into an apex
# curve - and their intersection is meaningless.
PARALLEL_SINE = 0.20


def _resolve(first, second, original, first_is_new: bool, second_is_new: bool):
    """Where two edges meet: a corner intersection, or a slide along the stroke."""
    determinant = first[0] * second[1] - second[0] * first[1]
    if abs(determinant) >= PARALLEL_SINE:
        return _intersect(first, second)
    return _project(first if first_is_new else second, original)


def _contour_ranges(glyph):
    starts = [0, *(endpoint + 1 for endpoint in glyph.endPtsOfContours[:-1])]
    return [range(s, e + 1) for s, e in zip(starts, glyph.endPtsOfContours)]


def _on_curve_cycle(glyph, contour: range) -> list[int]:
    return [index for index in contour if glyph.flags[index] & 1]


def _edge_key(plan_edge: tuple[int, int]) -> tuple[int, int]:
    return plan_edge


def _stroke_geometry(coordinates, edge: tuple[int, int]):
    start, end = coordinates[edge[0]], coordinates[edge[1]]
    return _line(start, end)


def measure_diagonal(coordinates, diagonal: Diagonal) -> tuple[float, tuple[float, float]]:
    """Perpendicular thickness and the shared unit direction of a stroke."""
    first_dir = _unit(
        (
            coordinates[diagonal.first[1]][0] - coordinates[diagonal.first[0]][0],
            coordinates[diagonal.first[1]][1] - coordinates[diagonal.first[0]][1],
        )
    )
    second_dir = _unit(
        (
            coordinates[diagonal.second[1]][0] - coordinates[diagonal.second[0]][0],
            coordinates[diagonal.second[1]][1] - coordinates[diagonal.second[0]][1],
        )
    )
    if first_dir[0] * second_dir[0] + first_dir[1] * second_dir[1] < 0:
        second_dir = (-second_dir[0], -second_dir[1])
    shared = _unit((first_dir[0] + second_dir[0], first_dir[1] + second_dir[1]))
    normal = (-shared[1], shared[0])
    first_offset = (
        coordinates[diagonal.first[0]][0] * normal[0]
        + coordinates[diagonal.first[0]][1] * normal[1]
    )
    second_offset = (
        coordinates[diagonal.second[0]][0] * normal[0]
        + coordinates[diagonal.second[0]][1] * normal[1]
    )
    return abs(second_offset - first_offset), shared


def reference_stem(reference, name: str, fallback: float = 80.0) -> float:
    """The stem the approved Regular master actually draws for this glyph."""
    plan = STROKE_PLANS[name]
    if not plan.stems:
        return fallback
    coordinates = [tuple(point) for point in reference.coordinates]
    return measure_stem(coordinates, plan.stems[0])


def measure_stem(coordinates, stem: VerticalStem) -> float:
    left = sum(coordinates[index][0] for index in stem.left) / len(stem.left)
    right = sum(coordinates[index][0] for index in stem.right) / len(stem.right)
    return right - left


def apply(glyph, name: str, *, stem: float, reference, reference_stem: float):
    """Restate `name`'s declared strokes at the family target thickness.

    `reference` is the approved Regular master; its stroke directions and its
    thickness-to-stem proportions are the design authority.
    """
    plan = STROKE_PLANS[name]
    coordinates = [tuple(point) for point in glyph.coordinates]
    reference_coordinates = [tuple(point) for point in reference.coordinates]
    design_weight = _design_weight_for_stem(stem)

    new_lines: dict[tuple[int, int], tuple[float, float, float]] = {}
    shift_x: dict[int, float] = {}

    for vertical in plan.stems:
        current = measure_stem(coordinates, vertical)
        delta = (stem - current) / 2
        for index in vertical.left:
            shift_x[index] = shift_x.get(index, 0.0) - delta
        for index in vertical.right:
            shift_x[index] = shift_x.get(index, 0.0) + delta

    for diagonal in plan.diagonals:
        regular_thickness, _ = measure_diagonal(reference_coordinates, diagonal)
        regular_ratio = regular_thickness / reference_stem
        target = stem * diagonal_ratio(regular_ratio, design_weight)
        current, _ = measure_diagonal(coordinates, diagonal)
        half = (target - current) / 2

        # Each edge keeps its own direction and slides along its own normal, away
        # from its opposite number. Any intentional taper in the approved drawing
        # survives, and a stroke already at its target does not move at all.
        for edge, opposite in (
            (diagonal.first, diagonal.second),
            (diagonal.second, diagonal.first),
        ):
            a, b, c = _line(coordinates[edge[0]], coordinates[edge[1]])
            mid = (
                (coordinates[opposite[0]][0] + coordinates[opposite[1]][0]) / 2,
                (coordinates[opposite[0]][1] + coordinates[opposite[1]][1]) / 2,
            )
            outward = -1.0 if a * mid[0] + b * mid[1] - c > 0 else 1.0
            new_lines[_edge_key(edge)] = (a, b, c + outward * half)

    updated = list(coordinates)
    for index, delta in shift_x.items():
        updated[index] = (coordinates[index][0] + delta, coordinates[index][1])

    # A stem edge only needs to publish its line when a junction has to meet it.
    junction_edges = {j.first for j in plan.junctions} | {j.second for j in plan.junctions}
    for vertical in plan.stems:
        for group in (vertical.left, vertical.right):
            for edge in junction_edges:
                if edge[0] in group and edge[1] in group:
                    new_lines[edge] = _line(updated[edge[0]], updated[edge[1]])

    # Undeclared edges stay fixed in space, so every vertex resolves from the
    # approved geometry rather than from whichever neighbour happened to move
    # first.
    for contour in _contour_ranges(glyph):
        cycle = _on_curve_cycle(glyph, contour)
        if len(cycle) < 3:
            continue
        count = len(cycle)
        resolved: dict[int, tuple[float, float]] = {}
        for position, index in enumerate(cycle):
            previous = cycle[position - 1]
            following = cycle[(position + 1) % count]
            incoming = (previous, index)
            outgoing = (index, following)
            if incoming not in new_lines and outgoing not in new_lines:
                continue
            first = new_lines.get(incoming) or _line(
                coordinates[previous], coordinates[index]
            )
            second = new_lines.get(outgoing) or _line(
                coordinates[index], coordinates[following]
            )
            point = _resolve(
                first,
                second,
                coordinates[index],
                incoming in new_lines,
                outgoing in new_lines,
            )
            if point is not None:
                resolved[index] = point
        for index, point in resolved.items():
            updated[index] = point
        straight = {
            (start, end)
            for start, end in zip(cycle, [*cycle[1:], cycle[0]])
            if (end - start) % len(glyph.coordinates) == 1
        }
        _clamp_flats(glyph, updated, coordinates, cycle, new_lines, straight)

    scale = stem / reference_stem if reference_stem else 1.0
    for junction in plan.junctions:
        first_key = _edge_key(junction.first)
        second_key = _edge_key(junction.second)
        if first_key not in new_lines or second_key not in new_lines:
            continue
        reference_mitre = _intersect(
            _line(
                reference_coordinates[junction.first[0]],
                reference_coordinates[junction.first[1]],
            ),
            _line(
                reference_coordinates[junction.second[0]],
                reference_coordinates[junction.second[1]],
            ),
        )
        first_line = new_lines[first_key]
        second_line = new_lines[second_key]
        mitre = _intersect(first_line, second_line)
        if reference_mitre is None or mitre is None:
            continue
        if junction.min_y is not None:
            # The floor applies to the lowest point of the assembly, not to the
            # meeting point: the tip sits below it.
            lowest = min(
                reference_coordinates[index][1]
                for index in range(junction.first[1], junction.second[0] + 1)
            )
            floor = junction.min_y + (reference_mitre[1] - lowest) * scale
            if mitre[1] < floor:
                mitre = (mitre[0], floor)

        for index in range(junction.first[1], junction.second[0] + 1):
            updated[index] = (
                mitre[0] + (reference_coordinates[index][0] - reference_mitre[0]) * scale,
                mitre[1] + (reference_coordinates[index][1] - reference_mitre[1]) * scale,
            )
        # The joins belong on their own edges; the reference direction and the
        # master's can differ by a fraction of a degree.
        updated[junction.first[1]] = _project(first_line, updated[junction.first[1]])
        updated[junction.second[0]] = _project(second_line, updated[junction.second[0]])

    _carry_controls(glyph, coordinates, updated)
    glyph.coordinates = type(glyph.coordinates)(
        [(round(x), round(y)) for x, y in updated]
    )
    return glyph


def _clamp_flats(glyph, updated, original, cycle, new_lines, straight) -> None:
    """Move a vertex cut to the mitre wherever the edges would cross it."""
    count = len(cycle)
    for position, index in enumerate(cycle):
        following = cycle[(position + 1) % count]
        flat = (index, following)
        if flat in new_lines or flat not in straight:
            continue
        before = cycle[position - 1]
        after = cycle[(position + 2) % count]
        entering = (before, index)
        leaving = (following, after)
        if entering not in new_lines or leaving not in new_lines:
            continue
        first, second = new_lines[entering], new_lines[leaving]
        # A stroke's own end cap sits between that stroke's two parallel edges.
        # They have no meaningful meeting point, and nothing can cross there.
        if abs(first[0] * second[1] - second[0] * first[1]) < PARALLEL_SINE:
            continue
        mitre = _intersect(first, second)
        if mitre is None:
            continue
        rising = original[index][1] - original[before][1]
        falling = original[after][1] - original[following][1]
        if rising < 0 and falling > 0:
            beyond = mitre[1] > min(updated[index][1], updated[following][1])
        elif rising > 0 and falling < 0:
            beyond = mitre[1] < max(updated[index][1], updated[following][1])
        else:
            continue
        if not beyond:
            continue
        # The cut runs along the average travel direction through the vertex.
        # Taking it from the existing flat would preserve the very reversal that
        # made the outline cross in the first place.
        entering_direction = _unit(
            (
                original[index][0] - original[before][0],
                original[index][1] - original[before][1],
            )
        )
        leaving_direction = _unit(
            (
                original[after][0] - original[following][0],
                original[after][1] - original[following][1],
            )
        )
        direction = _unit(
            (
                entering_direction[0] + leaving_direction[0],
                entering_direction[1] + leaving_direction[1],
            )
        )
        half = MIN_FLAT_WIDTH / 2
        updated[index] = (
            mitre[0] - direction[0] * half,
            mitre[1] - direction[1] * half,
        )
        updated[following] = (
            mitre[0] + direction[0] * half,
            mitre[1] + direction[1] * half,
        )


def _carry_controls(glyph, original, updated) -> None:
    """Move off-curve controls with their bracketing on-curve joins."""
    for contour in _contour_ranges(glyph):
        indices = list(contour)
        on_curve = [i for i in indices if glyph.flags[i] & 1]
        if not on_curve or len(on_curve) == len(indices):
            continue
        count = len(indices)
        for start, end in zip(on_curve, [*on_curve[1:], on_curve[0]]):
            span = (indices.index(end) - indices.index(start)) % count
            if span <= 1:
                continue
            start_delta = (
                updated[start][0] - original[start][0],
                updated[start][1] - original[start][1],
            )
            end_delta = (
                updated[end][0] - original[end][0],
                updated[end][1] - original[end][1],
            )
            for step in range(1, span):
                index = indices[(indices.index(start) + step) % count]
                fraction = step / span
                updated[index] = (
                    original[index][0]
                    + start_delta[0]
                    + (end_delta[0] - start_delta[0]) * fraction,
                    original[index][1]
                    + start_delta[1]
                    + (end_delta[1] - start_delta[1]) * fraction,
                )


def _design_weight_for_stem(stem: float) -> float:
    if stem <= 80:
        return 100 + (stem - 50) * 10
    return 400 + (stem - 80) * (400 / 70)
