import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
from youtubesearchpython.__future__ import VideosSearch

from Toxic import app
from config import YOUTUBE_IMG_URL # yeh 2 config me daal lena


def clear(text: str) -> str:
    words = text.split(" ")
    title = ""
    for i in words:
        if len(title) + len(i) < 60:
            title += " " + i
    return title.strip()


async def get_thumb(videoid: str):
    """
    Generate Spotify-like Neon thumbnail for YouTube video
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
        W, H = (720, 480)   # thoda bada size, cool lagega
        bg = cover.resize((W, H)).filter(ImageFilter.GaussianBlur(25))
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.35).convert("RGBA")

        # --- neon border effect ---
        neon = Image.new("RGBA", (W, H), (0,0,0,0))
        ndraw = ImageDraw.Draw(neon)
        for i in range(12):  # multiple strokes for glow
            ndraw.rounded_rectangle(
                (10+i, 10+i, W-10-i, H-10-i),
                radius=40,
                outline=(255,20,147, max(0,180-15*i)),  # pinkish neon
                width=3
            )
        bg.alpha_composite(neon)

        # --- card ---
        card = Image.new("RGBA", (W-80, H-80), (0, 0, 0, 180))
        draw = ImageDraw.Draw(card)

        # fonts
        font_title = ImageFont.truetype("Toxic/assets/font.ttf", 34)
        font_small = ImageFont.truetype("Toxic/assets/font2.ttf", 22)
        font_owner = ImageFont.truetype("Toxic/assets/font2.ttf", 20)

        # paste album art
        art_size = 260
        art = cover.resize((art_size, art_size))
        mask = Image.new("L", (art_size, art_size), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, art_size, art_size), 25, fill=255)
        card.paste(art, (30, 30), mask)

        # --- text info ---
        draw.text((320, 50), clear(title), font=font_title, fill="white")
        draw.text((320, 100), f"{channel} • {views}", font=font_small, fill=(220,220,220))
        draw.text((320, 140), f"⏳ Duration: {duration}", font=font_small, fill=(200,255,200))

        # --- Owner & Bot name ---
        draw.text((30, H-150), f"👑 Owner: Toxic", font=font_owner, fill=(0,255,255))
        draw.text((30, H-120), f"🤖 Bot: Toxic", font=font_owner, fill=(255,255,0))

        # --- controls (pause) ---
        draw.rectangle((350, 200, 365, 250), fill="white")  # left bar
        draw.rectangle((373, 200, 388, 250), fill="white")  # right bar

        # --- merge card with bg ---
        bg.alpha_composite(card, (40, 40))

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
