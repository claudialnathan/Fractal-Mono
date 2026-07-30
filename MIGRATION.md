# Migrating from CLN Mono to Fractal Mono

CLN Mono 1.305 is now Fractal Mono 1.400. The family name, the PostScript names,
and every file name changed, so both the `@font-face` sources and the
`font-family` declarations need updating.

Two behavioural changes matter beyond the rename:

- **SemiBold and Bold render heavier.** The weight axis was remapped so each named
  step is the same proportional change. `wght` 100, 400 and 800 are unchanged;
  500 goes from a stem of 92.9 to 93.0, 600 from 103.9 to 109.2, and 700 from
  121.3 to 128.1. If a heading looked right at 600 it may now want 550.
- **`K M W k w *` are redrawn away from Regular.** At 400–500 they are unchanged.
  At Thin and at Bold and above their diagonals now match the family stem
  instead of drifting; visual regression snapshots covering those weights will
  differ on purpose.

## What changed, by name

| Was | Now |
| --- | --- |
| `CLN Mono` | `Fractal Mono` |
| `CLNMono-Variable.ttf` | `FractalMono-Variable.ttf` |
| `CLNMono-Variable.woff2` | `FractalMono-Variable.woff2` |
| `CLNMono-Regular.ttf` and the other eight statics | `FractalMono-Regular.ttf`, etc. |
| `cln-mono.css` | `fractal-mono.css` |
| `~/repos/cln-mono` | `~/repos/fractal-mono` |

Axes, named instances, the 579-unit advance, cap height 680, x-height 528,
glyph coverage, and every OpenType feature are unchanged.

## Prompt for an agent working in a consuming repo

Paste this into a session opened in the repo that uses the font:

> The monospace font in this repo was called **CLN Mono** and has been renamed to
> **Fractal Mono** (version 1.400). Please migrate this repo to it.
>
> 1. Find every reference to the old font. Search for `CLN Mono`, `CLNMono`,
>    `cln-mono` and `cln_mono` across CSS, SCSS, Tailwind config, JS/TS, HTML,
>    JSON, Swift, Kotlin, `.xcassets`, Figma tokens, and any font manifest or
>    `@font-face` block. Also check editor and terminal config committed to the
>    repo (`settings.json`, `.vscode/`, `alacritty.*`, `kitty.conf`,
>    `wezterm.lua`, `.vimrc`, `ghostty`).
> 2. Rename the identifiers:
>    - `font-family` / family strings: `CLN Mono` becomes `Fractal Mono`
>    - file names in `src:` URLs and asset directories: `CLNMono-*` becomes
>      `FractalMono-*` (for example `CLNMono-Variable.woff2` becomes
>      `FractalMono-Variable.woff2`)
>    - a stylesheet named `cln-mono.css` becomes `fractal-mono.css`
>    - CSS custom properties or Tailwind theme keys named after the old font
>      (`--font-cln`, `fontFamily.cln`, and similar) become the Fractal
>      equivalent, and every usage site updates with them
> 3. Copy the new font files in. They are in `~/repos/fractal-mono/fonts/web`
>    (`.woff2` and `.woff`) and `~/repos/fractal-mono/fonts/desktop` (`.ttf`).
>    Prefer the single variable file `FractalMono-Variable.woff2` over the
>    statics unless this repo deliberately ships statics. Delete the old
>    `CLNMono-*` files once nothing references them.
> 4. Two rendering changes are deliberate, so do not try to compensate for them
>    in CSS:
>    - `font-weight: 500`, `600` and `700` are heavier than before, because the
>      weight axis was remapped so each named step is an equal proportional
>      change. `100`, `400` and `800` are unchanged. If a specific heading or
>      label now looks too heavy, lower its `font-weight` value rather than
>      changing anything else.
>    - `K M W k w` and `*` are redrawn at Thin and at Bold and above. Weights
>      400–500 are unchanged. Update visual regression baselines that cover the
>      other weights, and say which snapshots you refreshed.
> 5. Check nothing still falls back to a system font: grep for any remaining
>    `CLN` string, confirm each `src:` URL resolves to a file that exists, and
>    load the app to confirm the font is actually applied rather than silently
>    falling back.
> 6. Report what you changed, which files you touched, any snapshots you
>    refreshed, and anything you found that referenced the font in a way the
>    steps above did not cover.
>
> Do not change any type sizes, line heights, letter spacing, or layout. This is
> a rename plus a weight-ramp correction, nothing else.

## Reinstalling locally

The desktop font is installed from `fonts/desktop/FractalMono-Variable.ttf`. Only
the variable file is installed, so weights are selected with `font-weight` on the
family `Fractal Mono`; the static style names are not separate families.

Font caches are per-application as well as system-wide. Fully quit and reopen
Figma, Cursor, and any terminal before judging whether a glyph changed.
