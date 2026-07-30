#!/usr/bin/env python3
"""Build the Fractal Mono release family from its configured OFL source master."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from copy import deepcopy
from functools import lru_cache, partial
from pathlib import Path

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor
from fontTools.otlLib.builder import buildStatTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables._f_v_a_r import NamedInstance
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib import build as build_variable
from fontTools.varLib.instancer import AxisTriple, instantiateVariableFont

from fractal_geometry import (
    CUSTOM_GLYPH_NAMES,
    DEFAULT_OPSZ,
    DISPLAY_OPSZ,
    PRESERVED_MASTER_GLYPH_NAMES,
    SQUARE_MARK_NAMES,
    TEXT_OPSZ,
    apply_optical_geometry,
    install_preserved_master_glyphs,
    install_reference_glyphs,
    install_square_ellipsis,
    install_square_marks,
    fit_glyphs_to_cell,
    offset_glyph_stable,
)
import fitting
import key_symbols
import stroke_system
from version import ARCHIVE_NAME, PACKAGE_VERSION, VERSION


FAMILY = "Fractal Mono"
VENDOR_ID = "FRCT"

UPM = 1000
ADVANCE = 579

# Vertical proportions are tuned for a full coding-size lowercase inside a
# compact 1000 UPM design. The remap is piecewise so the lowercase and cap
# bands land on their targets independently.
SOURCE_X_HEIGHT = 550
SOURCE_CAP_HEIGHT = 730
CAP_HEIGHT = 680
X_HEIGHT = 528
LOWERCASE_ASCENDER_HEIGHT = 728
LOWER_ZONE_SCALE = X_HEIGHT / SOURCE_X_HEIGHT
UPPER_ZONE_SCALE = (CAP_HEIGHT - X_HEIGHT) / (SOURCE_CAP_HEIGHT - SOURCE_X_HEIGHT)
# The 728-unit lowercase ascender adds apparent size at small coding sizes
# without enlarging the x-height, caps, or family-wide line metrics. The custom
# k retains its established proportions; this target applies to b/d/f/h/l and the
# shared square dot used by i/j and dotted letters.
LOWERCASE_ASCENDER_CHARS = frozenset("bdfhl")
# Lowercase descenders deepen to -195 without stretching far enough to kink
# baseline-crossing curves.
DESCENDER_SCALE = 195 / 180

# Source-master coordinate used to produce Fractal Mono's ~80-unit Regular stems.
SOURCE_REGULAR_WEIGHT = 310
TYPO_ASCENDER = 950
TYPO_DESCENDER = -250
# The clipping box, measured from actual ink across the whole design space rather
# than set to the em box. Box-drawing glyphs deliberately pass the em box so a
# vertical rule joins the rows above and below, and legacy Windows rendering clips
# to these two fields. USE_TYPO_METRICS is set, so line spacing still comes from
# the typo metrics everywhere that honours it.
WIN_ASCENDER = 1009
WIN_DESCENDER = 384

# Custom-glyph stem widths at the wght axis extremes and default.
STEMS_LOWER = (50, 80, 150)
STEM_ANCHORS = STEMS_LOWER
WEIGHT_MASTER_DESIGN_LOCATIONS = (100.0, 400.0, 461.0, 620.0, 800.0)
WEIGHT_AXIS_SAMPLES = (100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800)
# Filled during the build with the glyphs the cell fit had to recentre, so the
# regression gate knows which outlines were expected to move.
CELL_FITTED: set[str] = set()
# Glyphs whose sidebearings the fitting pass moved; recorded so the regression gate
# knows their outlines were expected to change.
REFITTED: set[str] = set()

# v1.240's contour-local tension experiment moved quadratic controls without
# moving their implied on-curve joins. At display sizes this produced small
# reversals: dents across bowls and shoulders, hooks at diagonal joins, and
# pinches in M/N/Q/V/W. v1.250 deliberately retains the established metrics,
# fitting, custom k/r/t/w drawings, and zone remap while restoring the clean
# established curve geometry for every letter and numeral.

# The zero's centre dot supplies one interpolation-compatible contour for O and
# a proportionally smaller version for o. The defaults stay dotted.
LOWERCASE_O_DOT_SCALE = 0.82

# Fractal Mono's lowercase-r construction. Its compatible quadratic point
# order supports three variable masters while the contour expands along local
# normals to follow the family's 50/80/150 stem system.
FRACTAL_R_REFERENCE_ADVANCE = 996
FRACTAL_R_REFERENCE_TOP = 1007
FRACTAL_R_REFERENCE_STEM = 138
FRACTAL_R_POINTS = (
    (182, 998),
    (292, 998),
    (312, 909),
    (398, 995),
    (538, 1001),
    (687, 1007),
    (769, 932),
    (813, 891),
    (867, 816),
    (895, 754),
    (787, 693),
    (780, 704),
    (751, 758),
    (724, 795),
    (700, 818),
    (667, 849),
    (562, 876),
    (514, 870),
    (497, 868),
    (472, 863),
    (429, 846),
    (397, 823),
    (360, 778),
    (336, 719),
    (320, 630),
    (320, 576),
    (320, 0),
    (182, 0),
)

# Compact construction diagrams for Fractal Mono's lowercase t, k, and w. The
# coordinates describe the Regular silhouettes, then expand along
# contour normals to the family's 50/80/150 stem system.
FRACTAL_DRAWING_ADVANCE = 600
FRACTAL_DRAWING_X_HEIGHT = 500
FRACTAL_DRAWING_CAP_HEIGHT = 700
FRACTAL_DRAWING_STEM = 95
FRACTAL_T_CONTOURS = (
    (
        (335, 0, True),
        (280, 0, False),
        (224, 53, False),
        (224, 108, True),
        (224, 422, True),
        (62, 422, True),
        (62, 500, True),
        (224, 500, True),
        (224, 662, True),
        (319, 662, True),
        (319, 500, True),
        (502, 500, True),
        (502, 422, True),
        (319, 422, True),
        (319, 127, True),
        (319, 99, False),
        (338, 80, False),
        (366, 80, True),
        (524, 80, True),
        (524, 0, True),
    ),
)
FRACTAL_K_CONTOURS = (
    ((102, 0, True), (102, 700, True), (197, 700, True), (197, 0, True)),
    ((163, 130, True), (135, 220, True), (415, 500, True), (537, 500, True)),
    ((432, 0, True), (249, 264, True), (314, 333, True), (547, 0, True)),
)
FRACTAL_W_CONTOURS = (
    (
        (122, 0, True),
        (43, 500, True),
        (131, 500, True),
        (191, 47, True),
        (169, 47, True),
        (251, 388, True),
        (350, 388, True),
        (432, 46, True),
        (410, 46, True),
        (471, 500, True),
        (558, 500, True),
        (479, 0, True),
        (375, 0, True),
        (297, 317, True),
        (304, 317, True),
        (226, 0, True),
    ),
)

# Default glyphs replaced by the Fractal Mono character variants.
ALTERNATE_SWAPS = {"l": "l.cv01", "lslash": "lslash.cv01"}

# Every programming sequence remains source-legible by default. Joined drawings
# are exposed only through the explicit discretionary `dlig` feature. Genuine
# non-programming contextual alternates stay in `calt`.
EXPECTED_DISCRETIONARY_LIGATURE_LOOKUP_COUNT = 152
ALWAYS_LITERAL_LIGATURE_SEQUENCES = {"/\\", "\\/", "|||"}
DOTLESS_COUNTER_ALTERNATES = {
    "O": "O.dotless",
    "o": "o.dotless",
    "zero": "zero.dotless",
}

PROJECT = Path(__file__).resolve().parents[1]
BUILD = PROJECT / "build"
DESKTOP_DIR = PROJECT / "fonts" / "desktop"
WEB_DIR = PROJECT / "fonts" / "web"

VARIABLE_SOURCE = (
    PROJECT
    / "source"
    / "upstream"
    / "JetBrainsMono[wght].ttf"
)

INSTANCES = {
    100: "Thin",
    200: "ExtraLight",
    300: "Light",
    400: "Regular",
    450: "Book",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
    800: "ExtraBold",
}

# Optical fitting inside the fixed 579-unit cell. The values intentionally
# tune ink width, not advances, so code and tabular data remain aligned.
X_SCALE_BY_CHAR = {
    # Optical padding for wide, vertical-sided lowercase forms. l's flag and
    # foot previously crowded both cell edges; m only needs a subtle inset.
    "l": 0.87,
    "m": 0.97,
    "0": 1.04,
    "1": 0.82,
    "3": 0.95,
    "4": 1.05,
    "5": 0.97,
    "6": 0.98,
    "7": 0.94,
    "8": 0.97,
    "9": 0.98,
    "@": 0.96,
    "&": 0.92,
    "{": 0.80,
    "}": 0.80,
    "(": 0.90,
    ")": 0.90,
    "<": 0.88,
    ">": 0.88,
    "*": 0.94,
    "+": 0.92,
    "=": 1.08,
    "_": 0.88,
    "/": 0.96,
    "\\": 0.96,
    ".": 0.84,
    ",": 0.88,
    ":": 0.84,
    ";": 0.88,
}

# Shape-preserving cell translation for j. The custom k is drawn directly into
# its intended fit and needs no after-the-fact shift.
OPTICAL_X_SHIFT = {"j": 60}

# Per-glyph vertical optical corrections, applied after the zone remap.
Y_SPECIAL = {
    "@": (0.88, 300, 25),
    "*": (1.12, 340, 0),
    "_": (1.00, 0, -20),
    ".": (0.84, 70, 0),
    ",": (0.92, 70, 0),
    # Preserve their established tall punctuation character while bringing
    # both ends into the ascender-sized visual band: -106..764 -> -80..738.
    "/": (0.94, 329, 0),
    "\\": (0.94, 329, 0),
}

DESCENDER_BASE_NAMES = {"g", "j", "p", "q", "y", "mu", "micro", "thorn"}


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def best_character_map(font: TTFont) -> dict[str, str]:
    """Return glyph name -> a representative Unicode character."""
    result: dict[str, str] = {}
    for codepoint, glyph_name in font.getBestCmap().items():
        result.setdefault(glyph_name, chr(codepoint))
    return result


def representative_char(glyph_name: str, cmap: dict[str, str]) -> str | None:
    char = cmap.get(glyph_name)
    # Apply digit fitting to their dotted/slashed stylistic alternates too.
    for digit_name, digit_char in (
        ("zero", "0"),
        ("one", "1"),
        ("two", "2"),
        ("three", "3"),
        ("four", "4"),
        ("five", "5"),
        ("six", "6"),
        ("seven", "7"),
        ("eight", "8"),
        ("nine", "9"),
    ):
        if glyph_name == digit_name or glyph_name.startswith(f"{digit_name}."):
            return digit_char
    return char


def is_descender_glyph(glyph_name: str, glyph, char: str | None) -> bool:
    if glyph.numberOfContours == 0 or getattr(glyph, "yMin", 0) > -120:
        return False
    if char is not None and char.islower():
        return True
    parts = set(glyph_name.replace("_", ".").split("."))
    return bool(parts & DESCENDER_BASE_NAMES)


def zone_remap(
    y: float,
    descender: bool,
    upper_target: float = CAP_HEIGHT,
) -> float:
    if y <= 0:
        return y * (DESCENDER_SCALE if descender else LOWER_ZONE_SCALE)
    if y <= SOURCE_X_HEIGHT:
        return y * LOWER_ZONE_SCALE
    upper_scale = (upper_target - X_HEIGHT) / (
        SOURCE_CAP_HEIGHT - SOURCE_X_HEIGHT
    )
    return X_HEIGHT + (y - SOURCE_X_HEIGHT) * upper_scale


def zone_factor(
    y: float,
    descender: bool,
    upper_target: float = CAP_HEIGHT,
) -> float:
    if y <= 0:
        return DESCENDER_SCALE if descender else LOWER_ZONE_SCALE
    if y <= SOURCE_X_HEIGHT:
        return LOWER_ZONE_SCALE
    return (upper_target - X_HEIGHT) / (
        SOURCE_CAP_HEIGHT - SOURCE_X_HEIGHT
    )


def target_advance(source_advance: int) -> int:
    return ADVANCE if source_advance else 0


def ligature_sequence(font: TTFont, glyph_name: str) -> str | None:
    if ".liga" not in glyph_name or ".liga." in glyph_name:
        return None
    reverse_ascii = {
        mapped_name: chr(codepoint)
        for codepoint, mapped_name in font.getBestCmap().items()
        if 0x20 <= codepoint < 0x7F
    }
    tokens = glyph_name.split(".liga", 1)[0].split("_")
    if any(token not in reverse_ascii for token in tokens):
        return None
    return "".join(reverse_ascii[token] for token in tokens)


def contextual_lookup_references(lookup) -> set[int]:
    """Return child lookup indices used by a contextual GSUB lookup."""
    references: set[int] = set()
    for subtable in lookup.SubTable:
        lookup_type = lookup.LookupType
        if lookup_type == 7:  # ExtensionSubst
            lookup_type = subtable.ExtensionLookupType
            subtable = subtable.ExtSubTable

        rules = []
        if lookup_type == 6:  # ChainContextSubst
            if subtable.Format == 1:
                for rule_set in subtable.ChainSubRuleSet or []:
                    if rule_set:
                        rules.extend(rule_set.ChainSubRule or [])
            elif subtable.Format == 2:
                for rule_set in subtable.ChainSubClassSet or []:
                    if rule_set:
                        rules.extend(rule_set.ChainSubClassRule or [])
            elif subtable.Format == 3:
                rules = [subtable]
        elif lookup_type == 5:  # ContextSubst
            if subtable.Format == 1:
                for rule_set in subtable.SubRuleSet or []:
                    if rule_set:
                        rules.extend(rule_set.SubRule or [])
            elif subtable.Format == 2:
                for rule_set in subtable.SubClassSet or []:
                    if rule_set:
                        rules.extend(rule_set.SubClassRule or [])
            elif subtable.Format == 3:
                rules = [subtable]

        for rule in rules:
            for record in getattr(rule, "SubstLookupRecord", []) or []:
                references.add(record.LookupListIndex)
    return references


def direct_substitution_outputs(lookup) -> set[str]:
    outputs: set[str] = set()
    for subtable in lookup.SubTable:
        lookup_type = lookup.LookupType
        if lookup_type == 7:  # ExtensionSubst
            lookup_type = subtable.ExtensionLookupType
            subtable = subtable.ExtSubTable
        if lookup_type == 1:  # SingleSubst
            outputs.update((getattr(subtable, "mapping", {}) or {}).values())
        elif lookup_type == 4:  # LigatureSubst
            for ligatures in (getattr(subtable, "ligatures", {}) or {}).values():
                outputs.update(ligature.LigGlyph for ligature in ligatures)
    return outputs


def move_programming_ligatures_to_dlig(font: TTFont) -> list[str]:
    """Move every programming-ligature context from default `calt` to `dlig`."""
    gsub = font["GSUB"].table
    feature_records = list(gsub.FeatureList.FeatureRecord)
    assert all(record.FeatureTag != "dlig" for record in feature_records)

    sequences_by_glyph = {
        glyph_name: sequence
        for glyph_name in font.getGlyphOrder()
        if (sequence := ligature_sequence(font, glyph_name)) is not None
    }
    lookup_list = gsub.LookupList.Lookup
    calt_feature_indices = {
        index
        for index, record in enumerate(feature_records)
        if record.FeatureTag == "calt"
    }
    moved_lookup_indices: list[int] = []

    for feature_index in sorted(calt_feature_indices):
        feature = feature_records[feature_index].Feature
        retained = []
        for lookup_index in feature.LookupListIndex:
            outputs: set[str] = set()
            for child_index in contextual_lookup_references(lookup_list[lookup_index]):
                outputs.update(direct_substitution_outputs(lookup_list[child_index]))
            if any(".liga" in output for output in outputs):
                moved_lookup_indices.append(lookup_index)
            else:
                retained.append(lookup_index)
        feature.LookupListIndex = retained
        feature.LookupCount = len(retained)

    moved_lookup_indices = list(dict.fromkeys(moved_lookup_indices))
    assert len(moved_lookup_indices) == EXPECTED_DISCRETIONARY_LIGATURE_LOOKUP_COUNT, (
        len(moved_lookup_indices),
        moved_lookup_indices,
    )

    discretionary_record = otTables.FeatureRecord()
    discretionary_record.FeatureTag = "dlig"
    discretionary_record.Feature = otTables.Feature()
    discretionary_record.Feature.FeatureParams = None
    discretionary_record.Feature.LookupListIndex = moved_lookup_indices
    discretionary_record.Feature.LookupCount = len(moved_lookup_indices)

    indexed_records = list(enumerate(feature_records))
    indexed_records.append((None, discretionary_record))
    indexed_records.sort(key=lambda item: item[1].FeatureTag)
    old_to_new = {
        old_index: new_index
        for new_index, (old_index, _) in enumerate(indexed_records)
        if old_index is not None
    }
    dlig_index = next(
        new_index
        for new_index, (old_index, _) in enumerate(indexed_records)
        if old_index is None
    )

    for script_record in gsub.ScriptList.ScriptRecord:
        lang_systems = []
        if script_record.Script.DefaultLangSys is not None:
            lang_systems.append(script_record.Script.DefaultLangSys)
        lang_systems.extend(
            record.LangSys for record in script_record.Script.LangSysRecord
        )
        for lang_system in lang_systems:
            had_calt = any(
                feature_index in calt_feature_indices
                for feature_index in lang_system.FeatureIndex
            )
            lang_system.FeatureIndex = sorted(
                old_to_new[feature_index]
                for feature_index in lang_system.FeatureIndex
            )
            if had_calt:
                lang_system.FeatureIndex = sorted(
                    set(lang_system.FeatureIndex) | {dlig_index}
                )
            lang_system.FeatureCount = len(lang_system.FeatureIndex)
            if lang_system.ReqFeatureIndex != 0xFFFF:
                lang_system.ReqFeatureIndex = old_to_new[lang_system.ReqFeatureIndex]

    gsub.FeatureList.FeatureRecord = [record for _, record in indexed_records]
    gsub.FeatureList.FeatureCount = len(indexed_records)
    return sorted(sequences_by_glyph.values(), key=lambda value: (len(value), value))


def install_dotless_counter_glyphs(font: TTFont) -> None:
    """Copy O/o/zero without their final square-dot contour.

    The dotted drawings remain the encoded defaults. These copies are rebuilt
    in every optical master so they share the exact same bowls, fitting, and
    variation model as the defaults.
    """
    glyphs = font["glyf"]
    glyph_order = font.getGlyphOrder()
    for source_name, target_name in DOTLESS_COUNTER_ALTERNATES.items():
        source = glyphs[source_name]
        if source.isComposite() or source.numberOfContours != 3:
            raise ValueError(
                f"{source_name} must have two bowl contours plus one dot"
            )
        contour_start = source.endPtsOfContours[-2] + 1
        target = deepcopy(source)
        target.coordinates = type(source.coordinates)(
            source.coordinates[:contour_start]
        )
        target.flags = bytearray(source.flags[:contour_start])
        target.endPtsOfContours = list(source.endPtsOfContours[:-1])
        target.numberOfContours = 2
        target.recalcBounds(glyphs)
        glyphs[target_name] = target
        font["hmtx"].metrics[target_name] = (ADVANCE, target.xMin)

        if target_name not in glyph_order:
            glyph_order.append(target_name)

        if "gvar" in font:
            copied_variations = deepcopy(
                font["gvar"].variations.get(source_name, [])
            )
            source_coordinate_count = len(source.coordinates)
            for variation in copied_variations:
                if len(variation.coordinates) != source_coordinate_count + 4:
                    raise ValueError(
                        f"Unexpected gvar coordinate count for {source_name}"
                    )
                variation.coordinates = (
                    variation.coordinates[:contour_start]
                    + variation.coordinates[-4:]
                )
            font["gvar"].variations[target_name] = copied_variations

    font.setGlyphOrder(glyph_order)
    font["maxp"].numGlyphs = len(glyph_order)


def add_dotless_counter_feature(font: TTFont) -> None:
    """Expose dotless O/o/0 through named stylistic set 03."""
    gsub = font["GSUB"].table
    feature_records = list(gsub.FeatureList.FeatureRecord)
    if any(record.FeatureTag == "ss03" for record in feature_records):
        raise ValueError("ss03 is already present")

    lookup = otTables.Lookup()
    lookup.LookupType = 1
    lookup.LookupFlag = 0
    lookup.SubTable = []
    lookup.SubTableCount = 1
    subtable = otTables.SingleSubst()
    subtable.mapping = dict(DOTLESS_COUNTER_ALTERNATES)
    lookup.SubTable.append(subtable)
    lookup.MarkFilteringSet = None
    lookup_index = len(gsub.LookupList.Lookup)
    gsub.LookupList.Lookup.append(lookup)
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)

    params = otTables.FeatureParamsStylisticSet()
    params.Version = 0
    params.UINameID = add_name(font, "Dotless counters")
    record = otTables.FeatureRecord()
    record.FeatureTag = "ss03"
    record.Feature = otTables.Feature()
    record.Feature.FeatureParams = params
    record.Feature.LookupListIndex = [lookup_index]
    record.Feature.LookupCount = 1

    indexed_records = list(enumerate(feature_records))
    indexed_records.append((None, record))
    indexed_records.sort(key=lambda item: item[1].FeatureTag)
    old_to_new = {
        old_index: new_index
        for new_index, (old_index, _) in enumerate(indexed_records)
        if old_index is not None
    }
    ss03_index = next(
        new_index
        for new_index, (old_index, _) in enumerate(indexed_records)
        if old_index is None
    )
    for script_record in gsub.ScriptList.ScriptRecord:
        lang_systems = []
        if script_record.Script.DefaultLangSys is not None:
            lang_systems.append(script_record.Script.DefaultLangSys)
        lang_systems.extend(
            language.LangSys
            for language in script_record.Script.LangSysRecord
        )
        for lang_system in lang_systems:
            lang_system.FeatureIndex = sorted(
                {
                    *(old_to_new[index] for index in lang_system.FeatureIndex),
                    ss03_index,
                }
            )
            lang_system.FeatureCount = len(lang_system.FeatureIndex)
            if lang_system.ReqFeatureIndex != 0xFFFF:
                lang_system.ReqFeatureIndex = old_to_new[
                    lang_system.ReqFeatureIndex
                ]

    gsub.FeatureList.FeatureRecord = [record for _, record in indexed_records]
    gsub.FeatureList.FeatureCount = len(indexed_records)


def x_transform(
    glyph_name: str,
    char: str | None,
    source_advance: int,
    output_advance: int,
) -> tuple[float, float]:
    # Contextual ligature drawings extend left across one or more placeholder
    # cells while retaining a single-cell advance. Scaling those
    # drawings about x=0 keeps every implied 600-unit source-cell boundary on
    # Fractal Mono's 579-unit grid. The previous centre-only translation preserved
    # the old grid inside a tighter font, so long operators progressively
    # overran their cells and no longer matched Fractal's base punctuation.
    if ".liga" in glyph_name and source_advance:
        return output_advance / source_advance, 0.0

    x_scale = X_SCALE_BY_CHAR.get(char or "", 1.0)
    dx = output_advance / 2 - (source_advance / 2) * x_scale
    return x_scale, dx


def draw_polygon(pen: TTGlyphPen, points: list[tuple[float, float]]) -> None:
    pen.moveTo(points[0])
    for point in points[1:]:
        pen.lineTo(point)
    pen.closePath()


def translate_glyph_x(glyph, distance: float):
    for index, (x, y) in enumerate(glyph.coordinates):
        glyph.coordinates[index] = (round(x + distance), y)
    return glyph


def draw_stroke_segment(
    pen: TTGlyphPen,
    start: tuple[float, float],
    end: tuple[float, float],
    thickness: float,
) -> None:
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    length = (dx * dx + dy * dy) ** 0.5
    normal_x = (-dy / length) * thickness / 2
    normal_y = (dx / length) * thickness / 2
    draw_polygon(
        pen,
        [
            (round(x1 + normal_x), round(y1 + normal_y)),
            (round(x2 + normal_x), round(y2 + normal_y)),
            (round(x2 - normal_x), round(y2 - normal_y)),
            (round(x1 - normal_x), round(y1 - normal_y)),
        ],
    )


def line_intersection(
    first_start: tuple[float, float],
    first_end: tuple[float, float],
    second_start: tuple[float, float],
    second_end: tuple[float, float],
) -> tuple[float, float]:
    """Return the intersection of two infinite lines."""
    x1, y1 = first_start
    x2, y2 = first_end
    x3, y3 = second_start
    x4, y4 = second_end
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denominator == 0:
        raise ValueError("Cannot join parallel stroke segments")
    first_cross = x1 * y2 - y1 * x2
    second_cross = x3 * y4 - y3 * x4
    return (
        (first_cross * (x3 - x4) - (x1 - x2) * second_cross) / denominator,
        (first_cross * (y3 - y4) - (y1 - y2) * second_cross) / denominator,
    )


def draw_mitered_polyline(
    pen: TTGlyphPen,
    points: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
    thickness: float,
) -> None:
    """Draw a clean two-segment stroke as one contour with a true miter."""
    first, joint, last = points

    def normal(start: tuple[float, float], end: tuple[float, float]):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = (dx * dx + dy * dy) ** 0.5
        return (-dy / length * thickness / 2, dx / length * thickness / 2)

    first_normal = normal(first, joint)
    last_normal = normal(joint, last)

    def add(point: tuple[float, float], delta: tuple[float, float]):
        return point[0] + delta[0], point[1] + delta[1]

    def subtract(point: tuple[float, float], delta: tuple[float, float]):
        return point[0] - delta[0], point[1] - delta[1]

    left_joint = line_intersection(
        add(first, first_normal),
        add(joint, first_normal),
        add(joint, last_normal),
        add(last, last_normal),
    )
    right_joint = line_intersection(
        subtract(first, first_normal),
        subtract(joint, first_normal),
        subtract(joint, last_normal),
        subtract(last, last_normal),
    )
    draw_polygon(
        pen,
        [
            add(first, first_normal),
            left_joint,
            add(last, last_normal),
            subtract(last, last_normal),
            right_joint,
            subtract(first, first_normal),
        ],
    )


def draw_round_dot(
    pen: TTGlyphPen,
    center: tuple[float, float],
    radius: float,
) -> None:
    """Draw a quadratic circle for rounded code-symbol caps and joins."""
    center_x, center_y = center
    pen.moveTo((round(center_x), round(center_y + radius)))
    pen.qCurveTo(
        (round(center_x + radius), round(center_y + radius)),
        (round(center_x + radius), round(center_y)),
    )
    pen.qCurveTo(
        (round(center_x + radius), round(center_y - radius)),
        (round(center_x), round(center_y - radius)),
    )
    pen.qCurveTo(
        (round(center_x - radius), round(center_y - radius)),
        (round(center_x - radius), round(center_y)),
    )
    pen.qCurveTo(
        (round(center_x - radius), round(center_y + radius)),
        (round(center_x), round(center_y + radius)),
    )
    pen.closePath()


def draw_round_stroke_segment(
    pen: TTGlyphPen,
    start: tuple[float, float],
    end: tuple[float, float],
    thickness: float,
) -> None:
    """Draw a segment with Lucide-like rounded terminals."""
    draw_stroke_segment(pen, start, end, thickness)
    radius = thickness / 2
    draw_round_dot(pen, start, radius)
    draw_round_dot(pen, end, radius)


def draw_chevron(
    pen: TTGlyphPen,
    origin_x: float,
    direction: str,
    thickness: float,
) -> None:
    """Draw a code-sized angle on the shared punctuation height band."""
    top = origin_x + (465 if direction == "less" else 114), 560
    point = origin_x + (105 if direction == "less" else 474), 330
    bottom = origin_x + (465 if direction == "less" else 114), 70
    draw_mitered_polyline(pen, (top, point, bottom), thickness)


def draw_code_slash(pen: TTGlyphPen, origin_x: float, thickness: float) -> None:
    """Draw a markup slash on the same vertical band as its angle brackets."""
    draw_stroke_segment(
        pen,
        (origin_x + 142, 70),
        (origin_x + 437, 560),
        thickness,
    )


def build_markup_ligature(stem: float, symbols: str):
    """Build restrained, source-legible markup on one Fractal geometry system.

    Every part uses the same 70–560 vertical band and stroke ratio. Each source
    character remains centred in its own cell, and <> stays literal rather than
    becoming a decorative diamond.
    """
    pen = TTGlyphPen(None)
    thickness = stem * 0.80
    origin_x = -(len(symbols) - 1) * ADVANCE

    for symbol in symbols:
        if symbol == "<":
            draw_chevron(pen, origin_x, "less", thickness)
        elif symbol == ">":
            draw_chevron(pen, origin_x, "greater", thickness)
        elif symbol == "/":
            draw_code_slash(pen, origin_x, thickness)
        else:
            raise ValueError(f"Unsupported markup-ligature symbol: {symbol}")
        origin_x += ADVANCE
    return pen.glyph()


def build_comparison_ligature(stem: float, direction: str):
    """Draw <= and >= as compact mathematical symbols centred on two cells."""
    pen = TTGlyphPen(None)
    thickness = stem * 0.78
    left = -265
    right = 265
    top_y = 526
    middle_y = 338
    bottom_y = 150

    if direction == "less":
        point = (left, middle_y)
        draw_stroke_segment(pen, (right - 24, top_y), point, thickness)
        draw_stroke_segment(pen, point, (right - 24, bottom_y), thickness)
    elif direction == "greater":
        point = (right, middle_y)
        draw_stroke_segment(pen, (left + 24, top_y), point, thickness)
        draw_stroke_segment(pen, point, (left + 24, bottom_y), thickness)
    else:
        raise ValueError(f"Unsupported comparison direction: {direction}")

    draw_stroke_segment(pen, (left, 67), (right, 67), thickness)
    return pen.glyph()


def build_less_equal_ligature(stem: float):
    return build_comparison_ligature(stem, "less")


def build_greater_equal_ligature(stem: float):
    return build_comparison_ligature(stem, "greater")


def build_less_slash_ligature(stem: float):
    return build_markup_ligature(stem, "</")


def build_slash_greater_ligature(stem: float):
    return build_markup_ligature(stem, "/>")


def build_less_slash_greater_ligature(stem: float):
    return build_markup_ligature(stem, "</>")


def build_less_greater_ligature(stem: float):
    return build_markup_ligature(stem, "<>")


def build_directional_ligature(
    stem: float,
    symbols: str,
    line_count: int,
):
    """Draw compact arrows centred inside, but not stretched across, their cells.

    The old source drawings treated every added hyphen/equal as more visible
    shaft. That made arrows look like long rails. These use Lucide's compact
    icon logic instead: a short shaft, 45-degree head, rounded tail, and
    rounded joins. The glyph advance and placeholder cells are unchanged.
    """
    pen = TTGlyphPen(None)
    thickness = stem * 0.78
    center_y = 330
    run_left = -(len(symbols) - 1) * ADVANCE
    run_right = ADVANCE
    center_x = (run_left + run_right) / 2
    visible_width = {2: 680, 3: 760, 4: 840}[len(symbols)]
    left = center_x - visible_width / 2
    right = center_x + visible_width / 2
    head_reach = 190
    shaft_gap = max(38, stem * 0.58)

    points_left = symbols.startswith("<")
    points_right = symbols.endswith(">")

    shaft_left = left + (shaft_gap if points_left and line_count == 2 else 0)
    shaft_right = right - (shaft_gap if points_right and line_count == 2 else 0)
    shaft_ys = (
        (center_y,)
        if line_count == 1
        else (center_y - shaft_gap, center_y + shaft_gap)
    )
    for shaft_y in shaft_ys:
        draw_round_stroke_segment(
            pen,
            (shaft_left, shaft_y),
            (shaft_right, shaft_y),
            thickness,
        )

    if points_left:
        tip = (left, center_y)
        draw_round_stroke_segment(
            pen,
            (left + head_reach, center_y + head_reach),
            tip,
            thickness,
        )
        draw_round_stroke_segment(
            pen,
            tip,
            (left + head_reach, center_y - head_reach),
            thickness,
        )

    if points_right:
        tip = (right, center_y)
        draw_round_stroke_segment(
            pen,
            (right - head_reach, center_y + head_reach),
            tip,
            thickness,
        )
        draw_round_stroke_segment(
            pen,
            tip,
            (right - head_reach, center_y - head_reach),
            thickness,
        )

    return pen.glyph()


CUSTOM_PROGRAMMING_LIGATURES = {
    "less_equal.liga": build_less_equal_ligature,
    "greater_equal.liga": build_greater_equal_ligature,
    "less_slash.liga": build_less_slash_ligature,
    "slash_greater.liga": build_slash_greater_ligature,
    "less_slash_greater.liga": build_less_slash_greater_ligature,
    "less_greater.liga": build_less_greater_ligature,
    "hyphen_greater.liga": partial(
        build_directional_ligature, symbols="->", line_count=1
    ),
    "hyphen_hyphen_greater.liga": partial(
        build_directional_ligature, symbols="-->", line_count=1
    ),
    "less_hyphen.liga": partial(
        build_directional_ligature, symbols="<-", line_count=1
    ),
    "less_hyphen_hyphen.liga": partial(
        build_directional_ligature, symbols="<--", line_count=1
    ),
    "less_hyphen_greater.liga": partial(
        build_directional_ligature, symbols="<->", line_count=1
    ),
    "equal_greater.liga": partial(
        build_directional_ligature, symbols="=>", line_count=2
    ),
    "equal_equal_greater.liga": partial(
        build_directional_ligature, symbols="==>", line_count=2
    ),
    "less_equal_equal.liga": partial(
        build_directional_ligature, symbols="<==", line_count=2
    ),
    "less_equal_greater.liga": partial(
        build_directional_ligature, symbols="<=>", line_count=2
    ),
    "less_equal_equal_greater.liga": partial(
        build_directional_ligature, symbols="<==>", line_count=2
    ),
}


def fractal_drawing_y(y: float) -> float:
    if y <= FRACTAL_DRAWING_X_HEIGHT:
        return y * X_HEIGHT / FRACTAL_DRAWING_X_HEIGHT
    return X_HEIGHT + (y - FRACTAL_DRAWING_X_HEIGHT) * (
        (CAP_HEIGHT - X_HEIGHT)
        / (FRACTAL_DRAWING_CAP_HEIGHT - FRACTAL_DRAWING_X_HEIGHT)
    )


def build_fractal_letterform(
    stem: float,
    contours: tuple[tuple[tuple[int, int, bool], ...], ...],
):
    """Build a Fractal letterform in family metrics and weight."""
    x_scale = ADVANCE / FRACTAL_DRAWING_ADVANCE
    reference_stem = FRACTAL_DRAWING_STEM * x_scale
    offset = (stem - reference_stem) / 2
    pen = TTGlyphPen(None)

    for contour in contours:
        reference = [
            (x * x_scale, fractal_drawing_y(y), on_curve, y)
            for x, y, on_curve in contour
        ]
        area = sum(
            x * reference[(index + 1) % len(reference)][1]
            - reference[(index + 1) % len(reference)][0] * y
            for index, (x, y, _, _) in enumerate(reference)
        )
        # Clockwise contours have their exterior on the tangent's left.
        outward_sign = 1 if area < 0 else -1
        expanded = []
        for index, (x, y, on_curve, source_y) in enumerate(reference):
            previous = reference[index - 1]
            following = reference[(index + 1) % len(reference)]
            tangent_x = following[0] - previous[0]
            tangent_y = following[1] - previous[1]
            length = math.hypot(tangent_x, tangent_y)
            normal_x = outward_sign * -tangent_y / length
            normal_y = outward_sign * tangent_x / length
            expanded_y = y + normal_y * offset
            if source_y in {
                0,
                FRACTAL_DRAWING_X_HEIGHT,
                FRACTAL_DRAWING_CAP_HEIGHT,
                662,
            }:
                expanded_y = y
            expanded.append(
                (round(x + normal_x * offset), round(expanded_y), on_curve)
            )

        start_x, start_y, start_on_curve = expanded[0]
        assert start_on_curve
        pen.moveTo((start_x, start_y))
        controls = []
        for x, y, on_curve in expanded[1:]:
            point = (x, y)
            if on_curve:
                if controls:
                    pen.qCurveTo(*controls, point)
                    controls = []
                else:
                    pen.lineTo(point)
            else:
                controls.append(point)
        if controls:
            pen.qCurveTo(*controls, (start_x, start_y))
        pen.closePath()
    return pen.glyph()


def build_lowercase_t(stem: float):
    return build_fractal_letterform(stem, FRACTAL_T_CONTOURS)


@lru_cache(maxsize=None)
def _letterform_reference(name: str, contours):
    return build_fractal_letterform(STEMS_LOWER[1], contours)


def _stroked_letterform(name: str, stem: float, contours):
    glyph = build_fractal_letterform(stem, contours)
    reference = _letterform_reference(name, contours)
    stroke_system.apply(
        glyph,
        name,
        stem=stem,
        reference=reference,
        reference_stem=stroke_system.reference_stem(reference, name),
    )
    return glyph


def build_lowercase_k(stem: float):
    return _stroked_letterform("k", stem, FRACTAL_K_CONTOURS)


def build_lowercase_w(stem: float):
    return _stroked_letterform("w", stem, FRACTAL_W_CONTOURS)


def build_lowercase_r(stem: float):
    """Build Fractal Mono's lowercase r with compatible curve-handle movement."""
    scale = X_HEIGHT / FRACTAL_R_REFERENCE_TOP
    cell_shift = (ADVANCE - FRACTAL_R_REFERENCE_ADVANCE * scale) / 2
    points = [
        (round(x * scale + cell_shift), round(y * scale))
        for x, y in FRACTAL_R_POINTS
    ]

    pen = TTGlyphPen(None)
    pen.moveTo(points[0])
    pen.lineTo(points[1])
    pen.lineTo(points[2])
    pen.qCurveTo(points[3], points[4])
    pen.qCurveTo(points[5], points[6])
    pen.qCurveTo(points[7], points[8], points[9])
    pen.lineTo(points[10])
    pen.qCurveTo(points[11], points[12], points[13], points[14])
    pen.qCurveTo(points[15], points[16], points[17])
    pen.qCurveTo(
        points[18],
        points[19],
        points[20],
        points[21],
        points[22],
        points[23],
        points[24],
        points[25],
    )
    pen.lineTo(points[26])
    pen.lineTo(points[27])
    pen.closePath()
    glyph = pen.glyph()
    reference_stem = FRACTAL_R_REFERENCE_STEM * scale
    glyph = offset_glyph_stable(
        glyph,
        (stem - reference_stem) / 2,
        (0, X_HEIGHT),
    )
    highest = max(y for _, y in glyph.coordinates)
    if highest:
        glyph.coordinates = type(glyph.coordinates)(
            [
                (x, round(y * X_HEIGHT / highest) if y > 0 else y)
                for x, y in glyph.coordinates
            ]
        )
    # The stem cap is a horizontal stroke. Let the shoulder curve depart from
    # it; do not let weight expansion turn those first two points into a wedge.
    for index in (0, 1):
        glyph.coordinates[index] = (
            glyph.coordinates[index][0],
            X_HEIGHT,
        )
    # Distribute the short inner-terminal controls evenly into the shoulder.
    # Crowding these controls against the cut creates the visible bulb that
    # appeared at the end of r, especially in ExtraBold.
    terminal_inner = glyph.coordinates[10]
    shoulder_inner = glyph.coordinates[14]
    for index, fraction in zip((11, 12, 13), (0.25, 0.5, 0.75)):
        glyph.coordinates[index] = (
            round(
                terminal_inner[0]
                + (shoulder_inner[0] - terminal_inner[0]) * fraction
            ),
            round(
                terminal_inner[1]
                + (shoulder_inner[1] - terminal_inner[1]) * fraction
            ),
        )
    return glyph


