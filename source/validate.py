#!/usr/bin/env python3
"""Release validation for Fractal Mono."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import tempfile
import unicodedata
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from build import WEIGHT_MASTER_DESIGN_LOCATIONS, user_for_design
from fractal_geometry import (
    _master_outline,
    _stabilize_reference_shape,
    build_reference_glyph,
)
from version import PACKAGE_VERSION, VERSION


PROJECT = Path(__file__).resolve().parents[1]
DESKTOP = PROJECT / "fonts" / "desktop"
WEB = PROJECT / "fonts" / "web"
VARIABLE = DESKTOP / "FractalMono-Variable.ttf"
BUILD_REPORT = PROJECT / "build-report.json"
PREVIOUS_RELEASE = PROJECT / "archive" / "CLNMono-v1.305.zip"
PREVIOUS_FONT = "fonts/desktop/CLNMono-Variable.ttf"


CAP_HEIGHT = 680
X_HEIGHT = 528
TEXT_X_HEIGHT = 540
DISPLAY_X_HEIGHT = 500
LOWERCASE_ASCENDER_HEIGHT = 728
ADVANCE = 579
TEXT_OPSZ = 9
DEFAULT_OPSZ = 14
DISPLAY_OPSZ = 72
REGULAR_STEM_RANGE = range(77, 84)
NAMED_WEIGHTS = (100, 200, 300, 400, 450, 500, 600, 700, 800)
ALWAYS_LITERAL_LIGATURE_SEQUENCES = {"/\\", "\\/", "|||"}
HINTING_TABLES = {"cvt ", "fpgm", "prep", "hdmx", "LTSH", "VDMX"}
REFERENCE_DEPENDENTS = {
    "R": ("Racute", "Rcaron", "uni0156"),
    "r": ("racute", "rcaron", "uni0157"),
    "K": ("uni0136", "uni041A", "uni040C", "Kappa"),
}

CUSTOM_TOPOLOGY = {
    "J": (1, 28),
    "j": (2, 20),
    "K": (1, 15),
    "R": (2, 36),
    "M": (1, 25),
    "W": (1, 31),
    "S": (1, 61),
    "f": (1, 20),
    "l": (1, 10),
    "t": (1, 20),
    "r": (1, 22),
    "exclam": (2, 10),
    "question": (2, 33),
    "asciicircum": (1, 8),
    "colon": (2, 8),
    "semicolon": (2, 8),
    "asterisk": (1, 18),
    "period": (1, 4),
}
SQUARE_CONTOURS = {
    "j": (1,),
    "exclam": (1,),
    "question": (1,),
    "period": (0,),
    "colon": (0, 1),
    "semicolon": (0,),
    "uni0307": (0,),
    "uni0308": (0, 1),
    "dotbelowcomb": (0,),
    "ellipsis": (0, 1, 2),
}
INTENTIONAL_ROOTS = frozenset(
    set(CUSTOM_TOPOLOGY)
    | {
        "exclamdown",
        "questiondown",
        "uni0307",
        "uni0308",
        "dotbelowcomb",
        "zero",
        "O",
        "o",
        "ellipsis",
        # Redrawn in 1.400: the stroke system now governs their diagonals.
        "K",
        "M",
        "W",
        "k",
        "w",
        "asterisk",
        # Rebuilt in 1.400 from the designer's own vectors.
        "uni2325",
        "uni2318",
        "uni23CE",
    }
    # Plus whatever the cell fit had to recentre, which the build records rather
    # than this file restating.
    | set(json.loads((PROJECT / "build-report.json").read_text()).get("cellFittedGlyphs", []))
)


def family_name(font: TTFont) -> str:
    for record in font["name"].names:
        if record.nameID == 16 and record.platformID == 3:
            return record.toUnicode()
    raise AssertionError("Missing typographic family name")


def version_name(font: TTFont) -> str:
    for record in font["name"].names:
        if record.nameID == 5 and record.platformID == 3:
            return record.toUnicode()
    raise AssertionError("Missing version name")


def glyph_signature(font: TTFont, glyph_name: str) -> tuple[tuple[int, int], ...]:
    coordinates, _, _ = font["glyf"][glyph_name].getCoordinates(font["glyf"])
    return tuple((round(x), round(y)) for x, y in coordinates)


def glyph_bounds(font: TTFont, glyph_name: str) -> tuple[int, int, int, int]:
    glyph = font["glyf"][glyph_name]
    glyph.recalcBounds(font["glyf"])
    return glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax


def assert_version_consistency() -> None:
    """Nothing may advertise a version other than the one being built.

    The specimen used to link a download for a release four versions old that had
    never been packaged, because the version lived in four separate hardcoded
    copies. They now all derive from source/version.py; this holds the ones that
    cannot import it.
    """
    package = json.loads((PROJECT / "package.json").read_text())
    assert package["version"] == PACKAGE_VERSION, (
        "package.json",
        package["version"],
        PACKAGE_VERSION,
    )
    specimen = (PROJECT / "specimen.html").read_text()
    assert f"Fractal Mono {VERSION}" in specimen, "specimen title is stale"
    archive = PROJECT / "archive" / f"FractalMono-v{VERSION}.zip"
    linked = f"./archive/FractalMono-v{VERSION}.zip"
    assert linked in specimen, "specimen does not link this release"
    assert archive.exists(), f"specimen links {archive.name} but it is not packaged"

    report = json.loads((PROJECT / "build-report.json").read_text())
    assert report["version"] == VERSION, ("build-report.json", report["version"])
    print(f"PASS: every version reference agrees on {VERSION} and its archive exists")


def assert_reference_drawings(variable: TTFont) -> None:
    """Prove the supplied R/r/K constructions survive into the release binary.

    Checked at every weight master, where the instance must reproduce the source
    construction exactly. An off-master location can only ever be an
    interpolation of its neighbours, so asserting there tests arithmetic rather
    than the drawing.
    """
    for design_weight in WEIGHT_MASTER_DESIGN_LOCATIONS:
        instance = instantiateVariableFont(
            variable,
            {"wght": user_for_design(design_weight), "opsz": DEFAULT_OPSZ},
            inplace=False,
            optimize=True,
        )
        for glyph_name in ("R", "r", "K"):
            expected = build_reference_glyph(glyph_name, design_weight, DEFAULT_OPSZ)
            # The release applies the same cell-fitting pass before installing.
            _stabilize_reference_shape(glyph_name, expected)
            actual = instance["glyf"][glyph_name]
            where = f"design {design_weight:g}"
            assert list(actual.endPtsOfContours) == list(expected.endPtsOfContours), (
                glyph_name, where, "topology",
            )
            assert [flag & 1 for flag in actual.flags] == [
                flag & 1 for flag in expected.flags
            ], (glyph_name, where, "flags")
            assert len(actual.coordinates) == len(expected.coordinates)
            for current, target in zip(actual.coordinates, expected.coordinates):
                assert math.dist(current, target) <= 1.0, (
                    glyph_name, where, current, target,
                )
            assert instance["hmtx"].metrics[glyph_name][0] == ADVANCE


def assert_reference_dependents(variable: TTFont) -> int:
    """Ensure language derivatives inherit the new base drawings."""
    for base, dependents in REFERENCE_DEPENDENTS.items():
        for glyph_name in dependents:
            glyph = variable["glyf"][glyph_name]
            assert glyph.isComposite(), (glyph_name, "expected composite")
            assert any(
                component.glyphName == base for component in glyph.components
            ), (glyph_name, base, "missing base component")
            assert variable["hmtx"].metrics[glyph_name][0] == ADVANCE
    return sum(len(dependents) for dependents in REFERENCE_DEPENDENTS.values())


def contour_signature(
    font: TTFont,
    glyph_name: str,
    contour_index: int,
) -> tuple[tuple[int, int], ...]:
    glyph = font["glyf"][glyph_name]
    start = 0 if contour_index == 0 else glyph.endPtsOfContours[contour_index - 1] + 1
    end = glyph.endPtsOfContours[contour_index]
    return tuple(
        (round(x), round(y))
        for x, y in glyph.coordinates[start : end + 1]
    )


def contour_bounds(
    font: TTFont,
    glyph_name: str,
    contour_index: int,
) -> tuple[int, int, int, int]:
    coordinates = contour_signature(font, glyph_name, contour_index)
    return (
        min(x for x, _ in coordinates),
        min(y for _, y in coordinates),
        max(x for x, _ in coordinates),
        max(y for _, y in coordinates),
    )


def contour_area(coordinates: tuple[tuple[int, int], ...]) -> float:
    return sum(
        x * coordinates[(index + 1) % len(coordinates)][1]
        - coordinates[(index + 1) % len(coordinates)][0] * y
        for index, (x, y) in enumerate(coordinates)
    ) / 2


def segments_intersect(
    first_start: tuple[int, int],
    first_end: tuple[int, int],
    second_start: tuple[int, int],
    second_end: tuple[int, int],
) -> bool:
    def orientation(
        start: tuple[int, int],
        end: tuple[int, int],
        point: tuple[int, int],
    ) -> int:
        value = (
            (end[0] - start[0]) * (point[1] - start[1])
            - (end[1] - start[1]) * (point[0] - start[0])
        )
        return (value > 0) - (value < 0)

    def on_segment(
        start: tuple[int, int],
        point: tuple[int, int],
        end: tuple[int, int],
    ) -> bool:
        return (
            min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
            and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
        )

    orientations = (
        orientation(first_start, first_end, second_start),
        orientation(first_start, first_end, second_end),
        orientation(second_start, second_end, first_start),
        orientation(second_start, second_end, first_end),
    )
    if orientations[0] != orientations[1] and orientations[2] != orientations[3]:
        return True
    return (
        (orientations[0] == 0 and on_segment(first_start, second_start, first_end))
        or (orientations[1] == 0 and on_segment(first_start, second_end, first_end))
        or (orientations[2] == 0 and on_segment(second_start, first_start, second_end))
        or (orientations[3] == 0 and on_segment(second_start, first_end, second_end))
    )


def assert_clean_contour(
    font: TTFont,
    glyph_name: str,
    contour_index: int,
) -> None:
    coordinates = contour_signature(font, glyph_name, contour_index)
    assert len(coordinates) >= 3, (glyph_name, contour_index, coordinates)
    assert coordinates[0] != coordinates[-1], (
        glyph_name,
        contour_index,
        "explicit closing duplicate",
    )
    for current, following in zip(
        coordinates,
        (*coordinates[1:], coordinates[0]),
    ):
        assert current != following, (
            glyph_name,
            contour_index,
            "zero-length segment",
            current,
        )
    assert abs(contour_area(coordinates)) > 1, (
        glyph_name,
        contour_index,
        "zero-area contour",
    )
    glyph = font["glyf"][glyph_name]
    start = 0 if contour_index == 0 else glyph.endPtsOfContours[contour_index - 1] + 1
    if all(
        glyph.flags[index] & 1
        for index in range(start, start + len(coordinates))
    ):
        segments = list(
            zip(coordinates, (*coordinates[1:], coordinates[0]))
        )
        for first_index, first in enumerate(segments):
            for second_index in range(first_index + 1, len(segments)):
                if second_index in {
                    first_index,
                    first_index + 1,
                } or (first_index == 0 and second_index == len(segments) - 1):
                    continue
                assert not segments_intersect(*first, *segments[second_index]), (
                    glyph_name,
                    contour_index,
                    "self-intersection",
                    first_index,
                    second_index,
                )


def assert_square_contour(
    font: TTFont,
    glyph_name: str,
    contour_index: int,
) -> None:
    glyph = font["glyf"][glyph_name]
    coordinates = contour_signature(font, glyph_name, contour_index)
    assert len(coordinates) == 4, (glyph_name, contour_index, coordinates)
    start = 0 if contour_index == 0 else glyph.endPtsOfContours[contour_index - 1] + 1
    assert all(glyph.flags[index] & 1 for index in range(start, start + 4)), (
        glyph_name,
        contour_index,
        "square points must be on-curve",
    )
    xs = sorted({x for x, _ in coordinates})
    ys = sorted({y for _, y in coordinates})
    assert len(xs) == len(ys) == 2, (glyph_name, contour_index, coordinates)
    # Exactly square at the masters, which validate_geometry.py asserts. Between
    # them each of the four edges is rebuilt from an integer delta, so the width
    # and the height can each round a unit and diverge by two.
    assert abs((xs[1] - xs[0]) - (ys[1] - ys[0])) <= 2, (
        glyph_name,
        contour_index,
        "dot is not square",
        coordinates,
    )
    assert_clean_contour(font, glyph_name, contour_index)


def shape(text: str, features: str | None = None) -> str:
    harfbuzz = shutil.which("hb-shape")
    assert harfbuzz, "hb-shape is required for programming-ligature validation"
    command = [
        harfbuzz,
        str(VARIABLE),
        f"--variations=wght=400,opsz={DEFAULT_OPSZ}",
    ]
    if features:
        command.append(f"--features={features}")
    command.extend(["--", text])
    return subprocess.check_output(command, text=True).strip()


def shape_file(path: Path, text: str, features: str | None = None) -> str:
    harfbuzz = shutil.which("hb-shape")
    assert harfbuzz, "hb-shape is required for release-file validation"

    def run(shape_path: Path) -> str:
        command = [harfbuzz, str(shape_path)]
        if "Variable" in path.name:
            command.append(
                f"--variations=wght=400,opsz={DEFAULT_OPSZ}"
            )
        if features:
            command.append(f"--features={features}")
        command.extend(["--", text])
        return subprocess.check_output(command, text=True).strip()

    if path.suffix == ".ttf":
        return run(path)

    with tempfile.TemporaryDirectory(prefix="cln-font-validate-") as directory:
        temporary_path = Path(directory) / f"{path.stem}.ttf"
        font = TTFont(path)
        font.flavor = None
        font.save(temporary_path)
        return run(temporary_path)


def depends_on(
    font: TTFont,
    glyph_name: str,
    roots: frozenset[str],
    seen: frozenset[str] = frozenset(),
) -> bool:
    if glyph_name in roots:
        return True
    glyph = font["glyf"][glyph_name]
    if not glyph.isComposite():
        return False
    for component in glyph.components:
        if component.glyphName in seen:
            continue
        if depends_on(
            font,
            component.glyphName,
            roots,
            seen | {component.glyphName},
        ):
            return True
    return False


def assert_default_preservation(variable: TTFont) -> int:
    assert PREVIOUS_RELEASE.exists(), "Missing v1.305 regression archive"
    with ZipFile(PREVIOUS_RELEASE) as archive:
        previous = TTFont(BytesIO(archive.read(PREVIOUS_FONT)))

    preserved: set[str] = set()
    for weight in (100, 400, 800):
        current_instance = instantiateVariableFont(
            variable,
            {"wght": weight, "opsz": DEFAULT_OPSZ},
            inplace=False,
        )
        previous_instance = instantiateVariableFont(
            previous,
            {"wght": weight, "opsz": DEFAULT_OPSZ},
            inplace=False,
        )
        current_cmap = current_instance.getBestCmap()
        previous_cmap = previous_instance.getBestCmap()
        for codepoint in current_cmap.keys() & previous_cmap.keys():
            glyph_name = current_cmap[codepoint]
            if depends_on(variable, glyph_name, INTENTIONAL_ROOTS):
                continue
            old_name = previous_cmap[codepoint]
            current_coordinates, _, _ = current_instance["glyf"][
                glyph_name
            ].getCoordinates(current_instance["glyf"])
            previous_coordinates, _, _ = previous_instance["glyf"][
                old_name
            ].getCoordinates(previous_instance["glyf"])
            assert len(current_coordinates) == len(previous_coordinates), (
                glyph_name,
                weight,
                "topology",
            )
            for current, old in zip(current_coordinates, previous_coordinates):
                assert math.dist(current, old) <= 0.75, (
                    glyph_name,
                    weight,
                    current,
                    old,
                )
            assert current_instance["hmtx"].metrics[glyph_name][0] == (
                previous_instance["hmtx"].metrics[old_name][0]
            )
            preserved.add(glyph_name)

    # 1.400 restates k and w through the stroke system, so their coordinates are
    # expected to move. What must not change is that they remain the same
    # compatible drawings rather than replacements: same contours, same points,
    # same on-curve pattern. Their stroke behaviour is gated by
    # source/validate_geometry.py.
    for glyph_name in ("k", "w"):
        current = variable["glyf"][glyph_name]
        earlier = previous["glyf"][glyph_name]
        assert list(current.endPtsOfContours) == list(earlier.endPtsOfContours), (
            glyph_name,
            "contour topology changed",
        )
        assert [flag & 1 for flag in current.flags] == [
            flag & 1 for flag in earlier.flags
        ], (glyph_name, "on-curve pattern changed")
    return len(preserved)


def assert_round_dotted_bowls_preserved(variable: TTFont) -> None:
    """Protect established bowls while allowing only their final dot to change."""
    assert PREVIOUS_RELEASE.exists(), "Missing v1.305 regression archive"
    with ZipFile(PREVIOUS_RELEASE) as archive:
        previous = TTFont(BytesIO(archive.read(PREVIOUS_FONT)))

    for weight in (100, 400, 800):
        current_instance = instantiateVariableFont(
            variable,
            {"wght": weight, "opsz": DEFAULT_OPSZ},
            inplace=False,
        )
        previous_instance = instantiateVariableFont(
            previous,
            {"wght": weight, "opsz": DEFAULT_OPSZ},
            inplace=False,
        )
        for glyph_name in ("O", "o", "zero"):
            current = current_instance["glyf"][glyph_name]
            old = previous_instance["glyf"][glyph_name]
            current_dot_start = current.endPtsOfContours[-2] + 1
            old_dot_start = old.endPtsOfContours[-2] + 1
            assert current_dot_start == old_dot_start, (
                glyph_name,
                weight,
                "retained contour topology",
            )
            for index in range(current_dot_start):
                assert math.dist(
                    current.coordinates[index],
                    old.coordinates[index],
                ) <= 1.1, (glyph_name, weight, index)
                assert (current.flags[index] & 1) == (old.flags[index] & 1), (
                    glyph_name,
                    weight,
                    index,
                    "curve flag",
                )
            assert any(
                not (current.flags[index] & 1)
                for index in range(current_dot_start)
            ), (glyph_name, weight, "rounded contours lost")


def main() -> None:
    font_paths = (
        sorted(DESKTOP.glob("*.ttf"))
        + sorted(WEB.glob("*.woff"))
        + sorted(WEB.glob("*.woff2"))
    )
    assert len(font_paths) == 30, (
        f"Expected 30 font files, found {len(font_paths)}"
    )

    report = json.loads(BUILD_REPORT.read_text())
    assert report["version"] == VERSION
    assert report["metrics"] == {
        "unitsPerEm": 1000,
        "advanceWidth": ADVANCE,
        "capHeight": CAP_HEIGHT,
        "xHeight": X_HEIGHT,
        "lowercaseAscenderHeight": LOWERCASE_ASCENDER_HEIGHT,
        "typoAscender": 950,
        "typoDescender": -250,
    }
    assert report["axes"] == [
        {"tag": "wght", "min": 100, "default": 400, "max": 800},
        {
            "tag": "opsz",
            "min": TEXT_OPSZ,
            "default": DEFAULT_OPSZ,
            "max": DISPLAY_OPSZ,
        },
    ]
    assert report["opticalSize"] == {
        "text": TEXT_OPSZ,
        "default": DEFAULT_OPSZ,
        "display": DISPLAY_OPSZ,
        "textXHeight": TEXT_X_HEIGHT,
        "defaultXHeight": X_HEIGHT,
        "displayXHeight": DISPLAY_X_HEIGHT,
        "fixedAdvance": ADVANCE,
    }
    assert report["squareDots"]["contourPoints"] == 4
    assert set(report["squareDots"]["marks"]) == {
        "uni0307",
        "uni0308",
        "dotbelowcomb",
    }
    assert report["designer"] == "Claudia Nathan"
    assert report["designDirection"] == "Fractal"
    assert report["defaultProgrammingLigatures"] == "none"
    assert report["optionalProgrammingFeature"] == "dlig"
    assert len(report["defaultLiteralProgrammingSequences"]) == 153
    assert len(report["optionalProgrammingSequences"]) == 150
    assert set(report["alwaysLiteralProgrammingSequences"]) == (
        ALWAYS_LITERAL_LIGATURE_SEQUENCES
    )
    assert report["rasterization"] == {
        "hinting": "unhinted transformed outlines",
        "gaspVersion": 1,
        "gaspRange": {"65535": 10},
        "behavior": "grayscale and symmetric smoothing without grid fitting",
    }
    assert set(report["files"]) == {
        str(path.relative_to(PROJECT)) for path in font_paths
    }
    for path in font_paths:
        relative_path = str(path.relative_to(PROJECT))
        assert report["files"][relative_path]["bytes"] == path.stat().st_size
        assert report["files"][relative_path]["sha256"] == hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

    for path in font_paths:
        font = TTFont(path, lazy=False)
        assert family_name(font) == "Fractal Mono", path
        assert version_name(font) == f"Version {VERSION}", path
        assert round(font["head"].fontRevision, 3) == float(VERSION), path
        assert font["head"].unitsPerEm == 1000, path
        assert font["OS/2"].sxHeight == X_HEIGHT, path
        assert font["OS/2"].sCapHeight == CAP_HEIGHT, path
        assert font["OS/2"].fsSelection & (1 << 7), (
            f"USE_TYPO_METRICS missing in {path}"
        )
        assert (
            font["hhea"].ascent,
            font["hhea"].descent,
            font["hhea"].lineGap,
        ) == (
            font["OS/2"].sTypoAscender,
            font["OS/2"].sTypoDescender,
            font["OS/2"].sTypoLineGap,
        ), path
        assert font["gasp"].version == 1, path
        assert font["gasp"].gaspRange == {65535: 10}, path
        assert not (HINTING_TABLES & set(font.keys())), path
        assert len(font.getBestCmap()) >= 1360, path
        for glyph_name, expected_contours in (
            ("O", 3),
            ("o", 3),
            ("zero", 3),
        ):
            assert font["glyf"][glyph_name].numberOfContours == expected_contours
        if "Variable" in path.name:
            assert "HVAR" in font, path
        else:
            assert "fvar" not in font and "gvar" not in font, path
        font.close()

        for sequence in (
            "===",
            "!==",
            "=>",
            "->",
            "-->",
            "<->",
            "<==>",
            ">=",
            "<=",
            "--",
            "<<",
            ">>",
            "||",
            "</>",
            "<>",
            "//",
            "...",
            ":::",
        ):
            result = shape_file(path, sequence)
            assert ".liga" not in result, (path, sequence, result)
            assert result.count(f"+{ADVANCE}") == len(sequence), (
                path,
                sequence,
                result,
            )

        for sequence, glyph_name in {
            "===": "equal_equal_equal.liga",
            "!==": "exclam_equal_equal.liga",
            "=>": "equal_greater.liga",
            "->": "hyphen_greater.liga",
            ">=": "greater_equal.liga",
            "<=": "less_equal.liga",
            "</>": "less_slash_greater.liga",
            "<>": "less_greater.liga",
            "//": "slash_slash.liga",
            "...": "period_period_period.liga",
            ":::": "colon_colon_colon.liga",
        }.items():
            result = shape_file(path, sequence, "dlig=1")
            assert glyph_name in result, (path, sequence, result)
            assert result.count(f"+{ADVANCE}") == len(sequence), (
                path,
                sequence,
                result,
            )

    variable = TTFont(VARIABLE)
    axes = {axis.axisTag: axis for axis in variable["fvar"].axes}
    assert set(axes) == {"wght", "opsz"}
    assert (
        axes["wght"].minValue,
        axes["wght"].defaultValue,
        axes["wght"].maxValue,
    ) == (100, 400, 800)
    assert (
        axes["opsz"].minValue,
        axes["opsz"].defaultValue,
        axes["opsz"].maxValue,
    ) == (TEXT_OPSZ, DEFAULT_OPSZ, DISPLAY_OPSZ)
    instance_locations = {
        (
            round(instance.coordinates["wght"]),
            round(instance.coordinates["opsz"]),
        )
        for instance in variable["fvar"].instances
    }
    assert instance_locations == {
        (weight, DEFAULT_OPSZ)
        for weight in (100, 200, 300, 400, 450, 500, 600, 700, 800)
    }
    for tag in ("avar", "STAT", "gasp", "HVAR"):
        assert tag in variable, f"Missing {tag} table"
    assert_version_consistency()
    assert_reference_drawings(variable)
    reference_dependent_count = assert_reference_dependents(variable)

    feature_records = variable["GSUB"].table.FeatureList.FeatureRecord
    dlig_features = [
        record.Feature
        for record in feature_records
        if record.FeatureTag == "dlig"
    ]
    calt_features = [
        record.Feature
        for record in feature_records
        if record.FeatureTag == "calt"
    ]
    assert len(dlig_features) == 1
    assert dlig_features[0].LookupCount == 152
    assert len(calt_features) == 1
    assert calt_features[0].LookupCount == 2
    ss03_records = [
        record
        for record in feature_records
        if record.FeatureTag == "ss03"
    ]
    assert len(ss03_records) == 1
    assert ss03_records[0].Feature.LookupCount == 1
    params = ss03_records[0].Feature.FeatureParams
    assert params is not None
    assert any(
        record.nameID == params.UINameID
        and record.toUnicode() == "Dotless counters"
        for record in variable["name"].names
    )

    cmap = variable.getBestCmap()
    axis_grid = [
        (weight, opsz)
        for weight in NAMED_WEIGHTS
        for opsz in (TEXT_OPSZ, DEFAULT_OPSZ, DISPLAY_OPSZ)
    ]
    default_ascender_strokes = {}
    for weight in NAMED_WEIGHTS:
        instance = instantiateVariableFont(
            variable,
            {"wght": weight, "opsz": DEFAULT_OPSZ},
            inplace=False,
        )
        glyphs = instance["glyf"]
        f_coordinates, _, _ = glyphs["f"].getCoordinates(glyphs)
        l_coordinates, _, _ = glyphs["l"].getCoordinates(glyphs)
        default_ascender_strokes[weight] = (
            round(f_coordinates[9][1] - f_coordinates[10][1]),
            round(l_coordinates[5][1] - l_coordinates[4][1]),
        )

    for weight, opsz in axis_grid:
        instance = instantiateVariableFont(
            variable,
            {"wght": weight, "opsz": opsz},
            inplace=False,
        )
        for codepoint in range(0x20, 0x7F):
            glyph_name = cmap[codepoint]
            assert instance["hmtx"].metrics[glyph_name][0] == ADVANCE, (
                chr(codepoint),
                weight,
                opsz,
            )

        for glyph_name, (contours, points) in CUSTOM_TOPOLOGY.items():
            glyph = instance["glyf"][glyph_name]
            coordinates, _, _ = glyph.getCoordinates(instance["glyf"])
            assert glyph.numberOfContours == contours, (
                glyph_name,
                weight,
                opsz,
                glyph.numberOfContours,
            )
            assert len(coordinates) == points, (
                glyph_name,
                weight,
                opsz,
                len(coordinates),
            )
            for contour_index in range(contours):
                assert_clean_contour(instance, glyph_name, contour_index)

        t_coordinates, _, _ = instance["glyf"]["t"].getCoordinates(
            instance["glyf"]
        )
        assert round(t_coordinates[7][0]) == round(t_coordinates[8][0]), (
            weight,
            opsz,
            "t left ascender edge",
        )
        assert round(t_coordinates[9][0]) == round(t_coordinates[10][0]), (
            weight,
            opsz,
            "t right ascender edge",
        )
        assert round(t_coordinates[8][1]) == round(t_coordinates[9][1]), (
            weight,
            opsz,
            "t cap",
        )
        assert round(t_coordinates[7][1]) == round(t_coordinates[10][1]), (
            weight,
            opsz,
            "t crossbar",
        )
        t_crossbar_top = round(t_coordinates[6][1])
        assert all(
            round(t_coordinates[index][1]) == t_crossbar_top
            for index in (7, 10, 11)
        ), (weight, opsz, "t crossbar top")
        t_crossbar_bottom = round(t_coordinates[4][1])
        assert all(
            round(t_coordinates[index][1]) == t_crossbar_bottom
            for index in (5, 12, 13)
        ), (weight, opsz, "t crossbar bottom")

        h_coordinates, _, _ = instance["glyf"]["H"].getCoordinates(
            instance["glyf"]
        )
        h_vertical_stroke = round(
            abs(h_coordinates[2][0] - h_coordinates[1][0])
        )
        h_y = sorted({round(y) for _, y in h_coordinates})
        h_horizontal_stroke = h_y[-2] - h_y[1]
        # Exact at the weight masters. Between them both glyphs are rebuilt from
        # integer variation deltas, so each can round a single unit either way.
        assert abs(
            (t_crossbar_top - t_crossbar_bottom) - h_horizontal_stroke
        ) <= 1, (weight, opsz, "t/H horizontal stroke")
        t_foot_top = round(t_coordinates[17][1])
        assert all(
            round(t_coordinates[index][1]) == t_foot_top
            for index in (16, 17, 18)
        ), (weight, opsz, "t foot top")
        assert abs(t_foot_top - h_horizontal_stroke) <= 1, (
            weight,
            opsz,
            "t/H foot stroke",
        )
        assert round(t_coordinates[18][0]) == round(t_coordinates[19][0]), (
            weight,
            opsz,
            "t foot terminal",
        )

        j_coordinates, _, _ = instance["glyf"]["j"].getCoordinates(
            instance["glyf"]
        )
        assert round(j_coordinates[7][1]) == round(j_coordinates[8][1]), (
            weight,
            opsz,
            "j flag bottom",
        )
        assert round(j_coordinates[9][1]) == round(j_coordinates[10][1]), (
            weight,
            opsz,
            "j flag top",
        )
        assert round(j_coordinates[8][0]) == round(j_coordinates[9][0]), (
            weight,
            opsz,
            "j flag left edge",
        )
        assert round(j_coordinates[10][0]) == round(j_coordinates[11][0]), (
            weight,
            opsz,
            "j flag right edge",
        )
        assert abs(
            round(j_coordinates[9][1] - j_coordinates[8][1])
            - h_horizontal_stroke
        ) <= 2, (weight, opsz, "j/H horizontal stroke")
        assert round(j_coordinates[0][1]) == round(j_coordinates[15][1]), (
            weight,
            opsz,
            "j terminal bottom",
        )
        assert round(j_coordinates[1][1]) == round(j_coordinates[2][1]), (
            weight,
            opsz,
            "j terminal top",
        )

        j_cap = instance["glyf"]["J"].coordinates
        assert round(j_cap[6][1]) == round(j_cap[7][1]), (
            weight,
            opsz,
            "J terminal",
        )
        assert min(j_cap[8][0], j_cap[10][0]) - 1 <= j_cap[9][0] <= max(
            j_cap[8][0],
            j_cap[10][0],
        ) + 1, (weight, opsz, "J terminal control reversal")

        k_coordinates = instance["glyf"]["K"].coordinates
        upper_bridge_limits = sorted(
            (k_coordinates[3][0], k_coordinates[6][0])
        )
        assert all(
            upper_bridge_limits[0] - 4
            <= k_coordinates[index][0]
            <= upper_bridge_limits[1] + 4
            for index in (4, 5)
        ), (weight, opsz, "K upper bridge control escape")
        assert (
            k_coordinates[13][0]
            <= k_coordinates[12][0]
            < k_coordinates[9][0]
            and k_coordinates[12][1] < k_coordinates[9][1]
        ), (weight, opsz, "K lower bridge reversal")
        k_stem = round(k_coordinates[2][0] - k_coordinates[1][0])
        assert abs(k_stem - h_vertical_stroke) <= 6, (
            weight,
            opsz,
            "K/H vertical stroke",
            k_stem,
            h_vertical_stroke,
        )

        s_coordinates = instance["glyf"]["S"].coordinates
        assert round(s_coordinates[0][1]) == round(s_coordinates[1][1]), (
            weight,
            opsz,
            "S bottom terminal",
        )
        assert round(s_coordinates[31][1]) == round(s_coordinates[32][1]), (
            weight,
            opsz,
            "S top terminal",
        )
        assert all(
            0 <= s_coordinates[index][1] <= CAP_HEIGHT
            for index in (24, 25, 27, 28, 54, 55, 57, 58)
        ), (weight, opsz, "S hard-zone overshoot")

        r_cap_coordinates = instance["glyf"]["R"].coordinates
        r_cap_stem = round(
            r_cap_coordinates[24][0] - r_cap_coordinates[0][0]
        )
        assert abs(r_cap_stem - h_vertical_stroke) <= 4, (
            weight,
            opsz,
            "R/H vertical stroke",
            r_cap_stem,
            h_vertical_stroke,
        )
        r_cap_counter = contour_bounds(instance, "R", 1)
        counter_width = r_cap_counter[2] - r_cap_counter[0]
        counter_height = r_cap_counter[3] - r_cap_counter[1]
        assert counter_width >= 225 and counter_height >= 135, (
            weight,
            opsz,
            "R counter closure",
            r_cap_counter,
        )
        r_cap_bounds = glyph_bounds(instance, "R")
        assert (
            r_cap_bounds[0] < r_cap_counter[0] < r_cap_counter[2] < r_cap_bounds[2]
        ), (weight, opsz, "R counter containment")
        assert abs(
            (r_cap_counter[0] - r_cap_bounds[0]) - h_vertical_stroke
        ) <= 8, (weight, opsz, "R left bowl stroke")
        assert abs(
            (r_cap_bounds[2] - r_cap_counter[2]) - h_vertical_stroke
        ) <= 12, (weight, opsz, "R right bowl stroke")

        r_coordinates = instance["glyf"]["r"].coordinates
        assert abs(r_coordinates[0][0] - r_coordinates[1][0]) <= 1, (
            weight,
            opsz,
            "r left stem edge",
        )
        assert abs(r_coordinates[20][0] - r_coordinates[21][0]) <= 1, (
            weight,
            opsz,
            "r right stem edge",
        )
        assert abs(r_coordinates[11][0] - r_coordinates[12][0]) <= 1, (
            weight,
            opsz,
            "r terminal edge",
        )
        assert all(
            r_coordinates[current][0] < r_coordinates[following][0]
            for current, following in zip(
                (4, 5, 6, 7, 8, 9, 10),
                (5, 6, 7, 8, 9, 10, 11),
            )
        ), (weight, opsz, "r outer shoulder reversal")
        assert all(
            r_coordinates[current][0] > r_coordinates[following][0]
            for current, following in zip(
                (12, 13, 14),
                (13, 14, 15),
            )
        ), (weight, opsz, "r inner shoulder fold")
        aperture = r_coordinates[11][0] - r_coordinates[15][0]
        assert aperture >= max(38, h_vertical_stroke * 0.55), (
            weight,
            opsz,
            "r aperture",
            aperture,
        )
        r_stem = round(r_coordinates[21][0] - r_coordinates[0][0])
        assert abs(r_stem - h_vertical_stroke) <= 9, (
            weight,
            opsz,
            "r/H vertical stroke",
            r_stem,
            h_vertical_stroke,
        )
        assert round(r_coordinates[1][1]) == round(r_coordinates[2][1]), (
            weight,
            opsz,
            "r stem cap",
        )

        assert round(r_cap_coordinates[25][1]) == round(
            r_cap_coordinates[26][1]
        ), (weight, opsz, "R counter lower flat")
        assert round(r_cap_coordinates[34][1]) == round(
            r_cap_coordinates[35][1]
        ), (weight, opsz, "R counter upper flat")

        for source_name, alternate_name in (
            ("O", "O.dotless"),
            ("o", "o.dotless"),
            ("zero", "zero.dotless"),
        ):
            source = instance["glyf"][source_name]
            alternate = instance["glyf"][alternate_name]
            assert source.numberOfContours == 3
            assert alternate.numberOfContours == 2
            assert instance["hmtx"].metrics[source_name] == instance[
                "hmtx"
            ].metrics[alternate_name]
            for contour_index in (0, 1):
                source_contour = contour_signature(
                    instance,
                    source_name,
                    contour_index,
                )
                alternate_contour = contour_signature(
                    instance,
                    alternate_name,
                    contour_index,
                )
                assert len(source_contour) == len(alternate_contour)
                assert all(
                    math.dist(source_point, alternate_point) <= 1.1
                    for source_point, alternate_point in zip(
                        source_contour,
                        alternate_contour,
                    )
                ), (
                    weight,
                    opsz,
                    source_name,
                    "dotless bowl drift",
                )

        semicolon_tail = contour_signature(instance, "semicolon", 1)
        assert len({x for x, _ in semicolon_tail}) > 2, (
            weight,
            opsz,
            "semicolon tail was squared",
        )
        assert len({y for _, y in semicolon_tail}) == 2, (
            weight,
            opsz,
            "semicolon tail lost its two flat ends",
        )

        f_coordinates, _, _ = instance["glyf"]["f"].getCoordinates(
            instance["glyf"]
        )
        l_coordinates, _, _ = instance["glyf"]["l"].getCoordinates(
            instance["glyf"]
        )
        ascender_strokes = (
            round(f_coordinates[9][1] - f_coordinates[10][1]),
            round(l_coordinates[5][1] - l_coordinates[4][1]),
        )
        assert all(
            abs(current - default) <= 1
            for current, default in zip(
                ascender_strokes,
                default_ascender_strokes[weight],
            )
        ), (weight, opsz, "f/l optical-size stroke drift")
        assert all(
            -1 <= h_horizontal_stroke - stroke <= 25
            for stroke in ascender_strokes
        ), (weight, opsz, "f/l top stroke balance")
        assert_clean_contour(instance, "T", 0)

        for glyph_name, contour_indices in SQUARE_CONTOURS.items():
            for contour_index in contour_indices:
                assert_square_contour(instance, glyph_name, contour_index)

        for glyph_name in ("J", "j", "K", "M", "W", "S"):
            bounds = glyph_bounds(instance, glyph_name)
            assert -5 <= bounds[0] <= bounds[2] <= ADVANCE + 5, (
                glyph_name,
                weight,
                opsz,
                bounds,
            )
            assert -250 <= bounds[1] <= bounds[3] <= 800, (
                glyph_name,
                weight,
                opsz,
                bounds,
            )

    default = instantiateVariableFont(
        variable,
        {"wght": 400, "opsz": DEFAULT_OPSZ},
        inplace=False,
    )
    text = instantiateVariableFont(
        variable,
        {"wght": 400, "opsz": TEXT_OPSZ},
        inplace=False,
    )
    display = instantiateVariableFont(
        variable,
        {"wght": 400, "opsz": DISPLAY_OPSZ},
        inplace=False,
    )
    assert glyph_bounds(default, "x")[3] == X_HEIGHT
    assert glyph_bounds(text, "x")[3] == TEXT_X_HEIGHT
    assert glyph_bounds(display, "x")[3] == DISPLAY_X_HEIGHT
    for instance in (text, default, display):
        assert glyph_bounds(instance, "H")[3] == CAP_HEIGHT
        assert glyph_bounds(instance, "K")[3] == CAP_HEIGHT
        assert glyph_bounds(instance, "M")[3] == CAP_HEIGHT
        assert glyph_bounds(instance, "W")[3] == CAP_HEIGHT
        assert glyph_bounds(instance, "j")[3] == LOWERCASE_ASCENDER_HEIGHT
    assert glyph_signature(text, "H") != glyph_signature(display, "H")
    assert glyph_signature(text, "x") != glyph_signature(display, "x")
    assert glyph_signature(text, "J") != glyph_signature(display, "J")
    assert contour_bounds(default, "uni0307", 0) == (
        -356,
        616,
        -244,
        728,
    )

    extra_bold = instantiateVariableFont(
        variable,
        {"wght": 800, "opsz": DEFAULT_OPSZ},
        inplace=False,
    )
    for glyph_name in ("W", "M", "K", "asciicircum"):
        bounds = glyph_bounds(extra_bold, glyph_name)
        assert 0 <= bounds[0] < bounds[2] <= ADVANCE
        assert bounds[3] == CAP_HEIGHT

    h_coordinates, _, _ = default["glyf"]["H"].getCoordinates(
        default["glyf"]
    )
    h_x = sorted({round(x) for x, _ in h_coordinates})
    h_stem = h_x[1] - h_x[0]
    assert h_stem in REGULAR_STEM_RANGE, h_stem
    h_y = sorted({round(y) for _, y in h_coordinates})
    h_horizontal_stem = h_y[-2] - h_y[1]
    assert h_horizontal_stem < h_stem

    for glyph_name, maximum_sidebearing_delta in (
        ("H", 0),
        ("n", 2),
    ):
        bounds = glyph_bounds(default, glyph_name)
        assert abs(bounds[0] - (ADVANCE - bounds[2])) <= (
            maximum_sidebearing_delta
        ), (glyph_name, bounds)

    ligature_names = [
        name
        for name in variable.getGlyphOrder()
        if ".liga" in name
    ]
    assert len(ligature_names) >= 160
    for glyph_name in ligature_names:
        assert variable["hmtx"].metrics[glyph_name][0] == ADVANCE

    reverse_ascii = {
        glyph_name: chr(codepoint)
        for codepoint, glyph_name in variable.getBestCmap().items()
        if 0x20 <= codepoint < 0x7F
    }
    base_ligatures = [
        name
        for name in ligature_names
        if ".liga." not in name
    ]
    optional_ligatures = 0
    for glyph_name in base_ligatures:
        tokens = glyph_name.split(".liga")[0].split("_")
        sequence = "".join(reverse_ascii[token] for token in tokens)
        result = shape(sequence)
        assert result.count(f"+{ADVANCE}") == len(sequence), (
            sequence,
            result,
        )
        assert ".liga" not in result, (sequence, glyph_name, result)
        optional_result = shape(sequence, "dlig=1")
        if sequence not in ALWAYS_LITERAL_LIGATURE_SEQUENCES:
            assert glyph_name in optional_result, (
                sequence,
                glyph_name,
                optional_result,
            )
            assert optional_result.count(f"+{ADVANCE}") == len(sequence)
            optional_ligatures += 1
        else:
            assert glyph_name not in optional_result
    assert len(base_ligatures) == 153
    assert optional_ligatures == 150

    for text_run in ("====", "////", "....", "||||"):
        for features in (None, "dlig=1"):
            result = shape(text_run, features)
            assert ".liga" not in result, (
                text_run,
                features,
                result,
            )

    default_counters = shape("Oo0")
    dotless_counters = shape("Oo0", "ss03=1")
    assert "[O=0+579|o=1+579|zero=2+579]" == default_counters
    assert (
        "[O.dotless=0+579|o.dotless=1+579|zero.dotless=2+579]"
        == dotless_counters
    )

    preserved_count = assert_default_preservation(variable)
    assert_round_dotted_bowls_preserved(variable)

    print(f"PASS: {len(font_paths)} font files parse successfully")
    print("PASS: build report size/hash manifest matches all release files")
    print(f"PASS: all files identify as Version {VERSION}")
    print("PASS: wght 100–800 and opsz 9–72 axes carry 9 named weight instances")
    print("PASS: avar, STAT, HVAR, and gasp metadata are present and coherent")
    print("PASS: transformed outlines are unhinted and request grayscale smoothing")
    print(f"PASS: 95 printable ASCII characters retain a {ADVANCE}-unit advance across the axis grid")
    print("PASS: Text/Auto/Display masters set x-height to 540/528/500 with cap height fixed")
    print("PASS: J/j/K/R/r/M/W/S and punctuation designs interpolate at both axes")
    print("PASS: R/r/K reproduce their exact Book reference drawings")
    print(f"PASS: {reference_dependent_count} accented and cross-script R/r/K derivatives inherit the new bases")
    print("PASS: Thin and ExtraBold drawings retain open counters and cell containment")
    print("PASS: lowercase t keeps a flat cap, parallel ascender, and H-matched crossbar/foot")
    print("PASS: R/r/K keep open counters, monotone joins, and H-matched strokes at every named weight")
    print("PASS: lowercase f/l raised terminals preserve their local stroke through opsz")
    print("PASS: every square dot uses a clean native four-point contour")
    print("PASS: custom outlines contain no duplicate, closing, or zero-area contours")
    print("PASS: O/o/zero stay dotted by default and ss03 exposes bowl-identical dotless alternates")
    print("PASS: i/j marks, diaeresis, dot-below, punctuation, and ellipsis use square dots")
    print("PASS: semicolon keeps its tapered tail instead of squaring it")
    print(f"PASS: {len(ligature_names)} programming glyphs retain one-cell advances")
    print("PASS: 150 programming ligatures remain optional under dlig; 3 stay literal")
    print("PASS: four-character repeats remain literal instead of partially ligating")
    print(f"PASS: Regular H stem {h_stem} with optically lighter {h_horizontal_stem}-unit crossbar")
    print(f"PASS: {preserved_count} non-redrawn encoded glyphs match the archived 1.305 default design")


if __name__ == "__main__":
    main()
