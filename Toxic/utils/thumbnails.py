import os
import re
import math
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch

from Toxic import app
from config import YOUTUBE_IMG_URL, OWNER_NAME  # OWNER_NAME config me add karna

# ---------- helpers ----------
META_CACHE = {}  # {videoid: {"title":..., "duration": "m:ss", "channel":..., "thumb": path}}

def _mmss_to_sec(s: str) -> int:
    try:
        parts = s.split(":")
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return h*3600 + m*60 + s
        if len(parts) == 2:
            m, s = int(parts[0]), int(parts[1])
            return m*60 + s
        return int(s)
    except Exception:
        return 0

def _sec_to_mmss(sec: float) -> str:
    sec = max(0, int(sec))
    return f"{sec//60}:{sec%60:02d}"

def _font(path, size, fallback=None):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        # very small bitmap fallback
        return ImageFont.load_default()

async def _fetch_meta(videoid: str):
    if videoid in META_CACHE:
        return META_CACHE[videoid]

    url = f"https://www.youtube.com/watch?v={videoid}"
    results = VideosSearch(url, limit=1)
    data = (await results.next())["result"][0]

    title = re.sub(r"\s+", " ", data.get("title", "Unknown Song")).strip()
    duration = data.get("duration", "0:00")
    channel = data.get("channel", {}).get("name", "Unknown Artist")
    thumb_url = data["thumbnails"][0]["url"].split("?")[0]

    # download cover
    tmp_path = f"cache/thumb{videoid}.png"
    async with aiohttp.ClientSession() as session:
        async with session.get(thumb_url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(tmp_path, mode="wb")
                await f.write(await resp.read())
                await f.close()

    META_CACHE[videoid] = {
        "title": title,
        "duration": duration,
        "channel": channel,
        "tmp": tmp_path,
    }
    return META_CACHE[videoid]

# ---------- main ----------
async def get_thumb(
    videoid: str,
    position: float = 0.0,          # current playback seconds
    total: int | None = None,       # override total secs; else parsed from YouTube duration
):
    """
    Generate an iOS-style now playing thumbnail PNG with real-time progress.

    Call this repeatedly with updated `position` while the track plays.
    Returns: cache/{videoid}.png
    """
    out_path = f"cache/{videoid}.png"

    try:
        meta = await _fetch_meta(videoid)
        title = meta["title"]
        duration_str = meta["duration"]
        channel = meta["channel"]
        cover = Image.open(meta["tmp"]).convert("RGBA")

        # canvas & background
        W, H = 1280, 720
        bg = cover.resize((W, H)).filter(ImageFilter.GaussianBlur(38))
        # subtle vignette
        vign = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vign)
        vd.rectangle((0, 0, W, H), fill=(0, 0, 0, 90))
        bg = Image.alpha_composite(bg.convert("RGBA"), vign)

        # card container
        CARD_W, CARD_H = 1180, 600
        card = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
        mask = Image.new("L", (CARD_W, CARD_H), 0)
        radius = 56
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, CARD_W, CARD_H), radius, fill=255)

        # card background (glass look)
        glass = Image.new("RGBA", (CARD_W, CARD_H), (24, 26, 30, 200))
        # inner subtle border/glow
        glow = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for i in range(5):
            gd.rounded_rectangle(
                (3+i, 3+i, CARD_W-3-i, CARD_H-3-i),
                radius=radius-2,
                outline=(255, 255, 255, 70 - i*12),
                width=2,
            )
        glass = Image.alpha_composite(glass, glow)
        card.paste(glass, (0, 0), mask)

        cd = ImageDraw.Draw(card)

        # cover art (left)
        COVER_SIZE = 500
        cover_resized = cover.resize((COVER_SIZE, COVER_SIZE))
        cover_mask = Image.new("L", (COVER_SIZE, COVER_SIZE), 0)
        ImageDraw.Draw(cover_mask).rounded_rectangle((0, 0, COVER_SIZE, COVER_SIZE), 44, fill=255)
        card.paste(cover_resized, (40, 50), cover_mask)

        # fonts
        font_title = _font("Toxic/assets/font.ttf", 44)
        font_small = _font("Toxic/assets/font2.ttf", 26)
        font_med = _font("Toxic/assets/font2.ttf", 30)

        # text (right)
        RIGHT_X = 580
        cd.text((RIGHT_X, 120), f"{title}", font=font_title, fill=(255, 255, 255, 255))
        cd.text((RIGHT_X, 170), f"{channel}", font=font_small, fill=(220, 225, 230, 255))

        # progress bar
        total_secs = total if total is not None else _mmss_to_sec(duration_str)
        total_secs = max(1, int(total_secs))
        pos = max(0, min(int(position), total_secs))
        left_label = _sec_to_mmss(pos)
        right_label = _sec_to_mmss(total_secs)

        BAR_X1, BAR_X2 = RIGHT_X, RIGHT_X + 500
        BAR_Y = 230
        # base line
        cd.line((BAR_X1, BAR_Y, BAR_X2, BAR_Y), fill=(210, 215, 220, 180), width=8)
        # fill line
        p = pos / total_secs
        knob_x = int(BAR_X1 + (BAR_X2 - BAR_X1) * p)
        cd.line((BAR_X1, BAR_Y, knob_x, BAR_Y), fill=(255, 255, 255, 255), width=8)
        # knob
        cd.ellipse((knob_x-10, BAR_Y-10, knob_x+10, BAR_Y+10), fill=(255, 255, 255, 255))

        # time labels
        cd.text((BAR_X1, BAR_Y + 12), left_label, font=font_small, fill=(255, 255, 255, 230))
        tw = cd.textlength(right_label, font=font_small)
        cd.text((BAR_X2 - tw, BAR_Y + 12), right_label, font=font_small, fill=(255, 255, 255, 230))

        # transport controls (vector icons)
        CTRL_Y = 330
        # prev
        def triangle(center, size=18, direction="left"):
            cx, cy = center
            if direction == "left":
                return [(cx+size//2, cy-size), (cx+size//2, cy+size), (cx-size, cy)]
            else:
                return [(cx-size//2, cy-size), (cx-size//2, cy+size), (cx+size, cy)]
        cd.polygon(triangle((RIGHT_X + 40, CTRL_Y), direction="left"), fill=(255, 255, 255, 240))
        cd.rectangle((RIGHT_X + 48, CTRL_Y-20, RIGHT_X + 54, CTRL_Y+20), fill=(255, 255, 255, 240))

        # pause
        PX = RIGHT_X + 120
        cd.rectangle((PX-14, CTRL_Y-24, PX-6, CTRL_Y+24), fill=(255, 255, 255, 240))
        cd.rectangle((PX+6, CTRL_Y-24, PX+14, CTRL_Y+24), fill=(255, 255, 255, 240))

        # next
        NX = RIGHT_X + 200
        cd.rectangle((NX-54, CTRL_Y-20, NX-48, CTRL_Y+20), fill=(255, 255, 255, 240))
        cd.polygon(triangle((NX - 40, CTRL_Y), direction="right"), fill=(255, 255, 255, 240))

        # bot + owner (top-right)
        tag = f"{app.name}  •  {OWNER_NAME}"
        tag_w = cd.textlength(tag, font=font_small)
        cd.text((CARD_W - 30 - tag_w, 34), tag, font=font_small, fill=(235, 235, 240, 255))

        # paste card onto bg
        bg.paste(card, (50, 60), card)

        # iOS bottom handle (small line)
        h_d = ImageDraw.Draw(bg)
        h_d.rounded_rectangle((W//2 - 70, H - 60, W//2 + 70, H - 48), radius=6, fill=(255, 255, 255, 130))

        # save
        bg.convert("RGB").save(out_path, "PNG")
        # clean temp once (keep cache file for speed if you like)
        try:
            os.remove(meta["tmp"])
            META_CACHE[videoid]["tmp"] = out_path  # reuse final as cover source next calls
        except Exception:
            pass

        return out_path

    except Exception as e:
        print("Thumbnail Error:", e)
        return YOUTUBE_IMG_URL