def swap_in_alternates(font: TTFont) -> None:
    """Make selected character variants the default outlines. Runs before the
    metric transform, so the swapped glyphs go through the same pipeline.
    Deep copies keep the donor glyph independent — both names are transformed
    separately by the metrics loop."""
    import copy

    glyphs = font["glyf"]
    gvar = font["gvar"]
    hmtx = font["hmtx"]
    for target, source in ALTERNATE_SWAPS.items():
        glyphs[target] = copy.deepcopy(glyphs[source])
        gvar.variations[target] = copy.deepcopy(gvar.variations[source])
        hmtx.metrics[target] = hmtx.metrics[source]


def square_dot_mark(font: TTFont, glyph_name: str = "uni0307") -> None:
    """Replace the round dot-above mark with Fractal Mono's crisp square.
    i and j (and every dotted letter) reference this one mark glyph, so they
    all pick it up. Point count, order, and gvar deltas are preserved; the
    existing weight deltas keep growing the square across the axis."""
    glyph = font["glyf"][glyph_name]
    xs = [x for x, _ in glyph.coordinates]
    ys = [y for _, y in glyph.coordinates]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    half_w = (max(xs) - min(xs)) / 2 * 0.82
    half_h = (max(ys) - min(ys)) / 2 * 0.87
    # Keep the dot inside the ascender line.
    vertical_shift = LOWERCASE_ASCENDER_HEIGHT - (cy + half_h)
    # Snap every point to the corner of its quadrant: a true sharp square with
    # the original point count (consecutive duplicates are legal in TrueType).
    for index, (x, y) in enumerate(glyph.coordinates):
        sx = 1 if x >= cx else -1
        sy = 1 if y >= cy else -1
        glyph.coordinates[index] = (
            round(cx + sx * half_w),
            round(cy + sy * half_h + vertical_shift),
        )
    glyph.flags = bytearray([flag | 1 for flag in glyph.flags])
    glyph.recalcBounds(font["glyf"])


