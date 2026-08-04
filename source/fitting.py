"""Fit each glyph in the cell by moving its sidebearings, not by scaling it.

Scaling a glyph horizontally changes its vertical stems with it: the `X_SCALE_BY_CHAR`
table thinned `l`'s stem to 70 against the family's 80 and `1`'s further still. This
pass changes how much room a letter takes without touching stroke weight, by
translating the outermost ink bands and stretching only the space between them.

Why it is needed at all: measured against Berkeley Mono, the structural capitals sat
15–38% further from the cell edge, so adjacent letters carried about 25% more air,
while the intrinsically narrow letters — `i j 1 f Y` — were stretched wider than
they want to be. The range of widths was compressed at both ends. `notes/FITTING.md`
records the measurements.

The target is a sidebearing per shape class, because a round letter has to be set
tighter than a flat-sided one to look equally spaced, and a diagonal tighter again.
"""

from __future__ import annotations

from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

ADVANCE = 579
CAP_HEIGHT = 680
# The family's stem at the default instance. Both the sidebearing targets and the
# stem restoration are stated relative to it.
REGULAR_STEM = 80.0

# Sidebearing as a fraction of the cell, at the default instance. Rounds are set
# tighter than flats and diagonals tighter than rounds: the eye reads a curve or an
# apex as further away than a flat edge at the same distance.
FLAT = 0.132
ROUND = 0.112
# Narrow letters keep air instead of being stretched to fill the cell.
NARROW = 0.200

# A heavier weight fills more of its cell: as the stroke grows the sidebearing has
# to give way, or the letter keeps a light weight's air around a heavy weight's
# stroke. Measured across full ladders, ABC Diatype Mono gives up 0.27 units of
# sidebearing per unit of stem gained and KH Teka Mono 0.29, averaged over their
# flats; on the glyphs they fit tightest the rate is closer to 0.5.
#
# Applying a constant target at every master instead pins ink width across the whole
# axis. The glyphs this pass reaches then stay at their default width while the ones
# it excludes - every diagonal, N, and the digits - grow normally, so the two
# populations drift apart with every step up the ladder and the rhythm comes apart
# at the heavy end. Measured before this was fixed: cell fill spread rose 0.055 at
# Thin to 0.081 at ExtraBold, where both reference families fall.
SHRINK_PER_STEM = 0.51

# The round compensation also grows with weight. At Regular, Diatype sets its rounds
# 0.006 of a cell tighter than its flats; at Ultra, 0.040 tighter. A heavy curve
# reads further from its neighbour than a heavy flat does, more so than a light one.
ROUND_SHRINK_BONUS = 0.14

SHAPE_CLASS: dict[str, float] = {}


def _assign(names: str, target: float) -> None:
    for name in names.split():
        SHAPE_CLASS[name] = target


# Flat-sided and round letters only. A letter whose strokes cross the cell's
# midline - every diagonal, and N - cannot be refitted this way without changing
# the thickness of those strokes, because the midline is the region that stretches.
# They are also already the tightest-fitted glyphs in the family, so they gain
# least. R and r are asserted against their source drawings and stay put.
_assign("H I U E F L T B D P J", FLAT)
_assign("h n u m b d p q", FLAT)
_assign("O C G Q S", ROUND)
_assign("o c e s a g", ROUND)
_assign("i j l t f one", NARROW)

# M and W carry their diagonals across the cell's midline, which is the one region
# this pass stretches, so refitting them would undo the thickness the stroke system
# sets. Both are already fitted tighter than the rest of the family.
EXCLUDED = frozenset({"M", "W", "N", "K", "k", "A", "V", "X", "Y", "Z", "R", "r",
                      "v", "w", "x", "y", "z", "asterisk"})

# Anything whose ink is a single band through the middle of the cell cannot have its
# width changed without scaling its one stem, so it is left alone.
MIN_BAND_SEPARATION = 12.0


