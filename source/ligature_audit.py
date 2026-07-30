#!/usr/bin/env python3
"""Generate a browser catalog of every Fractal Mono base ligature definition."""

from __future__ import annotations

import html
from pathlib import Path

from fontTools.ttLib import TTFont


PROJECT = Path(__file__).resolve().parents[1]
FONT = PROJECT / "fonts" / "desktop" / "FractalMono-Variable.ttf"
OUTPUT = PROJECT / "ligature-audit.html"
OPTIONAL_LITERAL = {"/\\", "\\/", "|||"}


def inventory() -> list[tuple[str, str, str]]:
    font = TTFont(FONT)
    reverse_ascii = {
        glyph_name: chr(codepoint)
        for codepoint, glyph_name in font.getBestCmap().items()
        if 0x20 <= codepoint < 0x7F
    }
    rows = []
    for glyph_name in font.getGlyphOrder():
        if ".liga" not in glyph_name or ".liga." in glyph_name:
            continue
        tokens = glyph_name.split(".liga")[0].split("_")
        sequence = "".join(reverse_ascii[token] for token in tokens)
        if sequence in OPTIONAL_LITERAL:
            state = "literal"
        else:
            state = "dlig"
        rows.append((sequence, glyph_name, state))
    return sorted(rows, key=lambda row: (len(row[0]), row[0]))


def main() -> None:
    rows = inventory()
    items = "\n".join(
        f"""
        <article class="row">
          <code class="source">{html.escape(sequence)}</code>
          <code class="shaped">{html.escape(sequence)}</code>
          <code class="literal">{html.escape(sequence)}</code>
          <span class="name">{html.escape(glyph_name)}</span>
          <span class="status {state}">{'optional / dlig' if state == 'dlig' else state}</span>
        </article>"""
        for sequence, glyph_name, state in rows
    )
    document = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Fractal Mono complete ligature audit</title>
    <link rel="icon" href="data:," />
    <link rel="stylesheet" href="./fractal-mono.css" />
    <style>
      :root {{ --weight: 400; color-scheme: light; background: #f4f3ed; color: #171714; font-synthesis: none; font-variant-ligatures: none; }}
      * {{ box-sizing: border-box; }}
      body {{ min-width: 320px; margin: 0; font-family: "Fractal Mono", monospace; }}
      main {{ width: min(1320px, calc(100% - 40px)); margin: 0 auto; padding: 32px 0 80px; }}
      header {{ display: grid; grid-template-columns: 1fr auto; gap: 24px; align-items: end; padding: 24px 0 34px; border-top: 2px solid; }}
      h1, p {{ margin: 0; }}
      h1 {{ max-width: 14ch; font-size: clamp(2.5rem, 7vw, 6.5rem); font-weight: 500; line-height: .92; letter-spacing: -.06em; }}
      .meta {{ max-width: 38ch; color: #6f706a; font-size: .75rem; line-height: 1.55; text-align: right; }}
      label {{ display: flex; align-items: center; gap: 12px; padding: 16px 0; border-top: 1px solid #bdbdb5; font-size: .75rem; }}
      input[type="range"] {{ width: min(360px, 60vw); accent-color: #214cff; }}
      input[type="checkbox"] {{ width: 1rem; height: 1rem; accent-color: #214cff; }}
      .columns, .row {{ display: grid; grid-template-columns: 9ch 10ch 10ch minmax(240px, 1fr) 15ch; gap: 18px; align-items: center; }}
      .columns {{ position: sticky; top: 0; z-index: 1; padding: 13px 14px; border-block: 1px solid; background: #f4f3ed; color: #6f706a; font-size: .65rem; letter-spacing: .06em; text-transform: uppercase; }}
      .row {{ min-height: 62px; padding: 8px 14px; border-bottom: 1px solid #d6d5cd; }}
      code {{ font: inherit; font-size: 1.45rem; font-weight: var(--weight); font-variant-ligatures: none; white-space: nowrap; }}
      .preview-ligatures code.shaped {{ font-variant-ligatures: discretionary-ligatures; }}
      .source {{ color: #214cff; }}
      .name {{ overflow: hidden; color: #6f706a; font-size: .7rem; text-overflow: ellipsis; white-space: nowrap; }}
      .status {{ color: #8a6b33; font-size: .65rem; text-transform: uppercase; }}
      .status.default {{ color: #2d744e; }}
      .status.dlig {{ color: #214cff; }}
      @media (max-width: 760px) {{
        header {{ grid-template-columns: 1fr; }}
        .meta {{ text-align: left; }}
        .columns, .row {{ grid-template-columns: 8ch 1fr 1fr; }}
        .columns span:nth-child(4), .columns span:nth-child(5), .name, .status {{ display: none; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>Every ligature, audited.</h1>
        <p class="meta">Fractal Mono v1.305 · {len(rows)} base definitions · 0 automatic programming ligatures · 150 optional dlig drawings · 3 intentionally literal. Each row compares the source, optional shaping, and literal characters.</p>
      </header>
      <label for="weight">Weight <input id="weight" type="range" min="100" max="800" value="400" /><output for="weight">400</output></label>
      <label for="ligatures"><input id="ligatures" type="checkbox" /> Preview optional programming ligatures (<code>dlig</code>)</label>
      <div class="columns"><span>Source</span><span>Shaped</span><span>Literal</span><span>Glyph</span><span>State</span></div>
      <section aria-label="Ligature inventory">{items}
      </section>
    </main>
    <script>
      const input = document.querySelector("#weight");
      const output = document.querySelector("output");
      const ligatures = document.querySelector("#ligatures");
      input.addEventListener("input", () => {{
        document.documentElement.style.setProperty("--weight", input.value);
        output.value = input.value;
      }});
      ligatures.addEventListener("change", () => {{
        document.documentElement.classList.toggle("preview-ligatures", ligatures.checked);
      }});
    </script>
  </body>
</html>
"""
    OUTPUT.write_text(document)
    print(f"Wrote {OUTPUT} with {len(rows)} rows")


if __name__ == "__main__":
    main()
