from PIL import ImageFont
import time

try:
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18
    )
except:
    font = ImageFont.load_default()

WIDTH = 240

def time_overlay(draw):
    current_time = time.strftime("%H:%M")
    bbox = draw.textbbox((0, 0), current_time, font=font)
    w = bbox[2] - bbox[0]

    draw.text(
        ((WIDTH - w) // 2, 170),
        current_time,
        font=font,
        fill=(255, 255, 255)
    )
