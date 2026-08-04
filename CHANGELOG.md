# Changelog

## 1.0.0

First public release.

**Family.** Three axes: weight 100–800, width 85–115, and optical size 9–72,
with nine named weights from Thin to ExtraBold. 1,747 glyphs and 1,363 encoded
characters cover Latin, Greek, Cyrillic, symbols, box drawing, and Powerline.

**Metrics.** 1000 units per em, a 579-unit Normal-width advance on every encoded
non-mark glyph, cap height 680, x-height 528, ascender reach 728, descender −195.
Condensed, Normal, and Expanded instances use shared monospaced cells of 492,
579, and 666 units. Cap height and the vertical metrics hold constant across all
three axes; weight and optical size do not change the cell.

**Weight.** Control stems of 32, 80, and 150 units at Thin, Regular, and
ExtraBold. The ramp uses nearly even absolute increments, matching the measured
cadence of Geist Mono while retaining Fractal Mono's approved Regular. Thin
extends the source's compatible Thin-to-Regular motion instead of eroding or
offsetting the Regular outline.

**Stroke system.** `source/stroke_system.py` states each declared stroke from the
approved Regular direction at the family's target thickness and rebuilds the
affected vertices as true intersections, so diagonals track the stem instead of
drifting with interpolation. Thin diagonals receive optical relief, and every
measured diagonal remains within the validated 0.60–1.02 band. A vertex cut moves
to the mitre rather than crossing it.

**Extreme masters.** The accepted 300–500 drawings are pinned. Above 500,
compatible point deltas move `C G M N S` toward Claudia Nathan's heavy silhouette
references; the source drawings are normalised to the family stem rather than
treated as stroke-expansion instructions. `M` and `N` retain open inner joints,
`S` retains its hard zones and terminal cuts, and the round controls use a 1.03×
optical stroke while preserving their counters. Thin `J K M W` and the asterisk
have explicit control-point guards so no join or terminal reverses between
masters.

**Optical size.** Text raises the x-height to 540, enlarges the dots, and opens
dense joins; Display lowers it to 500 and tightens the drawing.

**Width.** Condensed 85, Normal 100, and Expanded 115 are compatible optical
masters, not horizontal scales. Structural ink bands and diagonal skeletons
move while stem thickness, counter integrity, and vertical geometry remain
stable. Intermediate widths interpolate through `gvar`, with advances supplied
through `HVAR`.

**Features.** 150 programming ligatures drawn but off by default under `dlig`, so
source stays literal and every sequence keeps one advance per character. Longer
repeats are guarded against partial ligation. Dotless `O o 0` under `ss03`;
character variants, tabular figures, fractions, superiors, and inferiors.

**Fitting.** Sidebearings are set per shape class — flat-sided letters at 0.132 of
the cell, rounds tighter at 0.112 — so a round letter looks as evenly spaced as a
flat one, and they tighten as the weight increases, because a heavier stroke has to
be given room out of the sidebearing rather than added to the letter's air. The
round compensation grows with weight for the same reason. `source/fitting.py`
changes a letter's width by translating its outermost ink bands and stretching only
the space between them, so stroke weights survive where a horizontal scale would
have thinned them; a letter whose ink is a single band, such as `E F I L T`, is
translated rigidly onto its stem instead. Where a glyph's width does come from a
scale, its stem is put back afterwards: `l` and `1` had carried stems of 70 and 66
against the family's 80.

**Details.** Dots on `i`, `j`, punctuation, and combining marks are exact squares
built from one integer edge plus one integer size. Lowercase colons sit on the
optical x-height centre; `case` and contextual capital/figure settings raise the
same squares to the cap centre. The semicolon derives its dot and comma head from
the matching colon before tapering. The lowercase `a` has a boolean-clean
bowl-to-stem join, so vector strokes do not expose a hidden loop. The counter
dots in `O`, `o`, and `0` are circles, centred in their counters at every weight
and optical size. The option,
command, and return key symbols are reconstructed from the designer's own vectors
as stroke geometry, so each holds across the whole axis. `usWinAscent` and
`usWinDescent` are set from measured ink so box-drawing glyphs, which pass the em
box on purpose in order to tile, are not clipped.

**Build.** Byte-reproducible: the same source produces the same bytes.
`source/version.py` is the only place the version is declared. Three suites gate
a release — `source/validate.py` for metadata, axes, metrics, advances, features
and shaping; `source/validate_geometry.py` sampling 29 weights against 3 optical
sizes; and `source/validate_width.py` sampling 15 weights, 3 optical sizes, and 7
widths for interpolation, metrics, outlines, shaping, stem stability, and cell
integrity.

**Known.** No italic or oblique, and no purpose-built Windows hinting. The
statics were evaluated with `ttfautohint`; it increased file size and made no
consistent improvement in the coding-size raster proof, so the release keeps the
coherent unhinted variable/static family. The ring in `copyright` and
`registered` gains less ink across the axis than the letters do. A number of
glyphs carry an inherited overlapping join resolved by the nonzero winding rule.

---

Development before 1.0.0 was private, under the working name CLN Mono. That
history is not carried here.