def append_zero_dot(
    font: TTFont,
    glyph_name: str,
    *,
    scale: float,
    target_center_y: float,
) -> None:
    """Append zero's centre dot to another variable glyph.

    The base coordinates and every gvar tuple are copied together, preserving
    interpolation at Thin, the intermediate source knot, and ExtraBold. The
    lowercase dot is scaled around its centre so o keeps more counter space.
    """
    glyphs = font["glyf"]
    gvar = font["gvar"]
    source = glyphs["zero"]
    target = glyphs[glyph_name]
    assert source.numberOfContours == 3 and not source.isComposite()
    assert target.numberOfContours > 0 and not target.isComposite()

    source_start = source.endPtsOfContours[-2] + 1
    source_end = source.endPtsOfContours[-1]
    source_coordinates = source.coordinates[source_start : source_end + 1]
    source_flags = source.flags[source_start : source_end + 1]
    source_center_x = (
        min(x for x, _ in source_coordinates)
        + max(x for x, _ in source_coordinates)
    ) / 2
    source_center_y = (
        min(y for _, y in source_coordinates)
        + max(y for _, y in source_coordinates)
    ) / 2
    target_center_x = ADVANCE / 2

    target.coordinates.extend(
        (
            round(target_center_x + (x - source_center_x) * scale),
            round(target_center_y + (y - source_center_y) * scale),
        )
        for x, y in source_coordinates
    )
    target.flags.extend(source_flags)
    target.endPtsOfContours.append(len(target.coordinates) - 1)
    target.numberOfContours += 1

    source_variations = {
        tuple(sorted(variation.axes.items())): variation
        for variation in gvar.variations["zero"]
    }
    for variation in gvar.variations[glyph_name]:
        source_variation = source_variations[tuple(sorted(variation.axes.items()))]
        dot_deltas = source_variation.coordinates[source_start : source_end + 1]
        scaled_deltas = [
            None
            if delta is None
            else (round(delta[0] * scale), round(delta[1] * scale))
            for delta in dot_deltas
        ]
        variation.coordinates = (
            variation.coordinates[:-4]
            + scaled_deltas
            + variation.coordinates[-4:]
        )

    target.recalcBounds(glyphs)