def _ink_bands(glyph, glyf, samples: int = 40) -> tuple[float, float, float, float] | None:
    """Return (left band start, left band end, right band start, right band end).

    The bands are the outermost runs of ink, taken across the glyph's height so a
    crossbar at one height does not hide a stem at another.
    """
    coordinates, endpoints, _ = glyph.getCoordinates(glyf)
    if not len(coordinates):
        return None
    ys = [y for _, y in coordinates]
    low, high = min(ys), max(ys)
    if high - low < 1:
        return None

    contours = []
    start = 0
    for end in endpoints:
        contours.append([tuple(coordinates[i]) for i in range(start, end + 1)])
        start = end + 1

    left_edges: list[float] = []
    right_edges: list[float] = []
    for index in range(samples):
        y = low + (high - low) * (index + 0.5) / samples
        spans = _spans(contours, y)
        # Only heights where the letter is open tell us where its sides are. At a
        # crossbar the ink is one run across the whole width, which would collapse
        # the two bands into each other.
        if len(spans) < 2:
            continue
        left_edges.append(spans[0][1])
        right_edges.append(spans[-1][0])
    if not left_edges:
        return None

    xs = [x for x, _ in coordinates]
    # Take the narrowest extent of each side, not the widest, so the band is inside
    # ink at every height. The widest extent lets a shoulder join reach across and
    # the two bands overlap, which is what happens on n, a, k and the diagonals.
    return min(xs), min(left_edges), max(right_edges), max(xs)


def _spans(contours, y):
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
    merged = []
    for span in spans:
        if merged and span[0] <= merged[-1][1] + 0.5:
            merged[-1] = (merged[-1][0], max(merged[-1][1], span[1]))
        else:
            merged.append(span)
    return merged


def target_units(fraction: float, stem: float, is_round: bool = False) -> float:
    """Sidebearing in font units for a shape class at a given weight.

    `fraction` is the class target at the default instance; `stem` is the family's
    stem at this master's weight. Returns units, not a fraction, so the weight
    dependence lives in one place.
    """
    # Only above the default. Below it the light weights already measured correct -
    # Thin's flats filled 0.737 of the cell against ABC Diatype Mono Thin's 0.736 -
    # and letting the target grow toward Thin re-creates the same two-population
    # split in the other direction: measured, it widened the spacing scatter in
    # `hamburge` from 0.073 to 0.090 at Thin while fixing nothing.
    if stem <= REGULAR_STEM:
        return fraction * ADVANCE
    rate = SHRINK_PER_STEM + (ROUND_SHRINK_BONUS if is_round else 0.0)
    return fraction * ADVANCE - rate * (stem - REGULAR_STEM)


def _stem_side(glyph, glyf, samples: int = 40) -> str | None:
    """Which side of a single-band glyph carries the full-height stem.

    `E F I L T` hold one run of ink at almost every height, so `_ink_bands` finds no
    two bands and returns None - which meant this pass never reached them at any
    weight, and they kept whatever the masters gave. `L` came out 0.181 of the cell
    on the left against 0.052 on the right.

    There is nothing to stretch in a single band, only somewhere to put it. The side
    to fit is the one a stem spans, because a vertical stem is what sets the rhythm
    against the previous letter; an arm end does not. A stem holds its edge over the
    glyph's height and an arm does not, so compare how much each edge moves.
    Returns "left", "right", or None when the two are too close to call, which is
    the symmetric case - `I` and `T` - where centring is right.
    """
    coordinates, endpoints, _ = glyph.getCoordinates(glyf)
    if not len(coordinates):
        return None
    ys = [y for _, y in coordinates]
    low, high = min(ys), max(ys)
    if high - low < 1:
        return None
    contours_list, start = [], 0
    for end in endpoints:
        contours_list.append([tuple(coordinates[i]) for i in range(start, end + 1)])
        start = end + 1

    lefts, rights = [], []
    for index in range(samples):
        y = low + (high - low) * (index + 0.5) / samples
        runs = _spans(contours_list, y)
        if not runs:
            continue
        lefts.append(runs[0][0])
        rights.append(runs[-1][1])
    if len(lefts) < samples // 2:
        return None

    # An edge held by a stem barely moves; one held by arms of different lengths
    # sweeps across the cell.
    left_range = max(lefts) - min(lefts)
    right_range = max(rights) - min(rights)
    if abs(left_range - right_range) < MIN_BAND_SEPARATION:
        return None
    return "left" if left_range < right_range else "right"


