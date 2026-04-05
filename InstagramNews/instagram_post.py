import os
import requests
from PIL import Image, ImageDraw, ImageFont
import textwrap
from io import BytesIO

def extract_link(text):
    import re
    match = re.search(r'https?://\S+', text)
    return match.group(0) if match else None

def remove_link(text):
    import re
    return re.sub(r'https?://\S+', '', text).strip()

def remove_hashtag(text, hashtag="#AldeaAI"):
    import re
    return re.sub(rf"\s*{re.escape(hashtag)}\b", "", text)

_BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-CO,es;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

def fetch_overlay_image(url):
    try:
        # Use image-specific Accept header for the image fetch
        img_headers = dict(_BROWSER_HEADERS)
        img_headers['Accept'] = 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
        img_headers['Sec-Fetch-Dest'] = 'image'
        img_headers['Sec-Fetch-Mode'] = 'no-cors'
        resp = requests.get(url, timeout=15, headers=img_headers)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert('RGBA')
        return img
    except Exception as e:
        print(f"[fetch_overlay_image] failed: {e}")
        return None

def extract_og_or_twitter_image(url):
    try:
        resp = requests.get(url, timeout=15, headers=_BROWSER_HEADERS)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        og = soup.find('meta', property='og:image')
        tw = soup.find('meta', attrs={'name': 'twitter:image'})
        if og and og.get('content'):
            print(f"[extract_og_or_twitter_image] found og:image: {og['content']}")
            return og['content']
        if tw and tw.get('content'):
            print(f"[extract_og_or_twitter_image] found twitter:image: {tw['content']}")
            return tw['content']
        print(f"[extract_og_or_twitter_image] no og:image or twitter:image found for {url}")
    except Exception as e:
        print(f"[extract_og_or_twitter_image] failed: {e}")
    return None

def generate_instagram_image(text, output_path, font_path=None, font_size=48, max_width=40, overlay_url=None):
    """
    Generate an Instagram-ready image with the given text over the website image (or white background).
    """
    bg_size = (1080, 1080)
    print(f"[generate_instagram_image] overlay_url={overlay_url}")
    if overlay_url:
        overlay_img = fetch_overlay_image(overlay_url)
        if overlay_img:
            print(f"[generate_instagram_image] overlay image fetched OK, size={overlay_img.size}")
            # Resize overlay_img to fit bg_size without deformation
            ow, oh = overlay_img.size
            bw, bh = bg_size
            scale = min(bw / ow, bh / oh)
            new_size = (int(ow * scale), int(oh * scale))
            overlay_img = overlay_img.resize(new_size, Image.LANCZOS)
            # Center overlay_img on a blank background
            base = Image.new('RGBA', bg_size, (255,255,255,255))
            paste_x = (bw - new_size[0]) // 2
            paste_y = (bh - new_size[1]) // 2
            base.alpha_composite(overlay_img, (paste_x, paste_y))
        else:
            print("[generate_instagram_image] overlay image fetch returned None, using white background")
            base = Image.new('RGBA', bg_size, (255,255,255,255))
    else:
        print("[generate_instagram_image] no overlay_url provided, using white background")
        base = Image.new('RGBA', bg_size, (255,255,255,255))
    image = base.copy()
    draw = ImageDraw.Draw(image)

    def wrap_text_fixed_width(text, font, draw, width, margin):
        # Wrap text so that no line exceeds the allowed width, but keep font size fixed
        words = text.split()
        lines = []
        current_line = ''
        for word in words:
            test_line = current_line + (' ' if current_line else '') + word
            line_width = draw.textbbox((0,0), test_line, font=font)[2]
            if line_width <= width - 2*margin:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    # Use fixed font size, no dynamic adjustment
    font_size = int(font_size * 0.8)  # Reduce font size by 20%
    if font_path and os.path.exists(font_path):
        font = ImageFont.truetype(font_path, font_size)
    else:
        try:
            font = ImageFont.truetype("Roboto-Regular.ttf", font_size)
        except:
            font = ImageFont.load_default()
    width, height = image.size
    padding = 40
    margin = 40
    lines = wrap_text_fixed_width(text, font, draw, width, margin)
    line_spacing = int(font_size * 0.3)
    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    line_heights = [line_height for _ in lines]
    text_height = sum(line_heights) + line_spacing * (len(lines) - 1)
    box_width = width
    box_height = text_height + 2 * padding
    box_x = 0
    box_y = height - box_height
    box_color = (34, 31, 28, 230)  # 90% opacity (255 * 0.9 ≈ 230)
    rectangle = Image.new('RGBA', (box_width, box_height), (0,0,0,0))
    rect_draw = ImageDraw.Draw(rectangle)
    rect_draw.rectangle([(0,0),(box_width,box_height)], fill=box_color)
    image.alpha_composite(rectangle, (box_x, box_y))
    y_text = box_y + padding
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0,0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x_text = margin
        draw.text((x_text, y_text), line, font=font, fill=(255,255,255,255))
        y_text += line_height
        if i < len(lines) - 1:
            y_text += line_spacing
    # Add logo to top right corner
    logo_path = os.path.join(os.path.dirname(__file__), 'Backgrounds', 'LogoOriginal.png')
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert('RGBA')
        logo_width = width // 8
        logo_ratio = logo_width / logo.width
        logo_height = int(logo.height * logo_ratio)
        logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
        logo_margin = 40
        logo_x = width - logo_width - logo_margin
        logo_y = logo_margin
        image.alpha_composite(logo, (logo_x, logo_y))
    # Add Instagram handle box to top left
    insta_logo_path = os.path.join(os.path.dirname(__file__), 'Backgrounds', 'InstagramLogo.png')
    handle_font_size = int(font_size * 0.6)
    handle_box_padding = 10
    handle_box_margin = 40  # Match logo margin
    handle_box_color = (255, 255, 255, 255)
    handle_text_color = (0, 0, 0, 255)
    roboto_path = os.path.join(os.path.dirname(__file__), 'Fonts', 'Roboto-Regular.ttf')
    try:
        roboto_font = ImageFont.truetype(roboto_path, handle_font_size)
    except:
        roboto_font = font
    at_text = "@AldeaAI"
    # Measure logo
    if os.path.exists(insta_logo_path):
        logo_img = Image.open(insta_logo_path).convert('RGBA')
        logo_height = handle_font_size + 8  # Slightly larger than text
        logo_ratio = logo_height / logo_img.height
        logo_width = int(logo_img.width * logo_ratio)
        logo_img = logo_img.resize((logo_width, logo_height), Image.LANCZOS)
    else:
        logo_img = None
        logo_width = 0
        logo_height = handle_font_size + 8
    # Measure text
    at_bbox = roboto_font.getbbox(at_text)
    at_text_width = at_bbox[2] - at_bbox[0]
    at_text_height = at_bbox[3] - at_bbox[1]
    # Calculate box size tightly
    handle_box_height = max(logo_height, at_text_height) + 2 * handle_box_padding
    handle_box_width = logo_width + at_text_width + 3 * handle_box_padding
    # Draw rounded rectangle box
    handle_box = Image.new('RGBA', (handle_box_width, handle_box_height), (0,0,0,0))
    handle_draw = ImageDraw.Draw(handle_box)
    radius = handle_box_height // 2
    handle_draw.rounded_rectangle([(0,0),(handle_box_width,handle_box_height)], radius=radius, fill=handle_box_color)
    # Draw logo
    if logo_img:
        logo_x = handle_box_padding
        logo_y = (handle_box_height - logo_height) // 2
        handle_box.alpha_composite(logo_img, (logo_x, logo_y))
    # Draw text
    at_x = logo_width + 2 * handle_box_padding
    at_y = (handle_box_height - at_text_height) // 2 - at_bbox[1]
    handle_draw.text((at_x, at_y), at_text, font=roboto_font, fill=handle_text_color)
    # Paste box on main image, aligned with logo top
    logo_top_y = logo_margin if 'logo_margin' in locals() else 40
    image.alpha_composite(handle_box, (handle_box_margin, logo_top_y))
    image.save(output_path)
    return output_path