def install_custom_variable_glyph(
    font: TTFont,
    glyph_name: str,
    builder,
    stems: tuple[float, float, float],
) -> None:
    glyphs = font["glyf"]
    thin = builder(stems[0])
    regular = builder(stems[1])
    extra_bold = builder(stems[2])
    assert thin.endPtsOfContours == regular.endPtsOfContours == extra_bold.endPtsOfContours
    assert len(thin.coordinates) == len(regular.coordinates) == len(extra_bold.coordinates)

    glyphs[glyph_name] = regular
    regular.recalcBounds(glyphs)
    font["hmtx"].metrics[glyph_name] = (ADVANCE, regular.xMin)

    def deltas(other) -> list[tuple[int, int]]:
        result = [
            (round(x - base_x), round(y - base_y))
            for (x, y), (base_x, base_y) in zip(other.coordinates, regular.coordinates)
        ]
        return result + [(0, 0)] * 4

    font["gvar"].variations[glyph_name] = [
        TupleVariation({"wght": (-1.0, -1.0, 0.0)}, deltas(thin)),
        TupleVariation({"wght": (0.0, 1.0, 1.0)}, deltas(extra_bold)),
    ]


def set_name(font: TTFont, name_id: int, value: str) -> None:
    table = font["name"]
    table.setName(value, name_id, 3, 1, 0x409)
    table.setName(value, name_id, 1, 0, 0)