def refit_single_band(glyph, glyf, target: float) -> float | None:
    """Translate a single-band glyph rigidly so its stem side sits at `target`.

    Nothing is stretched, so no stroke changes width. When neither side is a stem the
    ink is centred instead, which is what a symmetric glyph wants.
    """
    xs = [x for x, _ in glyph.coordinates]
    if not xs:
        return None
    left, right = min(xs), max(xs)
    side = _stem_side(glyph, glyf)
    if side == "left":
        shift = target - left
    elif side == "right":
        shift = (ADVANCE - target) - right
    else:
        shift = (ADVANCE - (right - left)) / 2 - left
    if abs(shift) < 0.5:
        return None
    glyph.coordinates = GlyphCoordinates(
        [(round(x + shift), y) for x, y in glyph.coordinates]
    )
    return 0.0


def refit(glyph, glyf, target: float) -> float | None:
    """Move the outermost ink to `target` units of sidebearing without changing
    stroke widths.

    The two outer bands translate rigidly, so every horizontal distance inside them
    — every stem width — survives. Only the space between them stretches, which is
    what widening or narrowing a letter should do.
    """
    bands = _ink_bands(glyph, glyf)
    if bands is None:
        return None
    left_start, left_end, right_start, right_end = bands
    if right_start - left_end < MIN_BAND_SEPARATION:
        return None
    shift_left = target - left_start
    shift_right = (ADVANCE - target) - right_end
    if abs(shift_left) < 0.5 and abs(shift_right) < 0.5:
        return None

    def mapped(x: float) -> float:
        if x <= left_end:
            return x + shift_left
        if x >= right_start:
            return x + shift_right
        # Between the bands the gap takes up the difference.
        span = right_start - left_end
        if span <= 0:
            return x
        fraction = (x - left_end) / span
        new_left = left_end + shift_left
        new_right = right_start + shift_right
        return new_left + (new_right - new_left) * fraction

    glyph.coordinates = GlyphCoordinates(
        [(round(mapped(x)), y) for x, y in glyph.coordinates]
    )
    return shift_right - shift_left


ROUND_CLASS = frozenset("O C G Q S o c e s a g".split())


def apply(font, stem: float = REGULAR_STEM) -> dict[str, float]:
    """Refit every classified glyph. Returns the width change per glyph.

    `stem` is the family's stem at this master's weight, not a constant. Passing the
    default here fits every master to the default's ink width, which is the defect
    described on `SHRINK_PER_STEM`.
    """
    glyf = font["glyf"]
    cmap = font.getBestCmap()
    by_name: dict[str, float] = {}
    for codepoint, name in cmap.items():
        character = chr(codepoint)
        if name in EXCLUDED:
            continue
        fraction = SHAPE_CLASS.get(character) or SHAPE_CLASS.get(name)
        if fraction is None:
            continue
        glyph = glyf[name]
        if glyph.numberOfContours <= 0:
            continue
        if font["hmtx"].metrics[name][0] != ADVANCE:
            continue
        target = target_units(fraction, stem, is_round=character in ROUND_CLASS)
        # Two bands means the glyph can be widened or narrowed; one band means it can
        # only be moved. `refit` returns None for both an unfittable glyph and one
        # already at target, so decide on the bands rather than on its return value.
        if _ink_bands(glyph, glyf) is None:
            change = refit_single_band(glyph, glyf, target)
        else:
            change = refit(glyph, glyf, target)
        if change is not None:
            glyph.recalcBounds(glyf)
            font["hmtx"].metrics[name] = (ADVANCE, glyph.xMin)
            by_name[name] = change
    return by_name


# X_SCALE_BY_CHAR fits these glyphs by scaling them horizontally, which takes their
# vertical stem with it: l is scaled 0.87 and its stem came out 70 against the
# family's 80, and 1 at 0.82 came out 66. The scale is kept, because it is what sets
# their width; the stem is put back afterwards.
# Only glyphs with one unambiguous vertical stem. The curved digits have no such
# stem, and detecting a "narrowest run" on them finds the thin part of a curve and
# corrects the wrong thing - it took 5 from 83 to 76 and 8 from 78 to 66.
STEM_COMPENSATED = ("l", "one")