INSTAGRAM_DEVICE_SETTINGS = {
    "app_version": "269.0.0.18.75",
    "android_version": 26,
    "android_release": "8.0.0",
    "dpi": "480dpi",
    "resolution": "1080x1920",
    "manufacturer": "OnePlus",
    "device": "ONEPLUS A3010",
    "model": "OnePlus3T",
    "cpu": "qcom",
    "version_code": "314665256",
}

def post_to_instagram(image_path, caption, username=None, password=None, session_file=None):
    from instagrapi import Client
    if not username or not password:
        raise ValueError("Instagram username and password are required.")
    cl = Client()
    cl.set_device(INSTAGRAM_DEVICE_SETTINGS)
    logged_in = False
    # Try to reuse an existing session without re-logging in
    if session_file and os.path.exists(session_file):
        try:
            cl.load_settings(session_file)
            cl.set_user(username, password)
            # Validate session is still alive without triggering a fresh login
            cl.get_timeline_feed()
            logged_in = True
        except Exception:
            logged_in = False
    # Fall back to full login if session missing or expired
    if not logged_in:
        cl = Client()
        cl.set_device(INSTAGRAM_DEVICE_SETTINGS)
        cl.login(username, password)
        if session_file:
            cl.dump_settings(session_file)
    media = cl.photo_upload(image_path, caption)
    return media

def create_and_optionally_post_instagram(text, output_path, font_path=None, username=None, password=None, article_url=None, session_file=None):
    link = extract_link(text)
    text_no_link = remove_link(text)
    text_no_link = remove_hashtag(text_no_link, hashtag="#AldeaAI")
    caption = f"Fuente: {link}" if link else ""
    print(f"[create_and_optionally_post_instagram] article_url={article_url}")
    overlay_url = extract_og_or_twitter_image(article_url) if article_url else None
    print(f"[create_and_optionally_post_instagram] overlay_url resolved to: {overlay_url}")
    image_path = generate_instagram_image(text_no_link, output_path, font_path, overlay_url=overlay_url)
    post_result = None
    if username and password:
        post_result = post_to_instagram(image_path, caption, username, password, session_file=session_file)
    return image_path, caption, post_result