def remove_name(font: TTFont, name_id: int) -> None:
    table = font["name"]
    table.names = [record for record in table.names if record.nameID != name_id]


def add_name(font: TTFont, value: str) -> int:
    table = font["name"]
    existing_ids = {
        record.nameID
        for record in table.names
        if record.nameID >= 256 and record.toUnicode() == value
    }
    if existing_ids:
        return min(existing_ids)
    name_id = max(255, *(record.nameID for record in table.names)) + 1
    set_name(font, name_id, value)
    return name_id


def style_postscript(style: str) -> str:
    return style.replace(" ", "")


def set_family_names(font: TTFont, style: str, weight: int) -> None:
    ps_style = style_postscript(style)
    is_variable = "fvar" in font
    is_legacy_bold = style == "Bold"
    if is_variable or style in {"Regular", "Bold"}:
        legacy_family = FAMILY
        legacy_style = style
    else:
        # The legacy name pair only supports Regular/Bold/Italic/Bold Italic.
        # Give other weights their own legacy family while retaining a single
        # typographic family through name IDs 16 and 17.
        legacy_family = f"{FAMILY} {style}"
        legacy_style = "Regular"
    set_name(
        font,
        0,
        (
            'Copyright 2026 Claudia Nathan, with Reserved Font Name "Fractal Mono". '
            "Copyright 2020 The JetBrains Mono Project Authors. "
            "Portions from Whois Mono created by Raphaël Bastide."
        ),
    )
    set_name(font, 1, legacy_family)
    set_name(font, 2, legacy_style)
    # The variable font takes its own PostScript name. Sharing the default
    # instance's name is conventional when only one of the two is installed, but
    # both are, and OpenType wants name ID 6 unique per installed face.
    postscript_name = "FractalMono-Variable" if is_variable else f"FractalMono-{ps_style}"
    set_name(font, 3, f"{VERSION};{VENDOR_ID.strip()};{postscript_name}")
    set_name(font, 4, f"{FAMILY} {style}")
    set_name(font, 5, f"Version {VERSION}")
    set_name(font, 6, postscript_name)
    set_name(font, 8, "Fractal")
    set_name(font, 9, "Claudia Nathan")
    set_name(
        font,
        10,
        "Fractal Mono is a monospaced typeface designed by Claudia Nathan.",
    )
    remove_name(font, 11)
    remove_name(font, 12)
    set_name(font, 13, "This Font Software is licensed under the SIL Open Font License, Version 1.1.")
    set_name(font, 14, "https://openfontlicense.org")
    set_name(font, 16, FAMILY)
    set_name(font, 17, style)
    set_name(font, 25, "FractalMono")

    os2 = font["OS/2"]
    os2.usWeightClass = weight
    os2.usWidthClass = 5
    os2.achVendID = VENDOR_ID
    os2.xAvgCharWidth = ADVANCE
    os2.sTypoAscender = TYPO_ASCENDER
    os2.sTypoDescender = TYPO_DESCENDER
    os2.sTypoLineGap = 0
    os2.usWinAscent = WIN_ASCENDER
    os2.usWinDescent = WIN_DESCENDER
    os2.sxHeight = X_HEIGHT
    os2.sCapHeight = CAP_HEIGHT
    os2.fsSelection &= ~((1 << 0) | (1 << 5) | (1 << 6))
    os2.fsSelection |= 1 << 7  # USE_TYPO_METRICS
    if is_legacy_bold:
        os2.fsSelection |= 1 << 5
    else:
        os2.fsSelection |= 1 << 6
    if hasattr(os2, "panose"):
        os2.panose.bProportion = 9

    hhea = font["hhea"]
    hhea.ascent = TYPO_ASCENDER
    hhea.descent = TYPO_DESCENDER
    hhea.lineGap = 0
    hhea.advanceWidthMax = ADVANCE

    font["head"].unitsPerEm = UPM
    font["head"].fontRevision = float(VERSION)
    font["head"].macStyle &= ~0b11
    if is_legacy_bold:
        font["head"].macStyle |= 1

    post = font["post"]
    post.italicAngle = 0
    post.isFixedPitch = 1


