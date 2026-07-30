# Fractal Mono design notes

Fractal Mono is an upright monospaced family designed by Claudia Nathan. Its visual system is crisp, slightly brutalist, and deliberately uniform across code, interface, editorial, and display settings.

## Metrics

- Units per em: `1000`
- Fixed advance: `579`
- Cap height: `680`
- Default x-height: `528`
- Text x-height: `540`
- Display x-height: `500`
- Lowercase ascender height: `728`
- Lowercase descender depth: `-195`
- Weight axis: `100–800`
- Optical-size axis: `9–72`, default `14`

Every spacing glyph keeps the same cell. Ink width, sidebearings, counters, joins, and optical proportions change without disturbing the monospaced rhythm.

## Construction

- `J/j` use a direct stem and compact low hook.
- `K` uses a horizontal bridge and outward diagonal junction.
- `R/r/K` are anchored by exact Book drawings and refit through dedicated compatible masters.
- `M` has open inner joins; `W` has a pinched angular centre.
- `S` stays compact and controlled through the heavy end of the axis.
- `t` has a flat, parallel-sided ascender and short hook.
- `! ? ^ ; : *` use angular construction and square terminals.
- Dots in `i`, `j`, punctuation, diacritics, and dotted counters use native four-point square contours.
- `O`, `o`, and `0` use centre dots by default.

Thin masters keep terminals and joins structurally clean. Heavy masters make explicit counter and aperture corrections so the family retains its shape instead of simply accumulating stroke.

## Optical size

The Text master at `opsz 9` carries a taller x-height, larger square dots, and more open joins for small settings. The Display master at `opsz 72` uses a lower x-height, tighter details, and reduced dots. `opsz 14` is the default drawing and the source of the static family.

Optical size does not change cap height, vertical metrics, or the `579`-unit advance.

## Programming features

- Programming sequences remain literal by default.
- `150` joined drawings are available through `dlig`.
- Three legacy sequences remain literal even with `dlig` enabled.
- Longer repeated sequences are guarded against partial substitution.
- Each typed character retains its cursor cell.

## Rasterisation

The outlines are deliberately unhinted. The `gasp` table requests grayscale and symmetric smoothing without grid fitting. Release validation covers the source contours, generated desktop and web fonts, interpolation grids, small-size rendering, and browser specimens.

## Release history

### 1.305

- Replaces offset-derived `R/r/K` endpoints with compatible Thin, Book, and ExtraBold cubic drawings.
- Converts corresponding cubic curves together to retain semantic node order and curve tangents.
- Adds a node-correspondence proof across the sensitive weight extremes.
- Adds optional dotless `O/o/0` under `ss03` while keeping the dotted defaults.
- Protects all unrelated glyphs against the preceding release.

### 1.304

- Redraws `R/r/K` from exact Book-weight constructions.
- Fits the signature forms across the weight axis while protecting counters and apertures.
- Adds a dedicated `R/r/K` filled and outline proof across every named weight and optical master.
- Protects all unrelated glyphs against the preceding release.

### 1.303

- Rebuilds signature masters with compatible curve-handle movement.
- Keeps short terminals and bridged joins uniform at every named weight.
- Stabilizes `f/l/t/r` details and the tapered semicolon construction.
- Preserves established `O/o/0` bowls while replacing only their dot contours.
- Extends filled and outline proofs across the complete named design space.

### 1.300

- Adds a true `opsz` axis with Text, Auto, and Display masters.
- Redraws `J/j/K/M/W/S` and `! ? ^ ; : *`.
- Rebuilds dot punctuation and combining marks as clean square contours.
- Corrects Thin `t` and applies dedicated heavy-master fitting.
- Makes the build self-contained and adds release-grade contour and axis checks.

### 1.252

- Redrew uppercase `K` with a stem bridge and outward junction.

### 1.251

- Consolidated family metadata, documentation, factsheets, and specimens.

### 1.250

- Restored clean quadratic controls.
- Added dotted `O/o` defaults.

### 1.240

- Raised lowercase ascenders from `680` to `728`.

## Invariants

- Keep the `579`-unit advance.
- Keep programming ligatures opt-in.
- Keep square-dot contours simple, axis-aligned, and non-overlapping.
- Check Thin, Regular, and ExtraBold at Text, Auto, and Display optical sizes.
- Judge changes in outline view and real coding-size rendering.
