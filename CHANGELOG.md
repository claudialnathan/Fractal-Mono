# Changelog

## 1.0.0

First public release.

**Family.** Two axes: weight 100–800 and optical size 9–72, with nine named
weights from Thin to ExtraBold. 1,746 glyphs and 1,363 encoded characters
covering Latin, Greek, Cyrillic, symbols, box drawing, and Powerline.

**Metrics.** 1000 units per em, a fixed 579-unit advance on every encoded
non-mark glyph, cap height 680, x-height 528, ascender reach 728, descender −195.
Cap height, advance, and the vertical metrics hold constant across both axes.

**Weight.** Stem widths of 50, 80, and 150 at Thin, Regular, and ExtraBold. The
axis is mapped so every named step is the same proportional change — a ratio of
1.170 per 100 units — rather than leaving the distribution to the source master.

**Stroke system.** `source/stroke_system.py` states each declared stroke from the
approved Regular direction at the family's target thickness and rebuilds the
affected vertices as true intersections, so diagonals track the stem instead of
drifting with interpolation. Every diagonal holds inside the 0.72–1.00 band that
Inter, ABC Diatype Mono, TT Commons Pro Mono, KH Teka Mono, and Berkeley Mono keep
across their own ranges. A vertex cut moves to the mitre rather than crossing it.

**Optical size.** A real second design axis. Text raises the x-height to 540,
enlarges the dots, and opens dense joins; Display lowers it to 500 and tightens
the drawing.

**Features.** 150 programming ligatures drawn but off by default under `dlig`, so
source stays literal and every sequence keeps one advance per character. Longer
repeats are guarded against partial ligation. Dotless `O o 0` under `ss03`;
character variants, tabular figures, fractions, superiors, and inferiors.

**Details.** Dots on `i`, `j`, punctuation, and combining marks are exact squares
built from one integer edge plus one integer size. The counter dots in `O`, `o`,
and `0` are circles, centred in their counters at every weight and optical size.
The option, command, and return key symbols are reconstructed from the designer's
own vectors as stroke geometry, so each holds across the whole axis. `usWinAscent`
and `usWinDescent` are set from measured ink so box-drawing glyphs, which pass the
em box on purpose in order to tile, are not clipped.

**Build.** Byte-reproducible: the same source produces the same bytes.
`source/version.py` is the only place the version is declared. Two suites gate a
release — `source/validate.py` for metadata, axes, metrics, advances, features and
shaping, and `source/validate_geometry.py` sampling 29 weights against 3 optical
sizes for self-intersection, diagonal-to-stem proportion, ink monotonicity, cell
containment, dot squareness, and counter-dot centring.

**Known.** No italic or oblique, no width axis, and no purpose-built Windows
hinting. The ring in `copyright` and `registered` gains less ink across the axis
than the letters do; it is a curve, so the straight-stroke system cannot restate
it. A number of glyphs carry a constant overlapping join inherited from the source
master, resolved by the nonzero winding rule and present at Regular.

---

Development before 1.0.0 was private, under the working name CLN Mono. That
history is not carried here.