def install_variable_instances(font: TTFont) -> None:
    fvar = font["fvar"]
    fvar.instances = []
    for weight, style in INSTANCES.items():
        instance = NamedInstance()
        instance.subfamilyNameID = add_name(font, style)
        instance.postscriptNameID = add_name(
            font,
            f"FractalMono-{style_postscript(style)}",
        )
        instance.coordinates = {
            "wght": float(weight),
            "opsz": float(DEFAULT_OPSZ),
        }
        instance.flags = 0
        fvar.instances.append(instance)


def install_stat_table(font: TTFont) -> None:
    weight_values = [
        {
            "name": style,
            "value": weight,
            **({"flags": 0x2} if weight == 400 else {}),
        }
        for weight, style in INSTANCES.items()
    ]
    optical_values = [
        {"name": "Text", "value": TEXT_OPSZ},
        {"name": "Auto", "value": DEFAULT_OPSZ, "flags": 0x2},
        {"name": "Display", "value": DISPLAY_OPSZ},
    ]
    buildStatTable(
        font,
        [
            {
                "tag": "wght",
                "name": "Weight",
                "ordering": 0,
                "values": weight_values,
            },
            {
                "tag": "opsz",
                "name": "Optical Size",
                "ordering": 1,
                "values": optical_values,
            },
        ],
    )


