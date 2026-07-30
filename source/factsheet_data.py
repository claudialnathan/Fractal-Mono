#!/usr/bin/env python3
"""Generate the verified data consumed by the public CLN Mono specimen."""

from __future__ import annotations

import argparse
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from fontTools import unicodedata as font_unicode
from fontTools.ttLib import TTFont


PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_FONT = PROJECT / "fonts" / "desktop" / "CLNMono-Variable.ttf"
DEFAULT_OUTPUT = PROJECT / "specimen-data.js"
BUILD_REPORT = PROJECT / "build-report.json"
LANGUAGE_SUPPORT = PROJECT / "source" / "language-support.json"


FEATURE_DETAILS: dict[str, dict[str, str]] = {
    "aalt": {
        "name": "Access all alternates",
        "sample": "l t g j K k r u y",
        "status": "optional",
        "description": "Exposes the family’s alternate drawings through one feature.",
    },
    "calt": {
        "name": "Contextual alternates",
        "sample": "08:42  A:B",
        "status": "default",
        "description": "Centers punctuation in suitable contexts. Programming ligatures are not part of calt.",
    },
    "case": {
        "name": "Case-sensitive forms",
        "sample": "(H:H) [A:B]",
        "status": "optional",
        "description": "Raises punctuation and accents for all-cap settings.",
    },
    "ccmp": {
        "name": "Glyph composition/decomposition",
        "sample": "ä ǵ ñ",
        "status": "automatic",
        "description": "Builds or decomposes accented forms as required by the shaping engine.",
    },
    "cv01": {
        "name": "Alternate lowercase l",
        "sample": "l ĺ ľ ļ ŀ ł",
        "status": "optional",
        "description": "Switches the lowercase l family to its alternate construction.",
    },
    "cv02": {
        "name": "Alternate lowercase t",
        "sample": "t ŧ ť ţ ț",
        "status": "optional",
        "description": "Switches the lowercase t family to its alternate construction.",
    },
    "cv03": {
        "name": "Alternate lowercase g",
        "sample": "g ǵ ğ ǧ ĝ ģ ġ",
        "status": "optional",
        "description": "Switches the lowercase g family to its alternate construction.",
    },
    "cv04": {
        "name": "Alternate lowercase j",
        "sample": "j ȷ ĵ ј",
        "status": "optional",
        "description": "Switches Latin and Cyrillic j forms to their alternate construction.",
    },
    "cv05": {
        "name": "Closed lowercase l",
        "sample": "l ĺ ľ ļ ŀ ł",
        "status": "optional",
        "description": "Uses the closed alternate for lowercase l and its accented forms.",
    },
    "cv06": {
        "name": "Alternate lowercase m",
        "sample": "minimum mm",
        "status": "optional",
        "description": "Switches lowercase m to its alternate construction.",
    },
    "cv07": {
        "name": "Alternate W and w",
        "sample": "Ww Wẃ Wŵ Wẅ Wẁ",
        "status": "optional",
        "description": "Switches uppercase and lowercase W families to alternate joins.",
    },
    "cv08": {
        "name": "Alternate K and k",
        "sample": "Kk Ķķ Жж Κκ",
        "status": "optional",
        "description": "Switches Latin, Cyrillic, and Greek K-related forms.",
    },
    "cv09": {
        "name": "Alternate lowercase f",
        "sample": "f ff ffi",
        "status": "optional",
        "description": "Switches lowercase f to its alternate construction.",
    },
    "cv10": {
        "name": "Alternate lowercase r",
        "sample": "r ŕ ř ŗ",
        "status": "optional",
        "description": "Switches lowercase r and its accented forms.",
    },
    "cv11": {
        "name": "Alternate y-family forms",
        "sample": "y ý ŷ ÿ у γ λ",
        "status": "optional",
        "description": "Switches Latin y and related Cyrillic and Greek forms.",
    },
    "cv12": {
        "name": "Alternate lowercase u",
        "sample": "u ú ŭ û ü ư",
        "status": "optional",
        "description": "Switches lowercase u and its accented forms.",
    },
    "cv14": {
        "name": "Alternate currency forms",
        "sample": "$ ¢ <$ $>",
        "status": "optional",
        "description": "Switches dollar and cent forms, including matching optional ligatures.",
    },
    "cv15": {
        "name": "Alternate ampersand",
        "sample": "& && &&& &=",
        "status": "optional",
        "description": "Switches the ampersand and its optional ligature forms.",
    },
    "cv16": {
        "name": "Alternate uppercase Q",
        "sample": "Q QUEUE",
        "status": "optional",
        "description": "Switches uppercase Q to its alternate tail.",
    },
    "cv17": {
        "name": "Closed lowercase f",
        "sample": "f off after",
        "status": "optional",
        "description": "Uses the closed alternate for lowercase f.",
    },
    "cv18": {
        "name": "Alternate 2, 6, and 9",
        "sample": "2 6 9 ² ⁶ ⁹ ₂ ₆ ₉",
        "status": "optional",
        "description": "Switches 2, 6, and 9 across baseline, superior, and inferior forms.",
    },
    "cv19": {
        "name": "Alternate 8",
        "sample": "8 ⁸ ₈",
        "status": "optional",
        "description": "Switches 8 across baseline, superior, and inferior forms.",
    },
    "cv20": {
        "name": "Alternate 5",
        "sample": "5 ⁵ ₅",
        "status": "optional",
        "description": "Switches 5 across baseline, superior, and inferior forms.",
    },
    "cv99": {
        "name": "Alternate Cyrillic Es",
        "sample": "С с",
        "status": "optional",
        "description": "Switches uppercase and lowercase Cyrillic Es.",
    },
    "dlig": {
        "name": "Discretionary ligatures",
        "sample": "=== !== => -> </> && ||",
        "status": "optional",
        "description": "Enables 150 programming drawings. All programming sequences stay literal by default.",
    },
    "frac": {
        "name": "Fractions",
        "sample": "1/2 3/4 11/16",
        "status": "optional",
        "description": "Builds arbitrary diagonal fractions from numerator and denominator forms.",
    },
    "locl": {
        "name": "Localized forms",
        "sample": "Ş ş Ț ț Í í",
        "status": "automatic",
        "description": "Selects language-appropriate forms for supported Latin language systems.",
    },
    "mark": {
        "name": "Mark positioning",
        "sample": "á g̈ ñ",
        "status": "automatic",
        "description": "Positions combining marks on their base glyphs.",
    },
    "mkmk": {
        "name": "Mark-to-mark positioning",
        "sample": "ä́ ṍ",
        "status": "automatic",
        "description": "Positions stacked combining marks relative to one another.",
    },
    "ordn": {
        "name": "Ordinals",
        "sample": "1st 2nd 3rd No.",
        "status": "optional",
        "description": "Uses ordinal and number-sign forms in supported contexts.",
    },
    "sinf": {
        "name": "Scientific inferiors",
        "sample": "H2O x10",
        "status": "optional",
        "description": "Replaces baseline numerals with scientific inferior forms.",
    },
    "ss01": {
        "name": "Classic construction",
        "sample": "K k f l r u y",
        "status": "optional",
        "description": "Applies the font’s named classic-construction alternate set.",
    },
    "ss02": {
        "name": "Closed construction",
        "sample": "W w f l m t y",
        "status": "optional",
        "description": "Applies the font’s named closed-construction alternate set.",
    },
    "ss03": {
        "name": "Dotless counters",
        "sample": "O o 0",
        "status": "optional",
        "description": "Removes the default square centre dots without changing the surrounding bowls.",
    },
    "ss19": {
        "name": "Broken equals ligatures",
        "sample": "!= !== == ===",
        "status": "optional",
        "description": "Uses broken-bar equality drawings when optional programming ligatures are active.",
    },
    "ss20": {
        "name": "Raised bar f",
        "sample": "f ff after",
        "status": "optional",
        "description": "Raises the crossbar of lowercase f.",
    },
    "subs": {
        "name": "Subscript",
        "sample": "H2O 0123456789",
        "status": "optional",
        "description": "Replaces baseline numerals with typographic subscript forms.",
    },
    "sups": {
        "name": "Superscript",
        "sample": "x2 0123456789+",
        "status": "optional",
        "description": "Replaces baseline numerals and plus with typographic superscript forms.",
    },
    "zero": {
        "name": "Alternate zero",
        "sample": "0 O o 00:00",
        "status": "optional",
        "description": "Switches the default dotted zero to the alternate disambiguated form.",
    },
}


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


