#!/usr/bin/env python3
"""Create a deterministic CLN Mono release archive."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


PROJECT = Path(__file__).resolve().parents[1]
VERSION = "1.304"
OUTPUT = PROJECT / "archive" / f"CLNMono-v{VERSION}.zip"
FILES = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "OFL.txt",
    "cln-mono.css",
    "specimen.html",
    "specimen.css",
    "specimen.js",
    "specimen-data.js",
    "code-example.html",
    "ligature-specimen.html",
    "ligature-audit.html",
    "build-report.json",
    "source/DESIGN_NOTES.md",
    "specimens/CLNMono-specimen.png",
    "specimens/CLNMono-specimen.pdf",
    "specimens/CLNMono-outline-proof.svg",
    "specimens/CLNMono-outline-proof.png",
    "specimens/CLNMono-RrK-proof.svg",
    "specimens/CLNMono-RrK-proof.png",
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
