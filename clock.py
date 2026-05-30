from display import ST7789Display
from PIL import Image, ImageDraw, ImageFont
import time
import math

disp = ST7789Display()

# --- Fonts ---
try:
    font_time = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28
    )
    font_date = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14
    )
except:
    font_time = ImageFont.load_default()
    font_date = ImageFont.load_default()

WIDTH = 240
HEIGHT = 240

while True:
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)

    # --- Time ---
    current_time = time.strftime("%H:%M")
    seconds = time.strftime("%S")
    date = time.strftime("%d %b %Y")

    # --- Breathing glow effect ---
    pulse = (math.sin(time.time() * 2) + 1) / 2
    glow_intensity = int(120 + pulse * 135)

    CYAN = (0, glow_intensity, glow_intensity)
    GLOW = (0, 60, 60)

    # --- Center time ---
    bbox = draw.textbbox((0, 0), current_time, font=font_time)
    w = bbox[2] - bbox[0]

    x_time = (WIDTH - w) // 2
    y_time = 80

    # Subtle glow layers
    for offset in range(1, 3):
        draw.text((x_time - offset, y_time), current_time, font=font_time, fill=GLOW)
        draw.text((x_time + offset, y_time), current_time, font=font_time, fill=GLOW)

    draw.text((x_time, y_time), current_time, font=font_time, fill=CYAN)

    # --- Seconds (small, right side) ---
    draw.text((x_time + w + 4, y_time + 8), seconds, font=font_date, fill=(0, 150, 150))

    # --- Date ---
    bbox2 = draw.textbbox((0, 0), date, font=font_date)
    w2 = bbox2[2] - bbox2[0]
    draw.text(((WIDTH - w2) // 2, 120), date, font=font_date, fill=(0, 200, 200))

    # --- Mirror for beam splitter ---
    image = image.transpose(Image.FLIP_LEFT_RIGHT)

    disp.display_image(image)

    time.sleep(0.05)
