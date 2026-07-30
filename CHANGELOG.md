# Changelog

## 1.420

- The counter dot in `O`, `o` and `zero` is a circle again, built as the same
  twelve-point quadratic it was drawn as before the square pass generalised to
  every dot-like mark. Diameter is set so the dot keeps the ink weight the square
  had, which lands on 119 units at Regular - the width it was originally drawn at.
- Free-standing dots and the `i`/`j` tittles stay square. Only these three
  counters are round.

## 1.410

- Rebuilt the option, command and return key symbols from the designer's own
  vectors, drawn at wght 600 for option and wght 500 for the other two.
  `source/key_symbols.py` carries each drawing and reconstructs it as stroke
  geometry, so it holds across the whole weight axis rather than only at the
  weight it was made at. Reconstruction at the design weight reproduces each
  supplied vector to within 1.6 units.
- All three now hold their outer size while the stroke grows, the way a letter
  holds its cap height. Previously command's and return's strokes barely moved
  across the axis at all.
- Option is 500 units wide against the previous 580, and return 557 against 634,
  so both now sit inside the cell where they used to overhang. Command is 712
  wide as drawn, which overhangs the 579 cell by 66 units each side.

## 1.400

Renamed from CLN Mono to Fractal Mono. Family name, PostScript names, file names,
and the repository all move; the OFL notices for JetBrains Mono and Whois Mono are
unchanged.

Weight axis:

- Replaced the upstream `avar` mapping, which had been inherited unchanged while
  the stem system was redesigned to `50/80/150`. Stem growth per 100 units of
  `wght` ran from 8.9 between Light and Regular to 28.7 between Bold and
  ExtraBold. The mapping is now computed from the family's own anchors and every
  named step is the same proportional change, a ratio of 1.170. Thin, Regular, and
  ExtraBold are unchanged; SemiBold and Bold are correspondingly heavier.
- Added weight masters at design 461 and 620. The bold half previously
  interpolated across one span from Book to ExtraBold.

Stroke system:

- Added `source/stroke_system.py`, which restates a declared stroke from the
  approved Regular direction at the family's target thickness and rebuilds the
  affected vertices as true intersections. Applied at Regular it reproduces the
  approved outline exactly.
- Corrected the diagonals on `K`, `M`, `W`, `k`, and `w`. Measured against the
  stem, `K` ran from 1.40x at Thin to 0.63x at ExtraBold, `W` from 1.33x to 0.71x,
  `M` from 1.17x to 0.53x; `k`'s arm and leg crossed over. All now hold inside the
  0.72–1.00 band that Inter, ABC Diatype Mono, TT Commons Pro Mono, KH Teka Mono,
  and Berkeley Mono keep across their own ranges.
- Fixed the lowercase `w`, whose vertex cuts inverted from +20 units at Thin to
  −79 at ExtraBold and produced real self-intersections from `wght` 300 up. A cut
  now moves to the mitre rather than crossing it.
- Rebuilt the asterisk's six arms through the stroke system. They had run
  backwards, 76 units at Thin down to 64 at ExtraBold, so it gained 6% of ink
  across an axis where letters gained 200%.
- `K`'s stem now matches `H` at every weight and optical size. Fitting the cell
  scales its arm and leg reach instead of the whole glyph.

Dots and fitting:

- Centred the counter dots in `O` and `zero`, which sat up to 10 units above
  their counter centre and drifted with weight while lowercase `o` was correct.
- All free-standing dots now derive from one shared size. `j`'s tittle had been
  13% oversized at Display because it was measured from its own scaled bounds.
- Square marks are built from one integer edge plus one integer size, so a dot
  can no longer come out a unit off square.
- Recentred 42 accented composites and wide symbols that left the cell at heavy
  weights; the circumflex on `h` had reached 74 units past the left edge.

Build and validation:

- Builds are byte-reproducible; `head.modified` was the only field that moved.
- Added `source/validate_geometry.py`, which samples 29 weights against 3 optical
  sizes for self-intersection, diagonal-to-stem band, ink monotonicity, cell
  containment, dot squareness, and counter-dot centring. Every defect above
  shipped in 1.305 with the existing release validation passing.
- Reference drawings are now asserted at every weight master rather than at one
  off-master location, and the anchor is resolved through the release mapping
  instead of assuming design and `wght` coincide.

Known, unchanged from 1.305: the ring in `copyright` and `registered` is a curve
the straight-stroke system cannot restate, and gains 43% of ink across the axis.
48 glyphs carry a constant overlapping join inherited from the source master,
resolved by the nonzero winding rule and present at the approved Regular.

## 1.305

- Replaced offset-derived `R/r/K` endpoints with explicit compatible Thin, Book, and ExtraBold cubic masters.
- Converted corresponding curves together so node order, flats, verticals, tangents, and joins remain stable throughout the weight axis.
- Added `ss03` dotless alternates for `O/o/0`; the square-dotted forms remain the defaults.
- Added node-correspondence proofs and preserved every unrelated encoded glyph against 1.304.

## 1.304

- Redrew uppercase `R`, lowercase `r`, and uppercase `K` from compatible Book-weight masters.
- Refit Thin through ExtraBold with uniform stroke growth and protected counters and apertures.
- Added exact Book-master checks and a dedicated filled and outline proof across both axes.
- Preserved every unrelated glyph against the previous release.

## 1.303

- Rebuilt signature weight masters with compatible curve-handle movement.
- Preserved the signature `J/j/K/M/W/S` constructions through every named weight.
- Matched `f`, `l`, and `t` horizontal details to the family stroke system.
- Removed the lowercase `r` terminal bulge and stabilized its shoulder.
- Restored the tapered semicolon tail and protected the established `O/o/0` bowls.
- Expanded outline and interpolation validation to every named weight at Text, Auto, and Display optical sizes.

## 1.300

- Added a continuous optical-size axis from 9 to 72.
- Redrew `J/j/K/M/W/S` and the principal angular punctuation.
- Rebuilt dots and dotted marks as clean square contours.
- Corrected Thin `t` and fitted signature glyphs independently at heavy weights.
- Added self-contained source inputs, axis-grid validation, outline proofs, and release automation.

## 1.252

- Redrew uppercase `K` with a bridged junction.

## 1.250

- Restored clean quadratic curves and added dotted `O/o` defaults.
