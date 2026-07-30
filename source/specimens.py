#!/usr/bin/env python3
"""Render the PNG and PDF specimens for the current build."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

PROJECT = Path(__file__).resolve().parents[1]
DESKTOP = PROJECT / "fonts" / "desktop"
SPECIMENS = PROJECT / "specimens"

BG = (243, 242, 237)
INK = (22, 23, 19)
MUTED = (108, 109, 103)
DARK_BG = (7, 8, 8)
DARK_GRID = (25, 28, 28)
DARK_MUTED = (128, 134, 132)
WHITE = (250, 250, 248)
CELL_BLUE = (51, 128, 255)
WIDTH = 1680
MARGIN = 96
ADVANCE = 579

VARIABLE = DESKTOP / "FractalMono-Variable.ttf"

WEIGHTS = {
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


def font(style: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(DESKTOP / f"FractalMono-{style}.ttf"), size)


def variable_font(weight: int, optical_size: int, size: int) -> ImageFont.FreeTypeFont:
    source = TTFont(VARIABLE)
    instance = instantiateVariableFont(
        source,
        {"wght": weight, "opsz": optical_size},
        inplace=True,
        optimize=True,
    )
    stream = BytesIO()
    instance.save(stream)
    stream.seek(0)
    return ImageFont.truetype(stream, size)


def canvas(height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, height), BG)
    return image, ImageDraw.Draw(image)


def specimen() -> Image.Image:
    image, draw = canvas(1560)
    y = MARGIN
    draw.text((MARGIN, y), "Fractal MONO", font=font("Medium", 132), fill=INK)
    y += 190
    draw.text(
        (MARGIN, y),
        "v1.305 — wght 100–800 · opsz 9–72 · ligatures opt-in",
        font=font("Regular", 34),
        fill=MUTED,
    )
    y += 96
    for line, size, style in (
        ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 56, "Regular"),
        ("abcdefghijklmnopqrstuvwxyz", 56, "Regular"),
        ("0123456789  0O 1Il 5S 8B", 56, "Regular"),
        ("@ # $ % & * + - = / \\ () [] {} <> . , : ; ! ? _", 56, "Regular"),
    ):
        draw.text((MARGIN, y), line, font=font(style, size), fill=INK)
        y += 96
    y += 40
    for size in (21, 28, 38, 52, 72):
        sample = "Telltale toolkit network — return x0 !== 0x1F?"
        if size > 52:
            sample = "Telltale toolkit network"
        draw.text((MARGIN, y), sample, font=font("Regular", size), fill=INK)
        y += int(size * 1.75)
    return image


def weights() -> Image.Image:
    image, draw = canvas(1120)
    y = MARGIN
    draw.text((MARGIN, y), "Weights 100-800", font=font("Medium", 54), fill=INK)
    y += 130
    for weight, style in WEIGHTS.items():
        draw.text((MARGIN, y), f"{weight}", font=font("Regular", 30), fill=MUTED)
        draw.text(
            (MARGIN + 130, y - 10),
            "Human systems, clearly expressed.",
            font=font(style, 52),
            fill=INK,
        )
        y += 96
    return image


def refinement() -> Image.Image:
    image, draw = canvas(1020)
    y = MARGIN
    draw.text(
        (MARGIN, y),
        "Fractal Mono 1.305 · Claudia Nathan",
        font=font("Medium", 54),
        fill=INK,
    )
    y += 110
    draw.text(
        (MARGIN, y),
        "cap 680 · x-height 528 · ascenders 728 · 579 cell · stems 80 · ligatures off · optional dlig",
        font=font("Regular", 30),
        fill=MUTED,
    )
    y += 90

    sample = "Telltale network 0123456789 rtkwo"
    draw.text((MARGIN, y), "Fractal Mono · designed by Claudia Nathan", font=font("Regular", 26), fill=MUTED)
    y += 48
    draw.text((MARGIN, y), sample, font=font("Regular", 56), fill=INK)
    y += 110

    y += 30
    draw.text((MARGIN, y), "custom r t k w across the axis", font=font("Regular", 26), fill=MUTED)
    y += 56
    x = MARGIN
    for style in ("Thin", "Light", "Regular", "Medium", "Bold", "ExtraBold"):
        draw.text((x, y), "rtkw", font=font(style, 100), fill=INK)
        x += 248
    return image


def rk_proof() -> Image.Image:
    """Dark outline-and-spacing proof for close contour inspection."""
    image = Image.new("RGB", (WIDTH, 900), DARK_BG)
    draw = ImageDraw.Draw(image)
    for x in range(0, WIDTH, 24):
        draw.line((x, 0, x, 900), fill=DARK_GRID, width=1)
    for y in range(0, 900, 24):
        draw.line((0, y, WIDTH, y), fill=DARK_GRID, width=1)

    draw.text((MARGIN, 54), "Fractal Mono K / r t k w construction proof", font=font("Regular", 32), fill=DARK_MUTED)
    for row, style in enumerate(("Thin", "Regular", "ExtraBold")):
        y = 150 + row * 235
        draw.text((MARGIN, y + 68), style, font=font("Regular", 25), fill=DARK_MUTED)
        draw.text((280, y), "K r t k w", font=font(style, 130), fill=WHITE)
        draw.text((1040, y + 46), "return  toolkit", font=font(style, 64), fill=WHITE)
    return image


def cell_fit() -> Image.Image:
    """Show the invariant advance cells and the optical padding inside them."""
    image, draw = canvas(700)
    draw.text((MARGIN, 62), "Lowercase optical cell fitting", font=font("Medium", 48), fill=INK)
    draw.text(
        (MARGIN, 128),
        "Every blue frame is the same 579-unit advance; only the ink fit changes.",
        font=font("Regular", 26),
        fill=MUTED,
    )

    size = 96
    cell = ADVANCE / 1000 * size
    row_y = 190
    draw.text((MARGIN, row_y), "abcdefghijklmnopqrstuvwxyz", font=font("Regular", size), fill=INK)
    for index in range(26):
        x = MARGIN + index * cell
        draw.rectangle((round(x), row_y + 8, round(x + cell), row_y + 102), outline=CELL_BLUE, width=1)

    draw.text((MARGIN, 370), "minimum  aluminum  formal  qr rs ro", font=font("Regular", 70), fill=INK)
    draw.text(
        (MARGIN, 510),
        "hijklmn · qrst · algorithm · programming",
        font=font("Regular", 48),
        fill=MUTED,
    )
    return image


def curve_size_comparison() -> Image.Image:
    """Compare the Text, Auto, and Display optical drawings."""
    image, draw = canvas(1240)
    draw.text((MARGIN, 62), "Optical-size masters", font=font("Medium", 48), fill=INK)
    draw.text(
        (MARGIN, 132),
        "A fixed 579-unit cell with a taller Text x-height and a calmer Display drawing.",
        font=font("Regular", 25),
        fill=MUTED,
    )

    sample = "Interface rhythm  0Oo iïj  Whether its a year"
    rows = (
        ("Text 9", variable_font(400, 9, 74)),
        ("Auto 14", variable_font(400, 14, 74)),
        ("Display 72", variable_font(400, 72, 74)),
    )
    y = 220
    for label, row_font in rows:
        draw.text((MARGIN, y), label, font=font("Regular", 24), fill=MUTED)
        draw.text((MARGIN, y + 42), sample, font=row_font, fill=INK)
        y += 145

    draw.text((MARGIN, y + 12), "Signature forms remain stable as internal proportions change", font=font("Regular", 24), fill=MUTED)
    draw.text((MARGIN, y + 54), "Jj K M W S  !?^;:*  return toolkit", font=variable_font(400, 14, 74), fill=INK)
    y += 180

    draw.text((MARGIN, y), "Text and Display at a true 13 px raster, enlarged 6×", font=font("Regular", 24), fill=MUTED)
    y += 48
    strip_text = "lilac build 0189"
    small_rows = (
        ("Text 9", variable_font(400, 9, 13)),
        ("Display 72", variable_font(400, 72, 13)),
    )
    x = MARGIN
    for label, row_font in small_rows:
        strip = Image.new("RGB", (210, 24), (255, 255, 253))
        strip_draw = ImageDraw.Draw(strip)
        strip_draw.line((0, 1, 209, 1), fill=CELL_BLUE, width=1)
        strip_draw.line((0, 20, 209, 20), fill=CELL_BLUE, width=1)
        strip_draw.text((4, 17), strip_text, font=row_font, fill=INK, anchor="ls")
        enlarged = strip.resize((1260, 144), Image.Resampling.NEAREST)
        cropped = enlarged.crop((0, 0, 460, 144))
        draw.text((x, y), label, font=font("Regular", 22), fill=MUTED)
        image.paste(cropped, (x, y + 34))
        x += 500
    return image


def final_polish() -> Image.Image:
    """High-magnification proof of square dots and extreme-weight fitting."""
    image, draw = canvas(1760)
    draw.text((MARGIN, 62), "Square details and extreme weights", font=font("Medium", 48), fill=INK)
    draw.text(
        (MARGIN, 128),
        "Native square contours, clean joins, and open counters from Thin to ExtraBold.",
        font=font("Regular", 25),
        fill=MUTED,
    )

    y = 210
    for label, row_font in (
        ("Thin 100", variable_font(100, 14, 168)),
        ("Regular 400", variable_font(400, 14, 168)),
        ("ExtraBold 800", variable_font(800, 14, 168)),
    ):
        draw.text((MARGIN, y), label, font=font("Regular", 24), fill=MUTED)
        draw.text((MARGIN, y + 40), "Jj K M W S  t i j", font=row_font, fill=INK)
        draw.text((MARGIN, y + 220), "!? ^ ; : *  O o 0", font=row_font, fill=INK)
        y += 400

    new = variable_font(400, 14, 168)
    draw.text((MARGIN, y), "Default punctuation fit", font=font("Regular", 24), fill=MUTED)
    draw.text((MARGIN, y + 38), "O o 0   . : ; ! ? i j", font=new, fill=INK)
    draw.text(
        (MARGIN, y + 235),
        "Square dots use four on-curve points with no collapsed or overlapping segments.",
        font=font("Regular", 25),
        fill=MUTED,
    )
    return image


def main() -> None:
    SPECIMENS.mkdir(exist_ok=True)
    pages = {
        "FractalMono-specimen.png": specimen(),
        "FractalMono-weights.png": weights(),
        "FractalMono-refinement.png": refinement(),
        "FractalMono-r-k-proof.png": rk_proof(),
        "FractalMono-cell-fit.png": cell_fit(),
        "FractalMono-curve-size-comparison.png": curve_size_comparison(),
        "FractalMono-final-polish.png": final_polish(),
    }
    for name, image in pages.items():
        image.save(SPECIMENS / name)
    first, *rest = pages.values()
    first.save(SPECIMENS / "FractalMono-specimen.pdf", save_all=True, append_images=rest, resolution=150)


if __name__ == "__main__":
    main()