def _stem_band(glyph, glyf, samples: int = 40):
    """Centre and width of the narrowest consistent vertical run of ink."""
    coordinates, endpoints, _ = glyph.getCoordinates(glyf)
    if not len(coordinates):
        return None
    ys = [y for _, y in coordinates]
    low, high = min(ys), max(ys)
    contours, start = [], 0
    for end in endpoints:
        contours.append([tuple(coordinates[i]) for i in range(start, end + 1)])
        start = end + 1

    candidates = []
    for index in range(samples):
        y = low + (high - low) * (index + 0.5) / samples
        spans = _spans(contours, y)
        if not spans:
            continue
        narrowest = min(spans, key=lambda span: span[1] - span[0])
        candidates.append(narrowest)
    if not candidates:
        return None
    widths = sorted(span[1] - span[0] for span in candidates)
    median_width = widths[len(widths) // 2]
    # Take the centre from the runs closest to that width, so a shoulder or a
    # terminal cannot drag it.
    close = [s for s in candidates if abs((s[1] - s[0]) - median_width) <= 2]
    centres = sorted((s[0] + s[1]) / 2 for s in close)
    return centres[len(centres) // 2], median_width


def measure_vertical_stem(font, glyph_name: str = "H") -> float | None:
    """Measure the control stem after weight and optical-size transforms."""
    band = _stem_band(font["glyf"][glyph_name], font["glyf"])
    return None if band is None else band[1]


def restore_stem(glyph, glyf, target: float = REGULAR_STEM, scale: float = 1.0):
    """Widen the vertical stem back to target without changing the glyph's width.

    Everything left of the stem's centre moves left and everything right moves
    right, so the only horizontal distance that changes is the one spanning that
    centre, which is the stem itself.
    """
    band = _stem_band(glyph, glyf)
    if band is None:
        return None
    centre, width = band
    wanted = target * scale if scale != 1.0 else target
    delta = (wanted - width) / 2
    if abs(delta) < 0.5:
        return None
    glyph.coordinates = GlyphCoordinates(
        [(round(x - delta if x < centre else x + delta), y) for x, y in glyph.coordinates]
    )
    return delta * 2


# `L`'s foot bar stops short of where the flats end, so the gap after it reads as a
# hole: at ExtraBold its right sidebearing was 0.162 of the cell against 0.071 on
# `H`, a 53-unit shortfall, and fitting can only slide the glyph, not fill it.
# Stretching the bar is not a stroke change — the bar is horizontal, so lengthening
# it leaves its thickness alone.
BAR_LENGTHENED = ("L", "Lacute", "Lcommaaccent", "Lcaron", "Ldot", "Lslash")


def lengthen_bar(glyph, glyf, target_right: float) -> float | None:
    """Stretch the horizontal bar right of the stem so its end reaches `target_right`."""
    band = _stem_band(glyph, glyf)
    if band is None:
        return None
    centre, width = band
    stem_right = centre + width / 2
    xs = [x for x, _ in glyph.coordinates]
    if not xs:
        return None
    right = max(xs)
    reach = right - stem_right
    if reach < MIN_BAND_SEPARATION or abs(target_right - right) < 0.5:
        return None
    scale = (target_right - stem_right) / reach
    if scale <= 0:
        return None
    glyph.coordinates = GlyphCoordinates(
        [
            (round(x if x <= stem_right else stem_right + (x - stem_right) * scale), y)
            for x, y in glyph.coordinates
        ]
    )
    return target_right - right


def apply_bar_lengthening(font, stem: float) -> dict[str, float]:
    """Bring `L`'s bar out to the same right edge the flat-sided capitals reach."""
    glyf = font["glyf"]
    cmap = font.getBestCmap()
    target_right = ADVANCE - target_units(FLAT, stem)
    result: dict[str, float] = {}
    for character in BAR_LENGTHENED:
        name = cmap.get(ord(character)) if len(character) == 1 else character
        if name is None or name not in glyf:
            continue
        glyph = glyf[name]
        if glyph.numberOfContours <= 0:
            continue
        change = lengthen_bar(glyph, glyf, target_right)
        if change is not None:
            glyph.recalcBounds(glyf)
            font["hmtx"].metrics[name] = (ADVANCE, glyph.xMin)
            result[name] = change
    return result


def apply_stem_compensation(font, stem: float) -> dict[str, float]:
    """`stem` is the family's stem at this master's weight, not a constant."""
    glyf = font["glyf"]
    result: dict[str, float] = {}
    for name in STEM_COMPENSATED:
        if name not in glyf:
            continue
        glyph = glyf[name]
        if glyph.numberOfContours <= 0:
            continue
        change = restore_stem(glyph, glyf, target=stem)
        if change is not None:
            glyph.recalcBounds(glyf)
            font["hmtx"].metrics[name] = (ADVANCE, glyph.xMin)
            result[name] = change
    return result
