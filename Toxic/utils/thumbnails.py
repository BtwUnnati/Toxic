import os
import re
import aiofiles
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
from youtubesearchpython.__future__ import VideosSearch

from Toxic import app
from config import YOUTUBE_IMG_URL


def clear(text: str) -> str:
    """
    Limit title length to 60 chars
    """
    words = text.split(" ")
    title = ""
    for i in words:
        if len(title) + len(i) < 60:
            title += " " + i
    return title.strip()


def sec_to_mmss(sec: int) -> str:
    try:
        sec = int(sec)
        return f"{sec//60}:{sec%60:02d}"
    except:
        return "0:00"


async def get_thumb(videoid: str):
    """
    Generate Spotify-like thumbnail for YouTube video
    """
    out_path = f"cache/{videoid}.png"
    if os.path.isfile(out_path):
        return out_path

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        data = (await results.next())["result"][0]

        # --- video info ---
        title = re.sub(r"\W+", " ", data.get("title", "Unknown")).title()
        duration = data.get("duration", "0:00")
        thumbnail = data["thumbnails"][0]["url"].split("?")[0]
        views = data.get("viewCount", {}).get("short", "0 views")
        channel = data.get("channel", {}).get("name", "Unknown")

        # --- download thumbnail ---
        tmp = f"cache/thumb{videoid}.png"
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(tmp, mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        cover = Image.open(tmp).convert("RGB")

        # --- canvas background ---
        W, H = (600, 360)
        bg = cover.resize((W, H)).filter(ImageFilter.GaussianBlur(20))
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.4).convert("RGBA")

        # --- card ---
        card = Image.new("RGBA", (W-40, H-40), (0, 0, 0, 180))
        draw = ImageDraw.Draw(card)

        # fonts
        font_title = ImageFont.truetype("Toxic/assets/font.ttf", 28)
        font_small = ImageFont.truetype("Toxic/assets/font2.ttf", 20)

        # paste album art
        art_size = 200
        art = cover.resize((art_size, art_size))
        mask = Image.new("L", (art_size, art_size), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, art_size, art_size), 20, fill=255)
        card.paste(art, (20, 20), mask)

        # --- text ---
        draw.text((250, 40), clear(title), font=font_title, fill="white")
        draw.text((250, 80), f"{channel} • {views}", font=font_small, fill=(220,220,220))

        # --- progress bar ---
        try:
            mins, secs = duration.split(":")
            total = int(mins)*60 + int(secs)
        except:
            total = 0
        pos = 0  # start hamesha 0 pe (live update ke liye baad me badlenge)
        bar_x, bar_y, bar_w = 250, 130, 300
        draw.rectangle((bar_x, bar_y, bar_x+bar_w, bar_y+6), fill=(90,90,90))
        fill_w = max(10, int(bar_w * 0.02))  # thoda filled
        draw.rectangle((bar_x, bar_y, bar_x+fill_w, bar_y+6), fill="white")

        draw.text((bar_x, bar_y+12), "0:00", font=font_small, fill="white")
        draw.text((bar_x+bar_w-50, bar_y+12), duration, font=font_small, fill="white")

        # --- controls (pause icon) ---
        draw.rectangle((310, 200, 322, 240), fill="white")  # left bar
        draw.rectangle((328, 200, 340, 240), fill="white")  # right bar

        # --- merge card with background ---
        bg.alpha_composite(card, (20, 20))

        # save
        bg.convert("RGB").save(out_path, "PNG")
        try:
            os.remove(tmp)
        except:
            pass

        return out_path
    except Exception as e:
        print("Thumb error:", e)
        return YOUTUBE_IMG_URL
