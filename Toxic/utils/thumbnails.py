import random
import logging
import os
import re
import aiofiles
import aiohttp
import traceback
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch

logging.basicConfig(level=logging.INFO)

def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage

def truncate(text):
    list = text.split(" ")
    text1 = ""
    text2 = ""    
    for i in list:
        if len(text1) + len(i) < 30:        
            text1 += " " + i
        elif len(text2) + len(i) < 30:       
            text2 += " " + i
    text1 = text1.strip()
    text2 = text2.strip()     
    return [text1,text2]

def draw_text_with_shadow(background, draw, position, text, font, fill, shadow_offset=(3, 3), shadow_blur=5):
    shadow = Image.new('RGBA', background.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.text(position, text, font=font, fill="black")
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
    background.paste(shadow, shadow_offset, shadow)
    draw.text(position, text, font=font, fill=fill)

def crop_center_circle(img, output_size):
    img = img.resize((output_size, output_size))
    mask = Image.new("L", (output_size, output_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, output_size, output_size), fill=255)
    result = Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask)
    return result

async def get_thumb(videoid: str):
    try:
        if os.path.isfile(f"cache/{videoid}_v4.png"):
            return f"cache/{videoid}_v4.png"

        url = f"https://www.youtube.com/watch?v={videoid}"
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            title = result.get("title")
            if title:
                title = re.sub("\W+", " ", title).title()
            else:
                title = "Unsupported Title"
            duration = result.get("duration") or "Live"
            thumbnail_data = result.get("thumbnails")
            thumbnail = thumbnail_data[0]["url"].split("?")[0] if thumbnail_data else None
            views_data = result.get("viewCount")
            views = views_data.get("short") if views_data and views_data.get("short") else "Unknown Views"
            channel_data = result.get("channel")
            channel = channel_data.get("name") if channel_data and channel_data.get("name") else "Unknown Channel"

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                content = await resp.read()
                if resp.status == 200:
                    filepath = f"cache/thumb{videoid}.png"
                    f = await aiofiles.open(filepath, mode="wb")
                    await f.write(content)
                    await f.close()

        # 🔹 Background GIF lagao
        gif_path = "Toxic/assets/dev.gif"  # <-- yaha apni gif ka path do
        background = Image.open(gif_path).convert("RGBA")
        background = background.resize((1280, 720))

        # 🔹 Song Thumbnail ko circle crop me dikhana (without border)
        image_path = f"cache/thumb{videoid}.png"
        youtube = Image.open(image_path).convert("RGBA")
        circle_thumbnail = crop_center_circle(youtube, 400)  # border hat gaya
        circle_position = (120, 160)
        background.paste(circle_thumbnail, circle_position, circle_thumbnail)

        # 🔹 Text & Details
        draw = ImageDraw.Draw(background)
        arial = ImageFont.truetype("Toxic/assets/font2.ttf", 30)
        title_font = ImageFont.truetype("Toxic/assets/font3.ttf", 45)

        text_x_position = 565
        title1 = truncate(title)
        draw_text_with_shadow(background, draw, (text_x_position, 180), title1[0], title_font, (255, 255, 255))
        draw_text_with_shadow(background, draw, (text_x_position, 230), title1[1], title_font, (255, 255, 255))
        draw_text_with_shadow(background, draw, (text_x_position, 320), f"{channel}  |  {views[:23]}", arial, (255, 255, 255))

        # 🔹 Progress Bar
        line_length = 580
        if duration != "Live":
            color_line_percentage = random.uniform(0.15, 0.85)
            color_line_length = int(line_length * color_line_percentage)
            draw.line([(text_x_position, 380), (text_x_position + color_line_length, 380)], fill="red", width=9)
            draw.line([(text_x_position + color_line_length, 380), (text_x_position + line_length, 380)], fill="white", width=8)
            draw.ellipse([text_x_position + color_line_length - 10, 370, text_x_position + color_line_length + 10, 390], fill="red")
        else:
            draw.line([(text_x_position, 380), (text_x_position + line_length, 380)], fill="red", width=9)

        draw_text_with_shadow(background, draw, (text_x_position, 400), "00:00", arial, (255, 255, 255))
        draw_text_with_shadow(background, draw, (1080, 400), duration, arial, (255, 255, 255))

        # 🔹 Play Icons
        play_icons = Image.open("Toxic/assets/play_icons.png").convert("RGBA")
        play_icons = play_icons.resize((580, 62))
        background.paste(play_icons, (text_x_position, 450), play_icons)

        os.remove(f"cache/thumb{videoid}.png")

        background_path = f"cache/{videoid}_v4.png"
        background.save(background_path)

        return background_path

    except Exception as e:
        logging.error(f"Error generating thumbnail for video {videoid}: {e}")
        traceback.print_exc()
        return None
