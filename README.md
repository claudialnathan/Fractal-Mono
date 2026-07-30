# Fractal Mono

A monospaced typeface for code, interfaces, and technical writing. Gently
brutalist construction, open counters, square punctuation, and a fixed `579`-unit
cell that keeps text sitting cleanly on the line.

Designed by Claudia Nathan. Free to use, under the SIL Open Font License 1.1.

![Fractal Mono specimen](specimens/FractalMono-specimen.png)

## Family

| Axis | Range | Default |
| --- | ---: | ---: |
| Weight (`wght`) | 100–800 | 400 |
| Optical size (`opsz`) | 9–72 | 14 |

Nine named weights: Thin, ExtraLight, Light, Regular, Book, Medium, SemiBold,
Bold, ExtraBold. Every named step is the same proportional change, so the ramp
reads evenly from one end to the other.

Optical size is a second design axis, not display scaling. The Text end raises the
x-height, enlarges the dots, and opens dense joins for small sizes; the Display end
lowers the x-height and tightens the drawing. Cap height, advance width, and the
vertical metrics hold constant across both axes.

- 1,746 glyphs, 1,363 encoded characters
- Latin, Greek, Cyrillic, symbols, box drawing, and Powerline
- 150 programming ligatures, drawn but off by default
- Character variants, dotless counters, tabular figures, fractions, superiors and
  inferiors

The signature set is the hooked `J j`, bridged `K`, compact `R r`, open `M`,
pinched `W`, compact `S`, and the angular `! ? ^ ; : *`. Dots on `i`, `j`,
punctuation and combining marks are exact squares; the counter dots in `O`, `o`
and `0` are circles. Diagonals are held to the family's stroke system at every
weight rather than left to interpolation.

## Install

**Desktop.** Install `fonts/desktop/FractalMono-Variable.ttf` for the whole axis
range, or the nine static faces in the same folder. Both can be installed
together. Some design tools clamp variable weights, so if a heavier weight renders
too light, use the statics there.

**Web.** Copy `fonts/web/` and `fractal-mono.css` into your project, or set it up
directly:

```css
@font-face {
  font-family: "Fractal Mono";
  src: url("./fonts/web/FractalMono-Variable.woff2") format("woff2") tech("variations");
  font-style: normal;
  font-weight: 100 800;
  font-display: swap;
}

code, pre, kbd {
  font-family: "Fractal Mono", ui-monospace, monospace;
  font-optical-sizing: auto;
  font-variant-ligatures: none;
}
```

One request covers the whole range. Use `font-weight` for weight and let
`font-optical-sizing: auto` follow the rendered size. To lock a specific optical
drawing:

```css
.display {
  font-optical-sizing: none;
  font-variation-settings: "opsz" 72;
}
```

**Editors and terminals.** Set the family to `Fractal Mono`. Terminals rasterise
each glyph into a fixed cell without hinting or subpixel positioning, so below
about 13px the strokes fall under one device pixel and soften. A slightly larger
size, or weight 500, holds up better there than the same settings would in an
editor.

## Features

Programming ligatures are drawn but **off by default**, so source stays literal
and cursoring stays predictable — every sequence keeps one advance per character.
Turn them on explicitly:

```css
code { font-variant-ligatures: discretionary-ligatures; }
```

| Feature | What it does |
| --- | --- |
| `dlig` | 150 programming ligatures, off by default |
| `ss03` | Dotless `O`, `o`, `0` — the dotted forms are the default |
| `cv01`–`cv20`, `cv99` | Character variants |
| `tnum`, `frac`, `sups`, `subs`, `zero` | Figures and fractions |

Longer repeated sequences are guarded, so a four-character run of the same
character stays literal even with `dlig` on.

## Files

- `fonts/desktop/` — variable font plus nine static weights at optical size 14
- `fonts/web/` — the same as `woff2` and `woff`
- `fractal-mono.css` — web setup with automatic optical sizing
- `specimen.html` — interactive tester, glyph set, features, release data
- `ligature-audit.html` — every programming sequence, shaped and literal
- `build-report.json` — release metrics, file sizes, SHA-256 hashes

## Build from source

Python 3.9+ and Node (for the browser-rendered proofs).

```sh
make setup      # install Python and Node dependencies
make build      # build every desktop and web artefact
make validate   # run both validation suites
make specimens  # regenerate proofs and specimen images
make release    # build, test, and package an archive
```

Builds are byte-reproducible — the same source produces the same bytes, so a
release hash identifies the outlines rather than the moment of the build.

The upright is transformed from JetBrains Mono 2.304, which supplied the initial
character set and OpenType scaffolding. The design, metrics, stroke system, and
drawings are original. `source/DESIGN_NOTES.md` covers the architecture;
`source/stroke_system.py` and `source/key_symbols.py` hold the geometry the
family's own rules are enforced through.

Two suites gate a release. `source/validate.py` checks metadata, axes, metrics,
advances, features, and shaping across the axis grid. `source/validate_geometry.py`
samples 29 weights against 3 optical sizes for self-intersection,
diagonal-to-stem proportion, ink monotonicity, cell containment, dot squareness,
and counter-dot centring.

## Not in this release

No italic or oblique, no width axis, and no purpose-built Windows hinting — the
outlines are unhinted and request grayscale smoothing. Applications will
synthesise an oblique from the upright if asked for one.

## Licence

Licensed under the [SIL Open Font License 1.1](LICENSE.txt), with the Reserved
Font Name **Fractal Mono**.

In plain terms: use it for anything, personal or commercial, bundle it with your
software, embed it in a document, and modify it. Two conditions. Keep the
copyright and licence notice with it. And if you modify it, release your version
under a different name — the reserved name stays with the original, so "Fractal
Mono" always means this font.

## Credits

Designed and built by Claudia Nathan.

- [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) 2.304 by the
  JetBrains Mono Project Authors — the source master the upright is transformed
  from. SIL Open Font License 1.1.
- [Whois Mono](https://github.com/raphaelbastide/Whois-mono) by Raphaël Bastide —
  the lowercase `r` construction. SIL Open Font License 1.1.

Both notices are reproduced in full in [LICENSE.txt](LICENSE.txt).
