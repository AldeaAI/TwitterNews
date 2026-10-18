"""
Square (1080x1080) image for the daily post: the article's photo as background,
a brand gradient, a kicker pill, an auto-fitted headline, the @AldeaAI handle and the logo.
"""
import os
from io import BytesIO
from typing import Optional
from urllib.parse import urljoin

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ASSETS = os.path.join(os.path.dirname(__file__), "..", "InstagramNews")
FONT_BOLD = os.path.join(ASSETS, "Fonts", "Roboto-Bold.ttf")
FONT_REG = os.path.join(ASSETS, "Fonts", "Roboto-Regular.ttf")
LOGO_PATH = os.path.join(ASSETS, "Backgrounds", "LogoOriginal.png")

SIZE = 1080
MARGIN = 80
CYAN = (51, 196, 255, 255)
DARK = (34, 31, 28)
WHITE = (255, 255, 255, 255)

KICKER = "MERCADO INMOBILIARIO"
HANDLE = "@AldeaAI"

# Headline area: below the kicker, above the handle pill
HEAD_TOP = 640
HEAD_BOTTOM = 940
HEAD_MAX_WIDTH = SIZE - 2 * MARGIN
HEAD_SIZES = range(66, 41, -2)  # largest first, down to 42 px

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _fetch_background(article_url: str) -> Optional[Image.Image]:
    """Return the article's og:image (or twitter:image) as RGBA, or None if unavailable."""
    try:
        from bs4 import BeautifulSoup

        page = requests.get(article_url, timeout=15, headers=_HEADERS)
        page.raise_for_status()
        soup = BeautifulSoup(page.text, "html.parser")
        meta = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if not (meta and meta.get("content")):
            print("[image_post] no og:image found on article page")
            return None
        img_url = urljoin(article_url, meta["content"])
        resp = requests.get(img_url, timeout=15, headers=_HEADERS)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        print(f"[image_post] background fetch failed: {e}")
        return None


def _cover_square(img: Image.Image) -> Image.Image:
    """Scale and center-crop to a SIZE x SIZE square."""
    scale = max(SIZE / img.width, SIZE / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (img.width - SIZE) // 2
    top = (img.height - SIZE) // 2
    return img.crop((left, top, left + SIZE, top + SIZE)).filter(ImageFilter.GaussianBlur(1))


def _gradient(start: int, alpha: int) -> Image.Image:
    """Transparent above `start`, rising to `alpha` at the bottom edge."""
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(SIZE):
        t = min(1.0, max(0.0, (y - start) / (SIZE - start)))
        draw.line([(0, y), (SIZE, y)], fill=(*DARK, int(alpha * t)))
    return layer


def _logo_tile(size: int, pad: int, radius: Optional[int] = None) -> Image.Image:
    """The Aldea logo on a white rounded square."""
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius or size // 7, fill=WHITE)
    logo = Image.open(LOGO_PATH).convert("RGBA").resize((size - 2 * pad,) * 2, Image.LANCZOS)
    tile.alpha_composite(logo, (pad, pad))
    return tile


def _mean_brightness(img: Image.Image) -> float:
    """Average grey level (0-255) of the lower half, where the headline sits."""
    lower = img.convert("L").crop((0, SIZE // 2, SIZE, SIZE))
    return sum(lower.getdata()) / (lower.width * lower.height)


def _fit_headline(text: str):
    """Largest font size where the wrapped headline fits the width and the headline area.

    Returns (font, lines, line_step). If nothing fits even at the smallest size, the text
    is cut to the lines that fit and ends with an ellipsis.
    """
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    smallest = None
    for size in HEAD_SIZES:
        font = ImageFont.truetype(FONT_BOLD, size)
        step = int(size * 1.18)
        lines = _wrap(text, font, probe)
        smallest = (font, lines, step)
        if HEAD_TOP + len(lines) * step <= HEAD_BOTTOM:
            return font, lines, step

    font, lines, step = smallest
    max_lines = (HEAD_BOTTOM - HEAD_TOP) // step
    print(f"[image_post] headline too long, truncated to {max_lines} lines")
    lines = lines[:max_lines]
    lines[-1] = lines[-1].rstrip(" ,.;:") + "…"
    return font, lines, step


def _wrap(text: str, font, draw) -> list:
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= HEAD_MAX_WIDTH:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_post_image(headline: str, article_url: str, out_path: str) -> str:
    """Render the post image to `out_path` and return that path."""
    background = _fetch_background(article_url)
    if background is not None:
        canvas = _cover_square(background)
        # Light backgrounds need more darkening so the white headline stays readable
        if _mean_brightness(canvas) > 140:
            print("[image_post] bright background, adding extra darkening")
            canvas = Image.alpha_composite(canvas, Image.new("RGBA", (SIZE, SIZE), (*DARK, 70)))
            canvas = Image.alpha_composite(canvas, _gradient(start=300, alpha=250))
        else:
            canvas = Image.alpha_composite(canvas, _gradient(start=420, alpha=235))
        logo_in_corner = True
    else:
        # No article photo: brand dark background with the logo centered on a white tile
        print("[image_post] no article image, using logo background")
        canvas = Image.new("RGBA", (SIZE, SIZE), (*DARK, 255))
        tile_size = 380
        tile = _logo_tile(tile_size, 50, radius=tile_size // 8)
        canvas.alpha_composite(tile, ((SIZE - tile_size) // 2, 150))
        logo_in_corner = False

    draw = ImageDraw.Draw(canvas)
    f_kicker = ImageFont.truetype(FONT_BOLD, 32)
    f_handle = ImageFont.truetype(FONT_REG, 32)

    # Kicker pill
    kb = draw.textbbox((0, 0), KICKER, font=f_kicker)
    kw, kh = kb[2] - kb[0] + 48, kb[3] - kb[1] + 26
    draw.rounded_rectangle([(MARGIN, 560), (MARGIN + kw, 560 + kh)], radius=kh // 2, fill=CYAN)
    draw.text((MARGIN + 24, 560 + 13 - kb[1]), KICKER, font=f_kicker, fill=DARK)

    # Headline with a soft shadow for legibility over the photo
    font, lines, step = _fit_headline(headline)
    y = HEAD_TOP
    for line in lines:
        draw.text((MARGIN + 2, y + 3), line, font=font, fill=(0, 0, 0, 120))
        draw.text((MARGIN, y), line, font=font, fill=WHITE)
        y += step

    # Handle pill
    hb = draw.textbbox((0, 0), HANDLE, font=f_handle)
    px, py = 26, 13
    pw, ph = hb[2] - hb[0] + 2 * px, hb[3] - hb[1] + 2 * py
    draw.rounded_rectangle([(MARGIN, 960), (MARGIN + pw, 960 + ph)], radius=ph // 2, fill=WHITE)
    draw.text((MARGIN + px, 960 + py - hb[1]), HANDLE, font=f_handle, fill=DARK)

    # Logo tile, top right (the centered version is already drawn in the fallback)
    if logo_in_corner:
        logo_size = 150
        canvas.alpha_composite(_logo_tile(logo_size, 14), (SIZE - logo_size - MARGIN + 10, MARGIN - 10))

    canvas.convert("RGB").save(out_path, quality=95)
    return out_path
