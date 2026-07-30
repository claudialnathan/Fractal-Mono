#!/usr/bin/env python3
"""Generate a self-contained Fractal Mono type specimen."""

from __future__ import annotations

import base64
import html
import unicodedata
from pathlib import Path

from fontTools.ttLib import TTFont


PROJECT = Path(__file__).resolve().parents[1]
VARIABLE_TTF = PROJECT / "fonts" / "desktop" / "FractalMono-Variable.ttf"
VARIABLE_WOFF2 = PROJECT / "fonts" / "web" / "FractalMono-Variable.woff2"
OUTPUT = PROJECT / "specimens" / "Fractal-Mono-Type-Specimen.html"


INVISIBLE_LABELS = {
    0x0000: "NUL",
    0x0009: "TAB",
    0x000A: "LF",
    0x000D: "CR",
    0x0020: "SP",
    0x00A0: "NBSP",
    0x034F: "CGJ",
    0x061C: "ALM",
    0x2000: "NQSP",
    0x2001: "MQSP",
    0x2002: "ENSP",
    0x2003: "EMSP",
    0x2004: "3/MSP",
    0x2005: "4/MSP",
    0x2006: "6/MSP",
    0x2007: "FIGSP",
    0x2008: "PUNCSP",
    0x2009: "THINSP",
    0x200A: "HAIRSP",
    0x200B: "ZWSP",
    0x200C: "ZWNJ",
    0x200D: "ZWJ",
    0x2028: "LSEP",
    0x2029: "PSEP",
    0x202F: "NNBSP",
    0x205F: "MMSP",
    0x2060: "WJ",
    0x2061: "FA",
    0x2062: "IT",
    0x2063: "IS",
    0x2064: "IP",
    0xFEFF: "BOM",
}


def name_value(font: TTFont, name_id: int, default: str) -> str:
    for record in font["name"].names:
        if record.nameID == name_id:
            try:
                return record.toUnicode()
            except UnicodeDecodeError:
                continue
    return default


def glyph_markup(codepoint: int) -> str:
    character = chr(codepoint)
    category = unicodedata.category(character)
    if codepoint in INVISIBLE_LABELS:
        return html.escape(INVISIBLE_LABELS[codepoint])
    if category.startswith("M"):
        return f"◌{html.escape(character)}"
    if category.startswith("C") or character.isspace():
        return "CTRL"
    return html.escape(character)


def glyph_tiles(cmap: dict[int, str]) -> str:
    tiles: list[str] = []
    for codepoint, glyph_name in sorted(cmap.items()):
        character = chr(codepoint)
        unicode_name = unicodedata.name(character, "Unnamed character")
        search = f"U+{codepoint:04X} {unicode_name} {glyph_name}".lower()
        tiles.append(
            "\n".join(
                (
                    f'<li class="glyph-card" data-search="{html.escape(search, quote=True)}">',
                    f'  <span class="glyph-char" aria-hidden="true">{glyph_markup(codepoint)}</span>',
                    f'  <span class="glyph-code">U+{codepoint:04X}</span>',
                    f'  <span class="glyph-name">{html.escape(unicode_name.title())}</span>',
                    "</li>",
                )
            )
        )
    return "\n".join(tiles)


