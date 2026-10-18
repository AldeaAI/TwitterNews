"""
Square (1080x1080) text-only images for the daily post. There are 12 layouts that share the
brand palette, logo and fonts; each run uses a different one so the posts don't all look the same.
No article photos are used, to avoid copyright issues.
"""
import os
from datetime import datetime, timezone
from typing import Callable, List, Optional

from PIL import Image, ImageDraw, ImageFont

ASSETS = os.path.join(os.path.dirname(__file__), "..", "InstagramNews")
FONT_BOLD = os.path.join(ASSETS, "Fonts", "Roboto-Bold.ttf")
FONT_REG = os.path.join(ASSETS, "Fonts", "Roboto-Regular.ttf")
LOGO_PATH = os.path.join(ASSETS, "Backgrounds", "LogoOriginal.png")

SIZE = 1080
MARGIN = 80
CYAN = (51, 196, 255, 255)
BLUE = (13, 58, 229, 255)
NAVY = (7, 28, 120, 255)
DARK = (34, 31, 28, 255)
OFF_WHITE = (246, 247, 249, 255)
WHITE = (255, 255, 255, 255)

KICKER = "MERCADO INMOBILIARIO"
HANDLE = "@AldeaAI"
RUNS_PER_DAY = 2  # the workflow runs twice a day (14:00 and 20:00 UTC)

_BOLD_CACHE = {}


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _BOLD_CACHE:
        _BOLD_CACHE[key] = ImageFont.truetype(path, size)
    return _BOLD_CACHE[key]


def _logo_tile(size: int, pad: int) -> Image.Image:
    """The Aldea logo on a white rounded square."""
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=size // 7, fill=WHITE)
    logo = Image.open(LOGO_PATH).convert("RGBA").resize((size - 2 * pad,) * 2, Image.LANCZOS)
    tile.alpha_composite(logo, (pad, pad))
    return tile


def _gradient(c1, c2) -> Image.Image:
    """Diagonal gradient from c1 (top-left) to c2 (bottom-right)."""
    layer = Image.new("RGBA", (SIZE, SIZE))
    draw = ImageDraw.Draw(layer)
    for i in range(2 * SIZE):
        t = min(1.0, i / (2 * SIZE))
        color = tuple(int(c1[k] * (1 - t) + c2[k] * t) for k in range(3)) + (255,)
        draw.line([(i, 0), (0, i)], fill=color, width=2)
    return layer


def _wrap(text: str, font, width: int) -> List[str]:
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if probe.textbbox((0, 0), trial, font=font)[2] <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _headline(canvas, text: str, x: int, y: int, width: int, bottom: int, color,
              align: str = "left", sizes=range(66, 41, -2)) -> None:
    """Draw the headline at the largest size that fits the width and the space down to `bottom`."""
    draw = ImageDraw.Draw(canvas)
    for size in sizes:
        font = _font(FONT_BOLD, size)
        step = int(size * 1.27)
        lines = _wrap(text, font, width)
        if y + len(lines) * step <= bottom:
            break
    else:
        # Nothing fits: keep the lines that fit and end with an ellipsis
        max_lines = max(1, (bottom - y) // step)
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" ,.;:") + "…"
        print(f"[image_post] headline too long, truncated to {max_lines} lines")
    for line in lines:
        w = draw.textbbox((0, 0), line, font=font)[2]
        xx = _align_x(align, x, width, w)
        draw.text((xx, y), line, font=font, fill=color)
        y += step


def _align_x(align: str, x: int, width: int, w: int) -> int:
    if align == "center":
        return x + (width - w) // 2
    return x


def _kicker(canvas, x: int, y: int, color, align: str = "left", width: int = 0) -> None:
    draw = ImageDraw.Draw(canvas)
    font = _font(FONT_BOLD, 34)
    w = draw.textbbox((0, 0), KICKER, font=font)[2]
    draw.text((_align_x(align, x, width, w), y), KICKER, font=font, fill=color)


