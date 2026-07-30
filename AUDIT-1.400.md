# Audit behind 1.400

Measurements taken from the release binaries with scanline geometry under the
nonzero winding rule, and compared against Inter 4.1, ABC Diatype Mono (static
and variable), TT Commons Pro Mono, KH Teka Mono, and Berkeley Mono.

## What was wrong

### The weight axis

`avar` came from JetBrains Mono unchanged while the stem system was redesigned to
`50/80/150`. Stem width per named step:

| wght | 1.305 | 1.400 | step per 100 units, 1.305 | 1.400 |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 50.0 | 50.0 | — | — |
| 200 | 61.1 | 58.5 | 11.1 | 8.5 |
| 300 | 71.1 | 68.4 | 10.0 | 9.9 |
| 400 | 80.0 | 80.0 | 8.9 | 11.6 |
| 500 | 92.9 | 93.0 | 12.9 | 13.7 |
| 600 | 103.9 | 109.2 | 11.0 | 16.2 |
| 700 | 121.3 | 128.1 | 17.4 | 18.9 |
| 800 | 150.0 | 150.0 | 28.7 | 21.9 |

The 1.305 ramp decelerated to 8.9 units and then accelerated to 28.7, a spread of
3.2x. 1.400 holds a constant ratio of 1.170 per 100 units, which the three
existing anchors already sit on to within 0.05%. Only the distribution changed.

The design space also had no master between 461 and 800, so the entire bold half
was one linear span. Masters now sit at design 100, 400, 461, 620, and 800.

### Diagonals

Perpendicular thickness as a fraction of the stem at the same instance:

| | Thin | Regular | ExtraBold | swing |
| --- | ---: | ---: | ---: | ---: |
| `K` arm, 1.305 | 1.36 | 0.94 | 0.53 | 0.83 |
| `K` arm, 1.400 | 0.97 | 0.94 | 0.87 | 0.10 |
| `W` outer, 1.305 | 1.33 | 0.98 | 0.71 | 0.62 |
| `W` outer, 1.400 | 0.99 | 0.98 | 0.93 | 0.06 |
| `M`, 1.305 | 1.17 | 0.95 | 0.53 | 0.64 |
| `M`, 1.400 | 0.97 | 0.95 | 0.89 | 0.08 |
| `k` arm / leg, 1.305 | 0.86 / 1.31 | 0.91 / 1.07 | 0.95 / 0.89 | crossed over |
| `k` arm / leg, 1.400 | 0.98 / 1.00 | 0.96 / 1.00 | 0.91 / 0.98 | 0.07 / 0.02 |

Reference swings across each family's full range, for the same measurements:
Inter 0.05–0.18, KH Teka Mono 0.02–0.17, TT Commons Pro Mono 0.06–0.23, ABC
Diatype Mono 0.02–0.29. No audited family puts a diagonal above 1.01x the stem at
any weight, and every one converges its strokes toward the stem at its thin
extreme, where there is no room for optical differentiation.

The glyphs that drifted are exactly the ones whose weight masters came from
geometric transfer. The inherited `N V X A x v y z` diagonals measured 0.04–0.13
swing and were left alone.

### Self-intersection

The lowercase `w`'s three vertex cuts inverted sign across the axis:

| cut | wght 100 | 400 | 800 |
| --- | ---: | ---: | ---: |
| first V, inner | +20 | −9 | −79 |
| second V, inner | +20 | −10 | −79 |
| middle peak, inner | −34 | −4 | +64 |

Two crossings from `wght` 300, three from 450. Invisible when filled, because
nonzero winding covers it, but the apex sat in the wrong place and the outline was
not valid geometry. `w` and `wcircumflex` are now clean at 29 weights against 3
optical sizes, as are `W`, `k`, `K`, and `M`.

### Everything else found

- The asterisk's arms ran backwards, 76 units at Thin down to 64 at ExtraBold, so
  it gained 6% of ink across an axis where letters gained 200%.
- `O` and `zero` took their counter dot's height from the upstream slashed zero,
  so it sat 10.5 units above the counter centre at Thin and 5.5 at ExtraBold.
  Lowercase `o` was centred correctly, which made the three inconsistent.
- `j`'s tittle was 13% larger than every other dot at `opsz` 72, because its size
  was measured from its own already optically-scaled bounds.
- `_clockwise_square` rounded four coordinates independently from a fractional
  centre, so `i`'s tittle came out 118x119.
- 42 accented composites and wide symbols left the 579 cell at heavy weights; the
  circumflex on `h` reached 74 units past the left edge and `Jcircumflex` 65 past
  the right.
- Two identical builds produced different bytes. `head.modified` was the only
  field that moved.

## What was checked and found correct

- Advance is 579 on every glyph at every instance. Cap height 680 and x-height
  528 are fixed across both axes.
- Horizontal-to-vertical stroke ratio holds at 0.87–0.89 across the whole axis, a
  swing of 0.01. Reference swings are 0.03–0.19.
- Stem consistency between `n`, `o`, and `H` swings 0.02 — tighter than every
  reference measured.
- The dot-to-stem ramp tracks Inter almost exactly (1.96 → 0.96 against Inter's
  2.30 → 1.02) and matches KH Teka. This was not a defect.
- Mean ink width over advance is 0.742, between JetBrains Mono's 0.730 and
  Berkeley Mono's 0.749 — the stated design intent, confirmed.
- Sidebearing spread and vertical-stem alignment are comparable to Berkeley Mono
  and inside the band set by the commercial references. The cap-stem group spans
  78 units against Berkeley's 75. Spacing was not changed.
- `W`'s counter closes to 0.23 of the stem at ExtraBold, between KH Teka Black's
  0.17 and Inter 900's 0.35. Normal, and not a reason to hold the diagonals back.

## Known and unchanged

- The ring in `copyright` and `registered` gains 43% of ink across the axis. It is
  a curve, so the straight-stroke system cannot restate it. Identical in 1.305.
- 48 glyphs carry a constant overlapping join inherited from the source master —
  the shoulder of `n`, the bowl of `d`, and similar. Resolved by nonzero winding,
  present at the approved Regular, and constant across the axis. Seven more vary
  their overlap count with weight (`ampersand`, `dollar`, `eogonek`, `m`, `nine`,
  `uogonek`, `Uogonek`); the same seven varied in 1.305.
- `W`'s middle apex rises from 512 at Thin to 524 at Regular and falls to 469 at
  ExtraBold. Lowering it at bold opens the counters and is standard; the 12-unit
  rise over the light half is 1.8% of cap height.
- `K`'s arm rotates from 43.5° off vertical at Thin to 37.4° at ExtraBold. Not
  addressed: correcting it means pinning the angle, which moves more of the
  approved drawing than thickness alone.

## Method note

Two findings were retracted during the audit rather than acted on. An apparent
growing ink trap in `k` and `K` was an artefact of rendering with even-odd fill;
under the nonzero winding rule a rasteriser actually applies, both are clean at
every weight. And the dot-size ramp, which looked wrong in isolation, matches the
references closely once compared.
