# Fractal Mono design notes

Fractal Mono is an upright monospaced family designed by Claudia Nathan. Its visual system is crisp, slightly brutalist, and deliberately uniform across code, interface, editorial, and display settings.

## Metrics

- Units per em: `1000`
- Normal-width advance: `579`
- Condensed/expanded advances: `492` / `666`
- Cap height: `680`
- Default x-height: `528`
- Text x-height: `540`
- Display x-height: `500`
- Lowercase ascender height: `728`
- Lowercase descender depth: `-195`
- Weight axis: `100–800`
- Width axis: `85–115`, default `100`
- Optical-size axis: `9–72`, default `14`

Every spacing glyph keeps the same cell at a given width instance. The width axis
changes that shared cell and the drawing together; weight and optical size leave
it unchanged.

## Construction

- `J/j` use a direct stem and compact low hook.
- `K` uses a horizontal bridge and outward diagonal junction.
- `R/r/K` are anchored by exact Book drawings and refit through dedicated compatible masters.
- `M` has open inner joins; `W` has a pinched angular centre.
- `S` stays compact and controlled through the heavy end of the axis.
- Heavy `C/G/M/N/S` approach the designer's silhouette references through
  compatible point deltas above weight 500; the references specify shape, not
  mechanical stroke expansion.
- `t` has a flat, parallel-sided ascender and short hook.
- The top of the `t` crossbar sits on the flat x-height; its ascender rises above
  that zone. Rounded lowercase forms overshoot the x-height and baseline by
  8–10 units so they appear the same height as flat forms rather than smaller.
- The lower-right `a` join is a trimmed quadratic boundary with no hidden loop,
  so filled and stroked outlines use the same clean silhouette.
- `! ? ^ ; : *` use angular construction and square terminals.
- Dots in `i`, `j`, punctuation, diacritics, and dotted counters use native four-point square contours.
- The default colon is centred on the optical x-height. `colon.case` reuses the
  same squares at the cap centre; `case` exposes it explicitly and `calt`
  selects it between capitals or lining figures.
- The semicolon reuses the matching colon's upper square and lower-square
  envelope before its comma head tapers into the tail.
- `O`, `o`, and `0` use centre dots by default.

Thin extends the source's compatible Thin-to-Regular point motion to a 32-unit
control stem, with explicit guards at the few joins that would otherwise reverse.
The accepted 300–500 range is pinned. Heavy masters make explicit counter,
aperture, joint-relief, and 1.03× round-stroke corrections so the family retains
its shape instead of simply accumulating stroke.

## Optical size

The Text master at `opsz 9` carries a taller x-height, larger square dots, and more open joins for small settings. The Display master at `opsz 72` uses a lower x-height, tighter details, and reduced dots. `opsz 14` is the default drawing and the source of the static family.

At Normal width, optical size does not change cap height, vertical metrics, or
the `579`-unit advance.

## Width

The registered `wdth` axis runs from Condensed `85` through Normal `100` to
Expanded `115`. Its cells are `492`, `579`, and `666` units. Compatible masters
move structural ink bands and diagonal skeletons while retaining the weight
axis's stem authority, square dots, vertical zones, component topology, mark
attachment, and programming-ligature grid.

Width never uses an anisotropic scale as the final drawing. Horizontal reach and
sidebearings change, but vertical metrics and every point's y coordinate remain
fixed. The family is monospaced at every width instance, not across different
width instances.

## Programming features

- Programming sequences remain literal by default.
- `150` joined drawings are available through `dlig`.
- Three legacy sequences remain literal even with `dlig` enabled.
- Longer repeated sequences are guarded against partial substitution.
- Each typed character retains its cursor cell.

## Rasterisation

The outlines are deliberately unhinted. The `gasp` table requests grayscale and
symmetric smoothing without grid fitting. A `ttfautohint` proof was evaluated on
Thin, Regular, and ExtraBold from 10–18px; it added roughly 45% to the static
files without a consistent rendering improvement and cannot provide the same
program to the variable font. Release validation covers source contours,
generated desktop and web fonts, interpolation grids, small-size rendering, and
browser specimens.

## Release history

See [CHANGELOG.md](../CHANGELOG.md).

## Invariants

- Keep the `579`-unit normal advance and the registered `85–115` width range.
- Keep every spacing glyph monospaced within each width instance.
- Keep programming ligatures opt-in.
- Keep square-dot contours simple, axis-aligned, and non-overlapping.
- Check Thin, Regular, and ExtraBold at Text, Auto, and Display optical sizes.
- Judge changes in outline view and real coding-size rendering.
