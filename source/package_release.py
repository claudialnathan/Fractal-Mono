#!/usr/bin/env python3
"""Create a deterministic Fractal Mono release archive."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
from version import VERSION


PROJECT = Path(__file__).resolve().parents[1]

OUTPUT = PROJECT / "archive" / f"FractalMono-v{VERSION}.zip"
FILES = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "OFL.txt",
    "fractal-mono.css",
    "specimen.html",
    "specimen.css",
    "specimen.js",
    "specimen-data.js",
    "code-example.html",
    "ligature-specimen.html",
    "ligature-audit.html",
    "build-report.json",
    "source/DESIGN_NOTES.md",
    "specimens/FractalMono-specimen.png",
    "specimens/FractalMono-specimen.pdf",
    "specimens/FractalMono-outline-proof.svg",
    "specimens/FractalMono-outline-proof.png",
    "specimens/FractalMono-RrK-proof.svg",
    "specimens/FractalMono-RrK-proof.png",
    "specimens/FractalMono-RrK-nodes.svg",
)
DIRECTORIES = ("fonts/desktop", "fonts/web")


def release_files() -> list[Path]:
    paths = [PROJECT / name for name in FILES]
    for directory in DIRECTORIES:
        paths.extend(path for path in (PROJECT / directory).iterdir() if path.is_file())
    missing = [path.relative_to(PROJECT) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing release files: {', '.join(map(str, missing))}")
    return sorted(paths, key=lambda path: path.relative_to(PROJECT).as_posix())


def main() -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in release_files():
            relative = path.relative_to(PROJECT).as_posix()
            info = ZipInfo(relative, date_time=(2026, 7, 30, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)
    size = OUTPUT.stat().st_size
    print(f"Wrote {OUTPUT} ({size:,} bytes)")


if __name__ == "__main__":
    main()
