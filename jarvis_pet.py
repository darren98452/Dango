from display import ST7789Display
from PIL import Image, ImageDraw
import time
import math
import random

disp = ST7789Display()

WIDTH = 240
HEIGHT = 240
CENTER = WIDTH // 2

blink = False
next_blink = time.time() + random.uniform(3, 6)

def smooth_color(t):
    # Soft cyan/teal glow
    base = 180 + int((math.sin(t * 0.5) + 1) * 40)
    return (0, base, base)

while True:
    t = time.time()
    now = time.time()

    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)

    color = smooth_color(t)

    # --- Breathing Effect ---
    breath = (math.sin(t * 2) + 1) / 2
    eye_scale = 1 + breath * 0.05

    # Eye geometry
    eye_width = int(40 * eye_scale)
    eye_height = int(50 * eye_scale)
    spacing = 35

    eye_y = CENTER

    # Blink timing
    if now > next_blink:
        blink = True
        next_blink = now + 0.15

    if blink and now > next_blink:
        blink = False
        next_blink = now + random.uniform(3, 6)

    # Draw Eyes
    if not blink:
        # Left Eye
        draw.rounded_rectangle(
            (
                CENTER - spacing - eye_width,
                eye_y - eye_height // 2,
                CENTER - spacing,
                eye_y + eye_height // 2
            ),
            radius=15,
            fill=color
        )

        # Right Eye
        draw.rounded_rectangle(
            (
                CENTER + spacing,
                eye_y - eye_height // 2,
                CENTER + spacing + eye_width,
                eye_y + eye_height // 2
            ),
            radius=15,
            fill=color
        )
    else:
        # Blinking (thin lines)
        draw.line(
            (
                CENTER - spacing - eye_width,
                eye_y,
                CENTER - spacing,
                eye_y
            ),
            fill=color,
            width=4
        )

        draw.line(
            (
                CENTER + spacing,
                eye_y,
                CENTER + spacing + eye_width,
                eye_y
            ),
            fill=color,
            width=4
        )

    # Mirror for beam splitter
    image = image.transpose(Image.FLIP_LEFT_RIGHT)

    disp.display_image(image)

    time.sleep(0.03)
