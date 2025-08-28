import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
from youtubesearchpython.__future__ import VideosSearch

from Toxic import app
from config import YOUTUBE_IMG_URL # OWNER_NAME config me define krna hoga


def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight))


def clear(text):
    words = text.split(" ")
    title = ""
    for word in words:
        if len(title) + len(word) < 60:
            title += " " + word
    return title.strip()


async def get_thumb(videoid):
    if os.path.isfile(f"cache/{videoid}.png"):
        return f"cache/{videoid}.png"

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            title = re.sub("\W+", " ", result.get("title", "Unsupported Title")).title()
            duration = result.get("duration", "Unknown Mins")
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            views = result.get("viewCount", {}).get("short", "Unknown Views")
            channel = result.get("channel", {}).get("name", "Unknown Channel")

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        youtube = Image.open(f"cache/thumb{videoid}.png")
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")

        # Background blur + dark effect
        background = image2.filter(ImageFilter.BoxBlur(20))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.4)

        draw = ImageDraw.Draw(background)
        font_big = ImageFont.truetype("Toxic/assets/font.ttf", 45)
        font_small = ImageFont.truetype("Toxic/assets/font2.ttf", 32)

        # Neon rectangle border (outer glow)
        neon_color = (0, 255, 200)
        for i in range(8):
            draw.rectangle(
                [15+i, 15+i, 1265-i, 705-i],
                outline=(neon_color[0], neon_color[1], neon_color[2], 255 - i*25),
                width=3,
            )

        # Bot + Owner Name (Top)
        bot_owner = f"{unidecode(app.name)}  Toxic • "
        draw.text((40, 25), bot_owner, fill="white", font=font_small)

        # Song info (Bottom area like player)
        draw.text((60, 560), f"{channel} • {views}", fill="white", font=font_small)
        draw.text((60, 610), clear(title), fill="white", font=font_big)

        # Duration + progress bar
        draw.rectangle([60, 670, 1220, 685], fill=(255, 255, 255, 180))
        draw.ellipse([60, 665, 75, 680], fill="white")
        draw.text((50, 690), "00:00", fill="white", font=font_small)
        draw.text((1150, 690), duration, fill="white", font=font_small)

        os.remove(f"cache/thumb{videoid}.png")
        background.save(f"cache/{videoid}.png")
        return f"cache/{videoid}.png"

    except Exception as e:
        print("Thumbnail Error:", e)
        return YOUTUBE_IMG_URL