def name_value(font: TTFont, name_id: int, default: str = "") -> str:
    return font["name"].getDebugName(name_id) or default


def display_character(codepoint: int) -> str:
    character = chr(codepoint)
    category = unicodedata.category(character)
    if codepoint in INVISIBLE_LABELS:
        return INVISIBLE_LABELS[codepoint]
    if category.startswith("M"):
        return f"◌{character}"
    if category.startswith("C") or character.isspace():
        return "CTRL"
    return character


def feature_tags(font: TTFont) -> list[str]:
    tags: set[str] = set()
    for table_tag in ("GSUB", "GPOS"):
        if table_tag not in font:
            continue
        feature_list = font[table_tag].table.FeatureList
        if feature_list:
            tags.update(record.FeatureTag for record in feature_list.FeatureRecord)
    return sorted(tags)


def lookup_count(font: TTFont, tag: str) -> int:
    lookups: set[int] = set()
    for table_tag in ("GSUB", "GPOS"):
        if table_tag not in font:
            continue
        feature_list = font[table_tag].table.FeatureList
        if not feature_list:
            continue
        for record in feature_list.FeatureRecord:
            if record.FeatureTag == tag:
                lookups.update(record.Feature.LookupListIndex)
    return len(lookups)


def character_data(font: TTFont) -> tuple[list[dict[str, Any]], Counter[str], Counter[str]]:
    characters: list[dict[str, Any]] = []
    scripts: Counter[str] = Counter()
    blocks: Counter[str] = Counter()
    for codepoint, glyph_name in sorted(font.getBestCmap().items()):
        character = chr(codepoint)
        script = font_unicode.script_name(font_unicode.script(character))
        block = font_unicode.block(character)
        category = unicodedata.category(character)
        scripts[script] += 1
        blocks[block] += 1
        characters.append(
            {
                "character": character,
                "display": display_character(codepoint),
                "codepoint": f"U+{codepoint:04X}",
                "name": unicodedata.name(character, "Unnamed character").title(),
                "glyph": glyph_name,
                "script": script,
                "block": block,
                "category": category,
            }
        )
    return characters, scripts, blocks