def transform_weight_variable() -> TTFont:
    if not VARIABLE_SOURCE.exists():
        raise FileNotFoundError(f"Missing configured OFL source master: {VARIABLE_SOURCE}")

    source = TTFont(VARIABLE_SOURCE, recalcBBoxes=False, recalcTimestamp=False)
    font = instantiateVariableFont(
        source,
        {"wght": AxisTriple(100, SOURCE_REGULAR_WEIGHT, 800)},
        inplace=False,
        optimize=True,
    )
    font["fvar"].axes[0].defaultValue = 400
    # The upstream mapping was tuned for the source's own stem widths. Fractal's
    # stem system is different, so the source axis is left unmapped here and the
    # release mapping is recomputed from Fractal's own anchors in weight_axis_map.
    font["avar"].segments["wght"] = {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}
    swap_in_alternates(font)
    move_programming_ligatures_to_dlig(font)
    glyphs = font["glyf"]
    gvar = font["gvar"]
    representative_chars = best_character_map(font)

    descender_flags = {
        glyph_name: is_descender_glyph(
            glyph_name, glyphs[glyph_name], representative_chars.get(glyph_name)
        )
        for glyph_name in font.getGlyphOrder()
    }

    for glyph_name in font.getGlyphOrder():
        glyph = glyphs[glyph_name]
        source_advance = font["hmtx"].metrics[glyph_name][0]
        output_advance = target_advance(source_advance)
        char = representative_char(glyph_name, representative_chars)
        descender = descender_flags[glyph_name]
        upper_target = (
            LOWERCASE_ASCENDER_HEIGHT
            if char in LOWERCASE_ASCENDER_CHARS
            else CAP_HEIGHT
        )
        xx, dx = x_transform(glyph_name, char, source_advance, output_advance)
        x_shift = OPTICAL_X_SHIFT.get(char or "", 0)
        extra_y, y_center, y_shift = Y_SPECIAL.get(char or "", (1.0, 0, 0))

        def map_y(y: float) -> float:
            remapped = zone_remap(y, descender, upper_target)
            return extra_y * (remapped - y_center) + y_center + y_shift

        if glyph.isComposite():
            # Component outlines are transformed in their own glyphs. Here we
            # only remap component offsets so accents retain alignment. Mark
            # components (zero advance) are positioned absolutely, so they get
            # the same cell-centering shift their base's outline received.
            for component in glyph.components:
                mark = font["hmtx"].metrics[component.glyphName][0] == 0
                component.x = round(component.x * xx + (dx if mark else 0) + x_shift)
                component.y = round(
                    zone_remap(component.y, descender, upper_target) * extra_y
                )
        elif glyph.numberOfContours > 0:
            for index, (x, y) in enumerate(glyph.coordinates):
                glyph.coordinates[index] = (round(x * xx + dx + x_shift), round(map_y(y)))

        # Variation coordinates are deltas, so scale them by the local zone
        # factor at the base point and never translate them.
        base_coordinates = glyph.coordinates if glyph.numberOfContours > 0 else None
        for variation in gvar.variations.get(glyph_name, []):
            for index, delta in enumerate(variation.coordinates):
                if delta is None:
                    continue
                if base_coordinates is not None and index < len(base_coordinates):
                    factor = (
                        zone_factor(
                            base_coordinates[index][1],
                            descender,
                            upper_target,
                        )
                        * extra_y
                    )
                else:
                    factor = LOWER_ZONE_SCALE
                variation.coordinates[index] = (round(delta[0] * xx), round(delta[1] * factor))

        if glyph.numberOfContours != 0:
            glyph.recalcBounds(glyphs)
        font["hmtx"].metrics[glyph_name] = (
            output_advance,
            glyph.xMin if glyph.numberOfContours != 0 else 0,
        )

    square_dot_mark(font)
    zero_dot = glyphs["zero"].coordinates[
        glyphs["zero"].endPtsOfContours[-2] + 1 :
    ]
    zero_dot_center_y = (
        min(y for _, y in zero_dot) + max(y for _, y in zero_dot)
    ) / 2
    append_zero_dot(font, "O", scale=1.0, target_center_y=zero_dot_center_y)
    lowercase_o = glyphs["o"]
    append_zero_dot(
        font,
        "o",
        scale=LOWERCASE_O_DOT_SCALE,
        target_center_y=(lowercase_o.yMin + lowercase_o.yMax) / 2,
    )
    install_dotless_counter_glyphs(font)
    add_dotless_counter_feature(font)
    install_custom_variable_glyph(font, "t", build_lowercase_t, STEMS_LOWER)
    install_custom_variable_glyph(font, "k", build_lowercase_k, STEMS_LOWER)
    install_custom_variable_glyph(font, "r", build_lowercase_r, STEMS_LOWER)
    install_custom_variable_glyph(font, "w", build_lowercase_w, STEMS_LOWER)
    # Option, command and return come from the designer's own vectors; see
    # source/key_symbols.py for the drawings and how they carry across the axis.
    install_custom_variable_glyph(
        font, "uni2325", key_symbols.build_option, STEMS_LOWER
    )
    install_custom_variable_glyph(
        font, "uni23CE", key_symbols.build_return, STEMS_LOWER
    )
    install_custom_variable_glyph(
        font,
        "uni2318",
        partial(key_symbols.build_command, offset_glyph_stable=offset_glyph_stable),
        STEMS_LOWER,
    )
    for glyph_name, builder in CUSTOM_PROGRAMMING_LIGATURES.items():
        install_custom_variable_glyph(font, glyph_name, builder, STEMS_LOWER)

    # Original bytecode and precomputed horizontal metrics no longer describe
    # the transformed outlines. gvar phantom points carry the live metrics.
    glyphs.removeHinting()
    for tag in ("cvt ", "fpgm", "prep", "hdmx", "LTSH", "VDMX", "DSIG", "HVAR"):
        if tag in font:
            del font[tag]

    # The source table enabled grid fitting at every PPEM even though Fractal's
    # transformed outlines deliberately carry no hint programs.
    # Ask rasterizers for grayscale and symmetric smoothing without grid fit.
    font["gasp"].version = 1
    font["gasp"].gaspRange = {65535: 0x000A}

    set_family_names(font, "Regular", 400)
    font.recalcBBoxes = True
    return font


def design_stem(design_weight: float) -> float:
    """Stem width the source masters blend to at a design-space location.

    The design axis is a linear blend between the three stem anchors, so stem
    width is piecewise linear in design weight.
    """
    if design_weight <= 400:
        return STEM_ANCHORS[0] + (design_weight - 100) * (
            (STEM_ANCHORS[1] - STEM_ANCHORS[0]) / 300
        )
    return STEM_ANCHORS[1] + (design_weight - 400) * (
        (STEM_ANCHORS[2] - STEM_ANCHORS[1]) / 400
    )


def design_for_stem(stem: float) -> float:
    if stem <= STEM_ANCHORS[1]:
        return 100 + (stem - STEM_ANCHORS[0]) * (
            300 / (STEM_ANCHORS[1] - STEM_ANCHORS[0])
        )
    return 400 + (stem - STEM_ANCHORS[1]) * (
        400 / (STEM_ANCHORS[2] - STEM_ANCHORS[1])
    )


def target_stem(user_weight: float) -> float:
    """Stem width a named weight should render.

    A constant proportional step keeps every named weight an equal perceptual
    distance from its neighbours. The three anchors already sit on one geometric
    progression, so both halves share a ratio of about 1.17 per 100 units.
    """
    if user_weight <= 400:
        return STEM_ANCHORS[0] * (STEM_ANCHORS[1] / STEM_ANCHORS[0]) ** (
            (user_weight - 100) / 300
        )
    return STEM_ANCHORS[1] * (STEM_ANCHORS[2] / STEM_ANCHORS[1]) ** (
        (user_weight - 400) / 400
    )


def user_for_design(design_weight: float) -> float:
    """Invert the release mapping: which wght value renders this design weight."""
    stem = design_stem(design_weight)
    if stem <= STEM_ANCHORS[1]:
        return 100 + 300 * (
            math.log(stem / STEM_ANCHORS[0])
            / math.log(STEM_ANCHORS[1] / STEM_ANCHORS[0])
        )
    return 400 + 400 * (
        math.log(stem / STEM_ANCHORS[1])
        / math.log(STEM_ANCHORS[2] / STEM_ANCHORS[1])
    )


def weight_master_locations() -> list[tuple[float, float]]:
    """Return (source location, design weight) pairs for the weight masters.

    With the source axis unmapped these are the same number. The 461 knot
    protects the sensitive 300-500 rhythm and 620 covers the bold half, which
    would otherwise interpolate across one span from Book to ExtraBold.
    """
    return [(value, value) for value in WEIGHT_MASTER_DESIGN_LOCATIONS]


def weight_axis_map() -> list[tuple[float, float]]:
    return [
        (sample, round(design_for_stem(target_stem(sample)), 4))
        for sample in WEIGHT_AXIS_SAMPLES
    ]


def make_optical_master(
    weight_variable: TTFont,
    user_weight: float,
    opsz: float,
) -> TTFont:
    font = instantiateVariableFont(
        weight_variable,
        {"wght": user_weight},
        inplace=False,
        optimize=True,
    )
    excluded = frozenset(
        set(CUSTOM_GLYPH_NAMES)
        | set(PRESERVED_MASTER_GLYPH_NAMES)
        | set(SQUARE_MARK_NAMES)
        | {
            "exclamdown",
            "questiondown",
            "ellipsis",
        }
    )
    apply_optical_geometry(font, opsz, excluded=excluded)
    install_preserved_master_glyphs(font, user_weight, opsz)
    install_dotless_counter_glyphs(font)
    install_reference_glyphs(font, user_weight, opsz)
    install_square_marks(font, user_weight, opsz)
    install_square_ellipsis(font, user_weight, opsz)
    REFITTED.update(fitting.apply(font))
    # The dotless alternates copy their bowls from O, o and zero, so they are
    # re-derived after the fitting pass has moved those sidebearings.
    install_dotless_counter_glyphs(font)
    CELL_FITTED.update(fit_glyphs_to_cell(font))
    font.recalcBBoxes = True
    return font