def _pill(canvas, x: int, y: int, bg, fg, align: str = "left", width: int = 0) -> None:
    draw = ImageDraw.Draw(canvas)
    font = _font(FONT_REG, 34)
    b = draw.textbbox((0, 0), HANDLE, font=font)
    px, py = 28, 14
    w, h = b[2] - b[0] + 2 * px, b[3] - b[1] + 2 * py
    xx = _align_x(align, x, width, w)
    draw.rounded_rectangle([(xx, y), (xx + w, y + h)], radius=h // 2, fill=bg)
    draw.text((xx + px, y + py - b[1]), HANDLE, font=font, fill=fg)


def _new(bg) -> Image.Image:
    return Image.new("RGBA", (SIZE, SIZE), bg)


# Each layout takes the headline text and returns the finished canvas.
# Coordinates are in pixels on the 1080x1080 square.

def _layout_1(text):  # off-white, cyan top-left and blue bottom-right triangles
    c = _new(OFF_WHITE); d = ImageDraw.Draw(c)
    d.polygon([(0, 0), (300, 0), (0, 240)], fill=CYAN)
    d.polygon([(SIZE, SIZE), (SIZE, 800), (640, SIZE)], fill=BLUE)
    c.alpha_composite(_logo_tile(170, 16), (SIZE - 170 - MARGIN + 10, MARGIN - 10))
    _kicker(c, MARGIN, 400, BLUE)
    _headline(c, text, MARGIN, 460, SIZE - 2 * MARGIN - 120, 900, DARK)
    _pill(c, MARGIN, 960, BLUE, WHITE)
    return c


def _layout_2(text):  # off-white with a thin blue bar on top, logo left
    c = _new(OFF_WHITE)
    ImageDraw.Draw(c).rectangle([(0, 0), (SIZE, 16)], fill=BLUE)
    c.alpha_composite(_logo_tile(150, 14), (MARGIN, MARGIN + 20))
    _kicker(c, MARGIN, 420, CYAN)
    _headline(c, text, MARGIN, 480, SIZE - 2 * MARGIN, 900, DARK)
    _pill(c, MARGIN, 960, DARK, WHITE)
    return c


def _layout_3(text):  # dark, cyan top-left corner, logo top-right
    c = _new(DARK)
    ImageDraw.Draw(c).polygon([(0, 0), (260, 0), (0, 200)], fill=CYAN)
    c.alpha_composite(_logo_tile(170, 16), (SIZE - 170 - MARGIN + 10, MARGIN - 10))
    _kicker(c, MARGIN, 400, CYAN)
    _headline(c, text, MARGIN, 460, SIZE - 2 * MARGIN, 900, WHITE)
    _pill(c, MARGIN, 960, BLUE, WHITE)
    return c


def _layout_4(text):  # dark, blue bottom-right corner, logo bottom-left
    c = _new(DARK)
    ImageDraw.Draw(c).polygon([(SIZE, SIZE), (SIZE, 560), (560, SIZE)], fill=BLUE)
    c.alpha_composite(_logo_tile(130, 12), (MARGIN, MARGIN))
    _kicker(c, MARGIN, 320, CYAN)
    _headline(c, text, MARGIN, 380, SIZE - 2 * MARGIN - 200, 900, WHITE)
    _pill(c, MARGIN, 960, WHITE, DARK)
    return c


def _layout_5(text):  # dark, cyan band across the top third, logo centered in the band
    c = _new(DARK)
    ImageDraw.Draw(c).rectangle([(0, 0), (SIZE, 300)], fill=CYAN)
    c.alpha_composite(_logo_tile(180, 18), ((SIZE - 180) // 2, 60))
    _kicker(c, MARGIN, 380, CYAN)
    _headline(c, text, MARGIN, 440, SIZE - 2 * MARGIN, 900, WHITE)
    _pill(c, MARGIN, 960, BLUE, WHITE)
    return c


def _layout_6(text):  # diagonal blue-to-navy gradient, white text, logo top-right
    c = _gradient(BLUE, NAVY)
    c.alpha_composite(_logo_tile(150, 14), (SIZE - 150 - MARGIN + 10, MARGIN - 10))
    _kicker(c, MARGIN, 400, WHITE)
    _headline(c, text, MARGIN, 460, SIZE - 2 * MARGIN, 900, WHITE)
    _pill(c, MARGIN, 960, WHITE, BLUE)
    return c


def _layout_7(text):  # off-white, centered, logo centered at the top
    c = _new(OFF_WHITE)
    c.alpha_composite(_logo_tile(190, 20), ((SIZE - 190) // 2, 90))
    _kicker(c, MARGIN, 400, BLUE, "center", SIZE - 2 * MARGIN)
    _headline(c, text, MARGIN, 460, SIZE - 2 * MARGIN, 880, DARK, "center")
    _pill(c, 0, 960, BLUE, WHITE, "center", SIZE)
    return c


def _layout_8(text):  # off-white, cyan vertical bar, text indented
    c = _new(OFF_WHITE)
    ImageDraw.Draw(c).rectangle([(MARGIN, 380), (MARGIN + 14, 880)], fill=CYAN)
    c.alpha_composite(_logo_tile(140, 12), (SIZE - 140 - MARGIN + 10, MARGIN - 10))
    _kicker(c, MARGIN + 50, 380, BLUE)
    _headline(c, text, MARGIN + 50, 440, SIZE - 2 * MARGIN - 120, 900, DARK)
    _pill(c, MARGIN + 50, 960, DARK, WHITE)
    return c


def _layout_9(text):  # dark, centered, logo centered at the top
    c = _new(DARK)
    c.alpha_composite(_logo_tile(170, 16), ((SIZE - 170) // 2, 80))
    _kicker(c, MARGIN, 360, CYAN, "center", SIZE - 2 * MARGIN)
    _headline(c, text, MARGIN, 420, SIZE - 2 * MARGIN, 900, WHITE, "center")
    _pill(c, 0, 960, CYAN, DARK, "center", SIZE)
    return c


def _layout_10(text):  # off-white with a blue block behind the headline
    c = _new(OFF_WHITE)
    ImageDraw.Draw(c).rectangle([(0, 430), (SIZE, 850)], fill=BLUE)
    c.alpha_composite(_logo_tile(150, 14), (MARGIN, MARGIN + 20))
    _kicker(c, MARGIN, 360, BLUE)
    _headline(c, text, MARGIN, 470, SIZE - 2 * MARGIN, 840, WHITE)
    _pill(c, MARGIN, 930, OFF_WHITE, BLUE)
    return c


def _layout_11(text):  # dark, cyan diagonal line near the bottom
    c = _new(DARK)
    ImageDraw.Draw(c).polygon([(0, 900), (SIZE, 780), (SIZE, 820), (0, 920)], fill=CYAN)
    c.alpha_composite(_logo_tile(150, 14), (SIZE - 150 - MARGIN + 10, MARGIN - 10))
    _kicker(c, MARGIN, 250, CYAN)
    _headline(c, text, MARGIN, 310, SIZE - 2 * MARGIN, 700, WHITE)
    _pill(c, MARGIN, 960, BLUE, WHITE)
    return c


def _layout_12(text):  # off-white top, blue bottom with the logo on the seam
    c = _new(OFF_WHITE)
    ImageDraw.Draw(c).rectangle([(0, 640), (SIZE, SIZE)], fill=BLUE)
    c.alpha_composite(_logo_tile(190, 20), ((SIZE - 190) // 2, 640 - 95))
    _kicker(c, MARGIN, 300, BLUE, "center", SIZE - 2 * MARGIN)
    _headline(c, text, MARGIN, 770, SIZE - 2 * MARGIN, 900, WHITE, "center", range(56, 41, -2))
    _pill(c, 0, 960, WHITE, BLUE, "center", SIZE)
    return c


LAYOUTS: List[Callable[[str], Image.Image]] = [
    _layout_1, _layout_2, _layout_3, _layout_4, _layout_5, _layout_6,
    _layout_7, _layout_8, _layout_9, _layout_10, _layout_11, _layout_12,
]


def layout_index(now: Optional[datetime] = None) -> int:
    """Pick the layout for this run: a different one for each run, cycling through all of them."""
    now = now or datetime.now(timezone.utc)
    # Two runs a day: the first run of the day gets an even slot, the second an odd one
    run_of_day = 0 if now.hour < 17 else 1
    slot = (now.timetuple().tm_yday - 1) * RUNS_PER_DAY + run_of_day
    return slot % len(LAYOUTS)


def build_post_image(text: str, out_path: str, layout: Optional[int] = None) -> str:
    """Render the post image to `out_path` (a .jpg path is saved as JPEG) and return that path."""
    index = layout_index() if layout is None else layout
    print(f"[image_post] layout {index + 1} of {len(LAYOUTS)}")
    canvas = LAYOUTS[index](text)
    canvas.convert("RGB").save(out_path, quality=95)
    return out_path