def generate(font_path: Path) -> dict[str, Any]:
    font = TTFont(font_path)
    cmap = font.getBestCmap()
    encoded_glyphs = set(cmap.values())
    unencoded_glyphs = [
        glyph_name
        for glyph_name in font.getGlyphOrder()
        if glyph_name not in encoded_glyphs
    ]
    characters, scripts, blocks = character_data(font)
    os2 = font["OS/2"]
    head = font["head"]
    hhea = font["hhea"]
    post = font["post"]
    fvar = font["fvar"]
    axes = {
        item.axisTag: item
        for item in fvar.axes
    }
    tags = feature_tags(font)
    report = json.loads(BUILD_REPORT.read_text())
    languages = json.loads(LANGUAGE_SUPPORT.read_text())
    table_sizes = {
        tag: record.length
        for tag, record in sorted(font.reader.tables.items())
    }

    features = []
    for tag in tags:
        detail = FEATURE_DETAILS.get(
            tag,
            {
                "name": tag,
                "sample": tag,
                "status": "optional",
                "description": "OpenType feature present in the font.",
            },
        )
        features.append(
            {
                "tag": tag,
                **detail,
                "lookups": lookup_count(font, tag),
            }
        )

    files = []
    for path, details in report["files"].items():
        suffix = Path(path).suffix.removeprefix(".").upper()
        files.append(
            {
                "path": path,
                "format": suffix,
                "bytes": details["bytes"],
                "sha256": details["sha256"],
                "kind": "Desktop" if "/desktop/" in path else "Web",
                "variable": "Variable" in path,
            }
        )

    return {
        "family": name_value(font, 1, "CLN Mono"),
        "version": name_value(font, 5, "Version 1.305"),
        "postscriptName": name_value(font, 6, "CLNMono-Regular"),
        "designer": name_value(font, 9),
        "license": name_value(font, 13),
        "licenseUrl": name_value(font, 14),
        "glyphCount": font["maxp"].numGlyphs,
        "encodedCount": len(cmap),
        "unencodedCount": len(unencoded_glyphs),
        "unencodedGlyphs": unencoded_glyphs,
        "axes": {
            tag: {
                "tag": axis.axisTag,
                "name": name_value(font, axis.axisNameID, tag),
                "min": int(axis.minValue),
                "default": int(axis.defaultValue),
                "max": int(axis.maxValue),
            }
            for tag, axis in axes.items()
        },
        "instances": [
            {
                "name": name_value(font, instance.subfamilyNameID),
                "value": int(instance.coordinates["wght"]),
            }
            for instance in fvar.instances
        ],
        "metrics": {
            "unitsPerEm": head.unitsPerEm,
            "advanceWidth": os2.xAvgCharWidth,
            "capHeight": os2.sCapHeight,
            "xHeight": os2.sxHeight,
            "typoAscender": os2.sTypoAscender,
            "typoDescender": os2.sTypoDescender,
            "typoLineGap": os2.sTypoLineGap,
            "hheaAscender": hhea.ascent,
            "hheaDescender": hhea.descent,
            "hheaLineGap": hhea.lineGap,
            "winAscender": os2.usWinAscent,
            "winDescender": os2.usWinDescent,
            "yMin": head.yMin,
            "yMax": head.yMax,
            "underlinePosition": post.underlinePosition,
            "underlineThickness": post.underlineThickness,
            "fixedPitch": bool(post.isFixedPitch),
            "useTypoMetrics": bool(os2.fsSelection & (1 << 7)),
        },
        "features": features,
        "featureCount": len(tags),
        "languages": languages,
        "languageSummary": dict(Counter(row["script"] for row in languages)),
        "languageCount": len(languages),
        "speakerEstimate": sum(row.get("speakers") or 0 for row in languages),
        "characters": characters,
        "scriptSummary": dict(scripts.most_common()),
        "blockSummary": dict(blocks.most_common()),
        "tableSizes": table_sizes,
        "files": files,
        "build": report,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    data = generate(args.font)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    args.output.write_text(f"window.CLN_MONO_DATA={payload};\n")
    print(
        f"Wrote {args.output} with {data['encodedCount']:,} characters, "
        f"{data['featureCount']} OpenType features, and "
        f"{data['languageCount']} Hyperglot language profiles"
    )


if __name__ == "__main__":
    main()