TEMPLATE = r'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="color-scheme" content="light" />
    <title>Fractal Mono — Type Specimen</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22><rect width=%2232%22 height=%2232%22 rx=%227%22 fill=%22%23202020%22/><path d=%22M8 10h16v3H14v3h8v3h-8v3h10v3H8z%22 fill=%22white%22/></svg>" />
    <style>
      @font-face {
        font-family: "Fractal Mono Specimen";
        src: url("data:font/woff2;base64,__FONT_DATA__") format("woff2-variations");
        font-display: block;
        font-style: normal;
        font-weight: 100 800;
      }

      :root {
        --background: oklch(0.991 0 0);
        --foreground: oklch(0.2393 0 0);
        --faint: oklch(0 0 0 / 0.4);
        --subtle: oklch(0 0 0 / 0.5);
        --border: oklch(0 0 0 / 0.075);
        --rule: oklch(0 0 0 / 0.1);
        --surface: oklch(1 0 0);
        --muted: oklch(0.9702 0 0);
        --blue: oklch(0.6187 0.2067 259.23);
        --cyan: oklch(0.8654 0.1272 207.08);
        --selection: oklch(0.8732 0.0955 217.8);
        --page-x: clamp(1.25rem, 3vw, 2.25rem);
        --measure: 40rem;
        --specimen-weight: 400;
        color: var(--foreground);
        background: var(--background);
        font-family: "Fractal Mono Specimen", monospace;
        font-synthesis: none;
        font-variant-ligatures: none;
        text-rendering: optimizeLegibility;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
      }

      :root.programming-ligatures {
        font-variant-ligatures: discretionary-ligatures;
      }

      * {
        box-sizing: border-box;
      }

      html {
        min-width: 20rem;
        scroll-behavior: smooth;
      }

      body {
        margin: 0;
        background:
          linear-gradient(var(--border) 1px, transparent 1px) top / 100% 4rem no-repeat,
          var(--background);
        font-size: 1rem;
        font-weight: 400;
        line-height: 1.55;
      }

      button,
      input,
      textarea {
        font: inherit;
      }

      ::selection {
        color: var(--foreground);
        background: var(--selection);
      }

      :focus-visible {
        outline: 2px solid var(--cyan);
        outline-offset: 2px;
      }

      a {
        color: var(--blue);
        text-decoration-thickness: from-font;
        text-underline-position: from-font;
      }

      .shell {
        inline-size: min(100%, calc(var(--measure) + 2 * var(--page-x)));
        margin-inline: auto;
        padding: 4rem var(--page-x) 7rem;
      }

      .hero {
        padding-block: 2.25rem 4rem;
      }

      .kicker,
      .meta-label,
      .section-number,
      .tester-label,
      .weight-label,
      .glyph-code,
      .glyph-name,
      .control-copy,
      .search-status {
        font-size: 0.75rem;
        line-height: 1.25rem;
      }

      .kicker,
      .meta-label,
      .section-number,
      .tester-label {
        letter-spacing: 0.075em;
        text-transform: uppercase;
      }

      .kicker {
        margin: 0 0 3rem;
        color: var(--faint);
      }

      h1,
      h2,
      p,
      pre,
      dl,
      dd {
        margin: 0;
      }

      h1 {
        max-inline-size: 8ch;
        font-size: clamp(3.75rem, 12vw, 7rem);
        font-weight: var(--specimen-weight);
        line-height: 0.92;
        letter-spacing: -0.06em;
        text-wrap: balance;
      }

      .dek {
        max-inline-size: 42ch;
        margin-block-start: 2rem;
        color: var(--subtle);
        font-size: 0.9375rem;
        line-height: 1.55;
        text-wrap: pretty;
      }

      .font-meta {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        margin-block-start: 3rem;
        border-block: 1px solid var(--border);
      }

      .font-meta > div {
        min-inline-size: 0;
        padding: 0.875rem 0;
      }

      .font-meta > div:nth-child(odd) {
        padding-inline-end: 1rem;
      }

      .font-meta > div:nth-child(even) {
        padding-inline-start: 1rem;
        border-inline-start: 1px solid var(--border);
      }

      .meta-label {
        display: block;
        color: var(--faint);
      }

      .meta-value {
        display: block;
        overflow-wrap: anywhere;
        font-size: 0.8125rem;
        font-variant-numeric: tabular-nums;
      }

      .weight-control {
        position: sticky;
        z-index: 10;
        top: 1rem;
        display: grid;
        grid-template-columns: auto minmax(8rem, 1fr) 4ch;
        gap: 1rem;
        align-items: center;
        margin-block-end: 5rem;
        padding: 0.875rem 1rem;
        border: 1px solid var(--border);
        border-radius: 0.625rem;
        background: color-mix(in oklab, var(--surface) 88%, transparent);
        box-shadow: 0 0.5rem 2rem -1rem oklch(0 0 0 / 0.18);
        backdrop-filter: blur(16px);
      }

      .control-copy {
        color: var(--subtle);
        white-space: nowrap;
      }

      input[type="range"] {
        inline-size: 100%;
        accent-color: var(--foreground);
        cursor: ew-resize;
      }

      output {
        color: var(--foreground);
        font-size: 0.8125rem;
        font-variant-numeric: tabular-nums;
        text-align: end;
      }

      .operator-toggle {
        grid-column: 1 / -1;
        display: flex;
        align-items: center;
        gap: 0.625rem;
        padding-block-start: 0.75rem;
        border-block-start: 1px solid var(--border);
        color: var(--subtle);
        font-size: 0.8125rem;
        cursor: pointer;
      }

      .operator-toggle input {
        inline-size: 1rem;
        block-size: 1rem;
        margin: 0;
        accent-color: var(--foreground);
      }

      section {
        padding-block: 0 5rem;
      }

      .section-heading {
        display: flex;
        gap: 1rem;
        align-items: flex-start;
        margin-block-end: 2rem;
        font-size: 0.9375rem;
        font-weight: 600;
        line-height: 1.25rem;
      }

      .section-heading::before {
        flex: 0 0 auto;
        inline-size: 4.75rem;
        block-size: 1px;
        margin-block-start: 0.625rem;
        content: "";
        background: var(--rule);
      }

      .section-number {
        margin-inline-start: auto;
        color: var(--faint);
        font-weight: 400;
        font-variant-numeric: tabular-nums;
      }

      .tester-grid {
        display: grid;
        gap: 1rem;
      }

      .tester {
        display: grid;
        gap: 0.625rem;
      }

      .tester-label {
        color: var(--faint);
      }

      textarea,
      .search-input {
        display: block;
        inline-size: 100%;
        border: 1px solid var(--border);
        border-radius: 0.625rem;
        color: var(--foreground);
        background: var(--surface);
        caret-color: var(--blue);
      }

      textarea {
        min-block-size: 11rem;
        padding: 1.125rem;
        resize: vertical;
        font-size: 1rem;
        font-weight: var(--specimen-weight);
        line-height: 1.55;
        tab-size: 2;
      }

      textarea::placeholder,
      .search-input::placeholder {
        color: var(--faint);
      }

      .code-tester textarea {
        background: var(--muted);
        font-size: 0.9375rem;
      }

      .prose-samples {
        display: grid;
        gap: 2rem;
      }

      .prose-sample {
        display: grid;
        grid-template-columns: 5.5rem minmax(0, 1fr);
        gap: 1.5rem;
        align-items: start;
      }

      .prose-sample p {
        max-inline-size: 65ch;
        font-size: 1rem;
        font-weight: var(--specimen-weight);
        line-height: 1.6;
      }

      .weight-label {
        padding-block-start: 0.2rem;
        color: var(--faint);
        font-variant-numeric: tabular-nums;
      }

      .weight-list {
        border-block-start: 1px solid var(--border);
      }

      .weight-row {
        display: grid;
        grid-template-columns: 5.5rem minmax(0, 1fr);
        gap: 1.5rem;
        align-items: baseline;
        padding-block: 1rem;
        border-block-end: 1px solid var(--border);
      }

      .weight-row p {
        overflow-wrap: break-word;
        font-size: clamp(1.05rem, 3.6vw, 1.5rem);
        line-height: 1.25;
      }

      .code-stack {
        display: grid;
        gap: 1rem;
      }

      .code-card {
        overflow: hidden;
        border: 1px solid var(--border);
        border-radius: 0.625rem;
        background: var(--muted);
      }

      .code-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.625rem 0.875rem;
        border-block-end: 1px solid var(--border);
        color: var(--faint);
        background: color-mix(in oklab, var(--surface) 70%, transparent);
        font-size: 0.75rem;
        line-height: 1.25rem;
      }

      pre {
        overflow-x: auto;
        padding: 1.125rem;
        font-size: 0.875rem;
        font-weight: var(--specimen-weight);
        line-height: 1.6;
        tab-size: 2;
      }

      .raster-intro,
      .raster-note {
        max-inline-size: 65ch;
        color: var(--subtle);
        font-size: 0.8125rem;
        line-height: 1.6;
      }

      .raster-grid {
        display: grid;
        margin-block: 1.5rem;
        border-block-start: 1px solid var(--border);
      }

      .raster-row {
        display: grid;
        grid-template-columns: 5.5rem minmax(0, 1fr);
        gap: 1.5rem;
        align-items: start;
        padding-block: 1rem;
        border-block-end: 1px solid var(--border);
      }

      .raster-copy {
        display: grid;
        gap: 0.35rem;
        overflow-wrap: anywhere;
        line-height: 1.45;
      }

      .raster-code {
        color: var(--subtle);
      }

      .raster-contrast {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        overflow: hidden;
        margin-block: 1.5rem;
        border: 1px solid var(--border);
        border-radius: 0.625rem;
      }

      .raster-contrast > div {
        min-inline-size: 0;
        padding: 1rem;
        background: var(--surface);
        font-size: 0.8125rem;
        line-height: 1.55;
      }

      .raster-contrast .dark {
        color: oklch(0.91 0 0);
        background: oklch(0.18 0 0);
      }

      .token-keyword,
      .token-tag {
        color: oklch(0.49 0.2 281);
      }

      .token-string,
      .token-attr {
        color: oklch(0.48 0.14 148);
      }

      .token-number,
      .token-value {
        color: oklch(0.55 0.17 42);
      }

      .token-comment {
        color: var(--faint);
        font-style: italic;
      }

      .core-set {
        display: grid;
        gap: 1.25rem;
      }

      .core-line {
        overflow-wrap: anywhere;
        font-size: clamp(1.25rem, 4.4vw, 2rem);
        font-weight: var(--specimen-weight);
        line-height: 1.55;
      }

      .core-note {
        color: var(--faint);
        font-size: 0.75rem;
        line-height: 1.5;
      }

      details {
        border-block: 1px solid var(--border);
      }

      summary {
        display: flex;
        gap: 1rem;
        align-items: center;
        padding-block: 1rem;
        cursor: pointer;
        font-size: 0.8125rem;
        list-style: none;
        user-select: none;
      }

      summary::-webkit-details-marker {
        display: none;
      }

      summary::before {
        inline-size: 1ch;
        content: "+";
        color: var(--faint);
      }

      details[open] summary::before {
        content: "−";
      }

      .search-bar {
        position: sticky;
        z-index: 5;
        top: 5.75rem;
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 1rem;
        align-items: center;
        padding-block: 0.75rem 1rem;
        background: color-mix(in oklab, var(--background) 92%, transparent);
        backdrop-filter: blur(12px);
      }

      .search-input {
        min-block-size: 2.75rem;
        padding-inline: 0.875rem;
        font-size: 1rem;
      }

      .search-status {
        color: var(--faint);
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
      }

      .glyph-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(6rem, 1fr));
        gap: 1px;
        margin: 0;
        padding: 1px;
        background: var(--border);
        list-style: none;
      }

      .glyph-card {
        display: grid;
        grid-template-rows: minmax(4rem, auto) auto auto;
        min-inline-size: 0;
        padding: 0.75rem;
        background: var(--surface);
      }

      .glyph-card[hidden] {
        display: none;
      }

      .glyph-char {
        align-self: center;
        overflow: hidden;
        font-size: 2rem;
        font-weight: var(--specimen-weight);
        line-height: 1.1;
        text-overflow: clip;
      }

      .glyph-code {
        color: var(--subtle);
        font-variant-numeric: tabular-nums;
      }

      .glyph-name {
        overflow: hidden;
        color: var(--faint);
        font-size: 0.625rem;
        line-height: 1rem;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .empty-state {
        padding-block: 3rem;
        color: var(--faint);
        font-size: 0.8125rem;
        text-align: center;
      }

      .empty-state[hidden] {
        display: none;
      }

      footer {
        display: grid;
        gap: 0.75rem;
        padding-block-start: 2rem;
        border-block-start: 1px solid var(--border);
        color: var(--faint);
        font-size: 0.75rem;
        line-height: 1.5;
      }

      @media (max-width: 36rem) {
        .shell {
          padding-block-start: 2rem;
        }

        .hero {
          padding-block-end: 3rem;
        }

        .kicker {
          margin-block-end: 2rem;
        }

        .font-meta {
          grid-template-columns: 1fr;
        }

        .font-meta > div:nth-child(odd),
        .font-meta > div:nth-child(even) {
          padding-inline: 0;
          border-inline-start: 0;
        }

        .font-meta > div + div {
          border-block-start: 1px solid var(--border);
        }

        .weight-control {
          top: 0.5rem;
          grid-template-columns: auto minmax(5rem, 1fr) 3ch;
          gap: 0.75rem;
        }

        .control-copy span {
          display: none;
        }

        section {
          padding-block-end: 4rem;
        }

        .section-heading::before {
          inline-size: 2.5rem;
        }

        .prose-sample,
        .weight-row,
        .raster-row {
          grid-template-columns: 1fr;
          gap: 0.375rem;
        }

        .raster-contrast {
          grid-template-columns: 1fr;
        }

        .search-bar {
          top: 5rem;
          grid-template-columns: 1fr;
          gap: 0.5rem;
        }

        .glyph-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        textarea,
        .search-input {
          font-size: 1rem;
        }
      }

      @media (prefers-reduced-motion: reduce) {
        html {
          scroll-behavior: auto;
        }
      }

      @media print {
        .weight-control,
        .search-bar {
          position: static;
          box-shadow: none;
          backdrop-filter: none;
        }

        .shell {
          inline-size: 100%;
          max-inline-size: none;
        }
      }
    </style>
  </head>
  <body>
    <main class="shell">
      <header class="hero">
        <p class="kicker">Fractal / Type system / 01</p>
        <h1 class="variable">Fractal MONO</h1>
        <p class="dek variable">
          A working specimen for reading, writing, and code — with the current
          variable build embedded directly into this file.
        </p>
        <dl class="font-meta" aria-label="Font metadata">
          <div>
            <dt class="meta-label">Build</dt>
            <dd class="meta-value">__VERSION__</dd>
          </div>
          <div>
            <dt class="meta-label">Axis</dt>
            <dd class="meta-value">wght __MIN_WEIGHT__–__MAX_WEIGHT__</dd>
          </div>
          <div>
            <dt class="meta-label">Glyphs</dt>
            <dd class="meta-value">__GLYPH_COUNT__</dd>
          </div>
          <div>
            <dt class="meta-label">Encoded characters</dt>
            <dd class="meta-value">__CHARACTER_COUNT__</dd>
          </div>
        </dl>
      </header>

      <div class="weight-control">
        <label class="control-copy" for="weight">Weight <span>axis</span></label>
        <input id="weight" type="range" min="__MIN_WEIGHT__" max="__MAX_WEIGHT__" step="1" value="__DEFAULT_WEIGHT__" />
        <output id="weight-output" for="weight">__DEFAULT_WEIGHT__</output>
        <label class="operator-toggle" for="programming-ligatures">
          <input id="programming-ligatures" type="checkbox" />
          Optional programming ligatures (<code>dlig</code>)
        </label>
      </div>

      <section aria-labelledby="testers-heading">
        <h2 class="section-heading" id="testers-heading">
          Type testers
          <span class="section-number">01</span>
        </h2>
        <div class="tester-grid">
          <label class="tester" for="plain-tester">
            <span class="tester-label">Plain text</span>
            <textarea class="variable" id="plain-tester" spellcheck="true">Clarity is not the absence of character. It is the careful arrangement of details so a reader can move through an idea without friction.</textarea>
          </label>
          <label class="tester code-tester" for="code-tester">
            <span class="tester-label">Code / JavaScript</span>
            <textarea class="variable" id="code-tester" spellcheck="false">const ready = status === "complete";
const next = ready ? "publish" : "review";

if (input !== null && count >= 3) {
  queue.map((item) => item.id);
}</textarea>
          </label>
        </div>
      </section>

      <section aria-labelledby="paragraphs-heading">
        <h2 class="section-heading" id="paragraphs-heading">
          Paragraphs
          <span class="section-number">02</span>
        </h2>
        <div class="prose-samples">
          <article class="prose-sample">
            <span class="weight-label">Regular / 400</span>
            <p class="variable">
              Good tools disappear into the work. Their controls stay close at
              hand, their states remain legible, and their details reward
              attention without asking for it. A coding typeface has the same
              task: preserve rhythm at speed, then hold up under inspection.
            </p>
          </article>
          <article class="prose-sample">
            <span class="weight-label">Mixed text</span>
            <p class="variable">
              At 09:42 the build moved from queued → running → complete. The
              result was 1,363 encoded characters, one continuous weight axis,
              and source-legible sequences such as ===, !==, &gt;=, and &lt;/&gt;.
              Every joined drawing remains available as an optional feature.
            </p>
          </article>
        </div>
      </section>

      <section aria-labelledby="weights-heading">
        <h2 class="section-heading" id="weights-heading">
          Weight range
          <span class="section-number">03</span>
        </h2>
        <div class="weight-list">
          <div class="weight-row"><span class="weight-label">100 / Thin</span><p style="font-weight: 100">Human systems, clearly expressed.</p></div>
          <div class="weight-row"><span class="weight-label">200 / Extra light</span><p style="font-weight: 200">Human systems, clearly expressed.</p></div>
          <div class="weight-row"><span class="weight-label">300 / Light</span><p style="font-weight: 300">Human systems, clearly expressed.</p></div>
          <div class="weight-row"><span class="weight-label">400 / Regular</span><p style="font-weight: 400">Human systems, clearly expressed.</p></div>
          <div class="weight-row"><span class="weight-label">450 / Book</span><p style="font-weight: 450">Human systems, clearly expressed.</p></div>
          <div class="weight-row"><span class="weight-label">500 / Medium</span><p style="font-weight: 500">Human systems, clearly expressed.</p></div>
          <div class="weight-row"><span class="weight-label">600 / Semi bold</span><p style="font-weight: 600">Human systems, clearly expressed.</p></div>
          <div class="weight-row"><span class="weight-label">700 / Bold</span><p style="font-weight: 700">Human systems, clearly expressed.</p></div>
          <div class="weight-row"><span class="weight-label">800 / Extra bold</span><p style="font-weight: 800">Human systems, clearly expressed.</p></div>
        </div>
      </section>

      <section aria-labelledby="code-heading">
        <h2 class="section-heading" id="code-heading">
          Code in context
          <span class="section-number">04</span>
        </h2>
        <div class="code-stack">
          <article class="code-card">
            <header class="code-card-header"><span>status-card.html</span><span>HTML</span></header>
            <pre class="variable"><code><span class="token-tag">&lt;article</span> <span class="token-attr">data-state</span>=<span class="token-string">"ready"</span><span class="token-tag">&gt;</span>
  <span class="token-tag">&lt;h1&gt;</span>System status<span class="token-tag">&lt;/h1&gt;</span>
  <span class="token-tag">&lt;p&gt;</span>queued -&gt; running -&gt; complete<span class="token-tag">&lt;/p&gt;</span>
<span class="token-tag">&lt;/article&gt;</span></code></pre>
          </article>
          <article class="code-card">
            <header class="code-card-header"><span>status-card.css</span><span>CSS</span></header>
            <pre class="variable"><code><span class="token-tag">.status-card</span> {
  display: grid;
  grid-template-columns: <span class="token-value">auto 1fr</span>;
  gap: <span class="token-number">0.75rem</span>;
  border: <span class="token-number">1px</span> solid <span class="token-value">color-mix(in oklab, currentColor 8%, transparent)</span>;
}

<span class="token-tag">.status-card[data-state="ready"]</span> {
  color: <span class="token-value">oklch(0.48 0.14 148)</span>;
}</code></pre>
          </article>
        </div>
      </section>

      <section aria-labelledby="raster-heading">
        <h2 class="section-heading" id="raster-heading">
          Rasterisation proof
          <span class="section-number">05</span>
        </h2>
        <p class="raster-intro">A browser-size proof for the unhinted outlines. It tests repeated stems, bowls, diagonals, punctuation, and code at ordinary interface sizes rather than judging only from display text.</p>
        <div class="raster-grid">
          <article class="raster-row" data-raster-size="11"><span class="weight-label">11px / 400</span><div class="raster-copy" style="font-size:11px;font-weight:400"><p>Hamburgefontsiv · minimum rhythm · 0O 1Il rn m</p><p class="raster-code">if (input !== null) return status === "ready";</p></div></article>
          <article class="raster-row" data-raster-size="12"><span class="weight-label">12px / 400</span><div class="raster-copy" style="font-size:12px;font-weight:400"><p>Hamburgefontsiv · minimum rhythm · 0O 1Il rn m</p><p class="raster-code">if (input !== null) return status === "ready";</p></div></article>
          <article class="raster-row" data-raster-size="13"><span class="weight-label">13px / 400</span><div class="raster-copy" style="font-size:13px;font-weight:400"><p>Hamburgefontsiv · minimum rhythm · 0O 1Il rn m</p><p class="raster-code">if (input !== null) return status === "ready";</p></div></article>
          <article class="raster-row" data-raster-size="14"><span class="weight-label">14px / 400</span><div class="raster-copy" style="font-size:14px;font-weight:400"><p>Hamburgefontsiv · minimum rhythm · 0O 1Il rn m</p><p class="raster-code">if (input !== null) return status === "ready";</p></div></article>
          <article class="raster-row" data-raster-size="16"><span class="weight-label">16px / 400</span><div class="raster-copy" style="font-size:16px;font-weight:400"><p>Hamburgefontsiv · minimum rhythm · 0O 1Il rn m</p><p class="raster-code">if (input !== null) return status === "ready";</p></div></article>
          <article class="raster-row" data-raster-size="14-600"><span class="weight-label">14px / 600</span><div class="raster-copy" style="font-size:14px;font-weight:600"><p>Hamburgefontsiv · minimum rhythm · 0O 1Il rn m</p><p class="raster-code">if (input !== null) return status === "ready";</p></div></article>
        </div>
        <div class="raster-contrast" aria-label="Light and dark rasterisation comparison">
          <div>Light UI / 13px<br />telltale toolkit network rarer<br />&lt;main data-state="ready"&gt;</div>
          <div class="dark">Dark UI / 13px<br />telltale toolkit network rarer<br />&lt;main data-state="ready"&gt;</div>
        </div>
        <p class="raster-note">Fractal Mono intentionally has no retained TrueType bytecode after its geometry changes. Its font metadata requests grayscale and symmetric smoothing without grid fitting, so the rasterisation instruction matches the outlines.</p>
      </section>

      <section aria-labelledby="core-heading">
        <h2 class="section-heading" id="core-heading">
          Core character set
          <span class="section-number">06</span>
        </h2>
        <div class="core-set variable">
          <p class="core-line">telltale · toolkit · network · rarer · error · retry</p>
          <p class="core-line">ABCDEFGHIJKLMNOPQRSTUVWXYZ</p>
          <p class="core-line">abcdefghijklmnopqrstuvwxyz</p>
          <p class="core-line">0123456789 0O 1Il 5S 8B</p>
          <p class="core-line">! &quot; # $ % &amp; ' ( ) * + , - . / : ; &lt; = &gt; ? @ [ \ ] ^ _ ` { | } ~</p>
          <p class="core-line">ÀÁÂÃÄÅ Æ Ç ÈÉÊË ÌÍÎÏ Ñ ÒÓÔÕÖ Ø Œ ÙÚÛÜ Ý Ÿ</p>
          <p class="core-line">àáâãäå æ ç èéêë ìíîï ñ òóôõö ø œ ùúûü ý ÿ</p>
          <p class="core-note">Operator checks: -&gt; =&gt; &lt;- &lt;=&gt; == === != !== &lt;= &gt;= &amp;&amp; || :: ... // /* */ &lt;tag&gt; &lt;/tag&gt;</p>
        </div>
      </section>

      <section aria-labelledby="repertoire-heading">
        <h2 class="section-heading" id="repertoire-heading">
          Complete repertoire
          <span class="section-number">07</span>
        </h2>
        <details open>
          <summary>
            All __CHARACTER_COUNT__ encoded characters
            <span class="section-number">cmap</span>
          </summary>
          <div class="search-bar">
            <label>
              <span class="tester-label" style="position:absolute;inline-size:1px;block-size:1px;overflow:hidden;clip:rect(0 0 0 0)">Filter characters</span>
              <input class="search-input" id="character-search" type="search" placeholder="Filter by character name or U+ code" autocomplete="off" />
            </label>
            <output class="search-status" id="character-count" aria-live="polite">__CHARACTER_COUNT__ / __CHARACTER_COUNT__</output>
          </div>
          <ul class="glyph-grid" id="glyph-grid">
__GLYPH_TILES__
          </ul>
          <p class="empty-state" id="empty-state" hidden>No encoded characters match that filter.</p>
        </details>
      </section>

      <footer>
        <p>Self-contained specimen · embedded WOFF2 · no external requests</p>
        <p>Character data read from the font’s Unicode cmap with open-source FontTools. Layout references the current Fractal article kit; browser behaviour verified with Playwright.</p>
      </footer>
    </main>

    <script>
      const root = document.documentElement;
      const weight = document.querySelector("#weight");
      const weightOutput = document.querySelector("#weight-output");
      const programmingLigatures = document.querySelector("#programming-ligatures");
      const search = document.querySelector("#character-search");
      const cards = [...document.querySelectorAll(".glyph-card")];
      const characterCount = document.querySelector("#character-count");
      const emptyState = document.querySelector("#empty-state");
      const numberFormat = new Intl.NumberFormat("en-US");

      function updateWeight() {
        const value = Number(weight.value);
        root.style.setProperty("--specimen-weight", value);
        weightOutput.value = String(value);
        weightOutput.textContent = String(value);
        weight.setAttribute("aria-valuetext", `${value} font weight`);
      }

      function filterCharacters() {
        const query = search.value.trim().toLowerCase();
        let visible = 0;
        for (const card of cards) {
          const matches = query === "" || card.dataset.search.includes(query);
          card.hidden = !matches;
          if (matches) visible += 1;
        }
        const countLabel = `${numberFormat.format(visible)} / ${numberFormat.format(cards.length)}`;
        characterCount.value = countLabel;
        characterCount.textContent = countLabel;
        emptyState.hidden = visible !== 0;
      }

      weight.addEventListener("input", updateWeight);
      programmingLigatures.addEventListener("change", () => {
        root.classList.toggle("programming-ligatures", programmingLigatures.checked);
      });
      search.addEventListener("input", filterCharacters);
      updateWeight();
      filterCharacters();
    </script>
  </body>
</html>
'''


def main() -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    font = TTFont(VARIABLE_TTF)
    cmap = font.getBestCmap()
    axis = next(axis for axis in font["fvar"].axes if axis.axisTag == "wght")
    version = name_value(font, 5, "Version unknown")
    font_data = base64.b64encode(VARIABLE_WOFF2.read_bytes()).decode("ascii")

    replacements = {
        "__FONT_DATA__": font_data,
        "__VERSION__": html.escape(version),
        "__MIN_WEIGHT__": str(int(axis.minValue)),
        "__DEFAULT_WEIGHT__": str(int(axis.defaultValue)),
        "__MAX_WEIGHT__": str(int(axis.maxValue)),
        "__GLYPH_COUNT__": f"{font['maxp'].numGlyphs:,}",
        "__CHARACTER_COUNT__": f"{len(cmap):,}",
        "__GLYPH_TILES__": glyph_tiles(cmap),
    }

    artifact = TEMPLATE
    for marker, value in replacements.items():
        artifact = artifact.replace(marker, value)

    if "__" in artifact:
        unresolved = sorted({part.split("__", 1)[0] for part in artifact.split("__")[1::2]})
        raise RuntimeError(f"Unresolved template marker: {unresolved}")

    OUTPUT.write_text(artifact, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"Characters: {len(cmap):,}; glyphs: {font['maxp'].numGlyphs:,}; axis: {int(axis.minValue)}–{int(axis.maxValue)}")


if __name__ == "__main__":
    main()