def build_optical_variable(weight_variable: TTFont) -> TTFont:
    masters_dir = BUILD / "masters"
    reset_dir(masters_dir)

    designspace = DesignSpaceDocument()
    weight_axis = AxisDescriptor()
    weight_axis.name = "Weight"
    weight_axis.tag = "wght"
    weight_axis.minimum = 100
    weight_axis.default = 400
    weight_axis.maximum = 800
    weight_axis.map = weight_axis_map()
    designspace.addAxis(weight_axis)

    optical_axis = AxisDescriptor()
    optical_axis.name = "Optical Size"
    optical_axis.tag = "opsz"
    optical_axis.minimum = TEXT_OPSZ
    optical_axis.default = DEFAULT_OPSZ
    optical_axis.maximum = DISPLAY_OPSZ
    designspace.addAxis(optical_axis)

    for user_weight, design_weight in weight_master_locations():
        for opsz in (TEXT_OPSZ, DEFAULT_OPSZ, DISPLAY_OPSZ):
            master = make_optical_master(
                weight_variable,
                user_weight,
                opsz,
            )
            weight_label = f"{user_weight:.3f}".rstrip("0").rstrip(".")
            master_path = masters_dir / f"FractalMono-wght{weight_label}-opsz{opsz}.ttf"
            pin_timestamp(master)
            master.save(master_path)

            source = SourceDescriptor()
            source.name = f"wght-{weight_label}-opsz-{opsz}"
            source.path = str(master_path)
            source.location = {
                "Weight": design_weight,
                "Optical Size": opsz,
            }
            if round(user_weight, 5) == 400 and opsz == DEFAULT_OPSZ:
                source.copyInfo = True
                source.copyLib = True
                source.copyGroups = True
                source.copyFeatures = True
            designspace.addSource(source)

    designspace_path = BUILD / "FractalMono.designspace"
    designspace.write(designspace_path)
    variable, _, _ = build_variable(designspace_path)
    set_family_names(variable, "Regular", 400)
    install_variable_instances(variable)
    install_stat_table(variable)
    variable.recalcBBoxes = True
    return variable


def save_web_flavors(source_path: Path, stem: str) -> None:
    for flavor in ("woff2", "woff"):
        font = TTFont(source_path, recalcTimestamp=False)
        pin_timestamp(font)
        font.flavor = flavor
        font.save(WEB_DIR / f"{stem}.{flavor}")


def instantiate_static(variable_path: Path, weight: int, style: str) -> Path:
    variable = TTFont(variable_path, recalcTimestamp=False)
    static = instantiateVariableFont(
        variable,
        {
            "wght": weight,
            "opsz": DEFAULT_OPSZ,
        },
        inplace=False,
        optimize=True,
    )
    set_family_names(static, style, weight)
    destination = DESKTOP_DIR / f"FractalMono-{style_postscript(style)}.ttf"
    pin_timestamp(static)
    static.save(destination)
    save_web_flavors(destination, f"FractalMono-{style_postscript(style)}")
    return destination


# A release hash has to identify the outlines, not the moment of the build.
# head.modified is the only field that moved between identical builds.
BUILD_TIMESTAMP = 3910000000


def pin_timestamp(font: TTFont) -> None:
    font.recalcTimestamp = False
    font["head"].modified = BUILD_TIMESTAMP
    font["head"].created = BUILD_TIMESTAMP


def sync_package_version() -> None:
    """Keep the npm manifests on the one declared version.

    They cannot import source/version.py, so the build writes them instead of
    trusting anyone to remember.
    """
    for name in ("package.json", "package-lock.json"):
        path = PROJECT / name
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        changed = data.get("version") != PACKAGE_VERSION
        data["version"] = PACKAGE_VERSION
        root = data.get("packages", {}).get("")
        if root is not None and root.get("version") != PACKAGE_VERSION:
            root["version"] = PACKAGE_VERSION
            changed = True
        if changed:
            path.write_text(json.dumps(data, indent=2) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    quick = "--quick" in sys.argv

    reset_dir(BUILD)
    if not quick:
        reset_dir(DESKTOP_DIR)
        reset_dir(WEB_DIR)
    else:
        DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

    weight_variable = transform_weight_variable()
    variable = build_optical_variable(weight_variable)
    programming_sequences = sorted(
        sequence
        for glyph_name in variable.getGlyphOrder()
        if (sequence := ligature_sequence(variable, glyph_name)) is not None
    )
    optional_programming_sequences = [
        sequence
        for sequence in programming_sequences
        if sequence not in ALWAYS_LITERAL_LIGATURE_SEQUENCES
    ]
    variable_path = DESKTOP_DIR / "FractalMono-Variable.ttf"
    pin_timestamp(variable)
    variable.save(variable_path)
    if quick:
        return

    save_web_flavors(variable_path, "FractalMono-Variable")

    static_paths = [
        instantiate_static(variable_path, weight, style)
        for weight, style in INSTANCES.items()
    ]

    files = [variable_path, *static_paths, *sorted(WEB_DIR.iterdir())]
    report = {
        "family": FAMILY,
        "version": VERSION,
        "format": "TrueType outlines; variable wght and opsz axes plus static instances",
        "metrics": {
            "unitsPerEm": UPM,
            "advanceWidth": ADVANCE,
            "capHeight": CAP_HEIGHT,
            "xHeight": X_HEIGHT,
            "lowercaseAscenderHeight": LOWERCASE_ASCENDER_HEIGHT,
            "typoAscender": TYPO_ASCENDER,
            "typoDescender": TYPO_DESCENDER,
        },
        "axes": [
            {"tag": "wght", "min": 100, "default": 400, "max": 800},
            {
                "tag": "opsz",
                "min": TEXT_OPSZ,
                "default": DEFAULT_OPSZ,
                "max": DISPLAY_OPSZ,
            },
        ],
        "sourceRegularWeight": SOURCE_REGULAR_WEIGHT,
        "regularStemTarget": STEMS_LOWER[1],
        "curveRepair": {
            "method": "explicit compatible cubic endpoint masters",
            "removed": "mechanical endpoint outline offsets for R/r/K",
            "scope": "R/r/K at weights 100, 450, and 800",
            "preserves": [
                "metrics",
                "optical fitting",
                "zone remap",
                "canonical Book drawings",
                "variable interpolation",
            ],
        },
        "dottedLetters": {
            "default": ["O", "o", "zero"],
            "dotlessAlternates": list(DOTLESS_COUNTER_ALTERNATES.values()),
            "dotlessFeature": "ss03",
            "sourceContour": "zero centre dot",
            "lowercaseScale": LOWERCASE_O_DOT_SCALE,
        },
        "apparentSize": {
            "strategy": "raise lowercase ascenders without enlarging x-height or line metrics",
            "characters": sorted(LOWERCASE_ASCENDER_CHARS),
            "sharedSquareDotTarget": LOWERCASE_ASCENDER_HEIGHT,
            "target": LOWERCASE_ASCENDER_HEIGHT,
        },
        "opticalXScale": {char: X_SCALE_BY_CHAR[char] for char in ("l", "m")},
        "opticalXShift": OPTICAL_X_SHIFT,
        "slashVerticalScale": Y_SPECIAL["/"][0],
        "customGlyphs": sorted(
            set(CUSTOM_GLYPH_NAMES)
            | {
                "exclamdown",
                "questiondown",
                "k",
                "r",
                "t",
                "w",
            }
        ),
        "opticalSize": {
            "text": TEXT_OPSZ,
            "default": DEFAULT_OPSZ,
            "display": DISPLAY_OPSZ,
            "textXHeight": 540,
            "defaultXHeight": X_HEIGHT,
            "displayXHeight": 500,
            "fixedAdvance": ADVANCE,
        },
        "squareDots": {
            "punctuation": [
                "period",
                "colon",
                "semicolon",
                "exclam",
                "question",
                "ellipsis",
            ],
            "marks": sorted(SQUARE_MARK_NAMES),
            "centerDots": ["zero", "O", "o"],
            "contourPoints": 4,
        },
        "designer": "Claudia Nathan",
        "designDirection": "Fractal",
        "ligatureGridScale": ADVANCE / 600,
        "defaultProgrammingLigatures": "none",
        "defaultLiteralProgrammingSequences": programming_sequences,
        "optionalProgrammingFeature": "dlig",
        "optionalProgrammingSequences": optional_programming_sequences,
        "alwaysLiteralProgrammingSequences": sorted(ALWAYS_LITERAL_LIGATURE_SEQUENCES),
        "rasterization": {
            "hinting": "unhinted transformed outlines",
            "gaspVersion": 1,
            "gaspRange": {"65535": 10},
            "behavior": "grayscale and symmetric smoothing without grid fitting",
        },
        "customProgrammingLigatures": sorted(CUSTOM_PROGRAMMING_LIGATURES),
        "cellFittedGlyphs": sorted(CELL_FITTED),
        "refittedGlyphs": sorted(REFITTED),
        "instances": INSTANCES,
        "files": {
            str(path.relative_to(PROJECT)): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        },
    }
    (PROJECT / "build-report.json").write_text(json.dumps(report, indent=2) + "\n")
    sync_package_version()


if __name__ == "__main__":
    main()
