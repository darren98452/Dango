"""
widgets.py — Clock + Weather widget for Dango idle screen

Shows:
  - Current time (large, glowing cyan)
  - Current date
  - Temperature + weather condition
  - Weather icon (drawn with PIL shapes, no image files needed)

Weather updates every 10 minutes via OpenWeatherMap.
"""

import time
import math
import threading
import requests
from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------
# CONFIGURATION — set your details here
# --------------------------------------------------
OWM_API_KEY = "##################################"   # get free at openweathermap.org
CITY        = "bangalore"                          # your city
UNITS       = "metric"                          # "metric" = °C, "imperial" = °F
WEATHER_REFRESH_INTERVAL = 600                  # seconds (10 min)

WIDTH  = 240
HEIGHT = 240

# Colour palette
CYAN        = (0, 255, 255)
CYAN_DIM    = (0, 160, 160)
CYAN_GLOW   = (0, 60, 60)
WHITE       = (255, 255, 255)
GREY        = (120, 120, 120)
YELLOW      = (255, 220, 50)
BLUE_LIGHT  = (100, 180, 255)
ORANGE      = (255, 140, 50)
BLACK       = (0, 0, 0)

# --------------------------------------------------
# FONTS
# --------------------------------------------------
def _load_fonts():
    base = "/usr/share/fonts/truetype/dejavu/DejaVuSans"
    bold = base + "-Bold.ttf"
    reg  = base + ".ttf"
    try:
        return {
            "time":    ImageFont.truetype(bold, 52),
            "seconds": ImageFont.truetype(reg,  18),
            "date":    ImageFont.truetype(reg,  16),
            "weather": ImageFont.truetype(reg,  15),
            "temp":    ImageFont.truetype(bold, 26),
            "small":   ImageFont.truetype(reg,  13),
        }
    except Exception:
        default = ImageFont.load_default()
        return {k: default for k in ["time","seconds","date","weather","temp","small"]}

FONTS = _load_fonts()


# --------------------------------------------------
# WEATHER FETCHER
# --------------------------------------------------
class WeatherFetcher:
    def __init__(self):
        self.data = None          # dict with temp, condition, icon_code
        self.last_fetch = 0
        self.lock = threading.Lock()
        self._fetch()             # fetch immediately on init

    def get(self):
        with self.lock:
            return self.data

    def _fetch(self):
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def _do_fetch(self):
        try:
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?q={CITY}&appid={OWM_API_KEY}&units={UNITS}"
            )
            r = requests.get(url, timeout=8)
            r.raise_for_status()
            d = r.json()
            with self.lock:
                self.data = {
                    "temp":      round(d["main"]["temp"]),
                    "feels":     round(d["main"]["feels_like"]),
                    "condition": d["weather"][0]["main"],
                    "desc":      d["weather"][0]["description"].title(),
                    "icon":      d["weather"][0]["icon"],
                    "humidity":  d["main"]["humidity"],
                    "city":      d["name"],
                }
            self.last_fetch = time.time()
            print(f"[Weather] {self.data['temp']}° {self.data['desc']}")
        except Exception as e:
            print(f"[Weather] Fetch failed: {e}")

    def tick(self):
        """Call this every frame — triggers refresh if due."""
        if time.time() - self.last_fetch > WEATHER_REFRESH_INTERVAL:
            self._fetch()


# --------------------------------------------------
# WEATHER ICON DRAWING (PIL shapes, no image files)
# --------------------------------------------------
def draw_weather_icon(draw, cx, cy, icon_code, size=28):
    """Draw a simple weather icon centred at (cx, cy)."""
    s = size
    h = s // 2

    if icon_code.startswith("01"):          # clear sky / sun
        draw.ellipse([cx-h, cy-h, cx+h, cy+h], fill=YELLOW)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = cx + int((h+3) * math.cos(rad))
            y1 = cy + int((h+3) * math.sin(rad))
            x2 = cx + int((h+8) * math.cos(rad))
            y2 = cy + int((h+8) * math.sin(rad))
            draw.line([x1, y1, x2, y2], fill=YELLOW, width=2)

    elif icon_code.startswith("02"):        # few clouds
        draw.ellipse([cx-h, cy-h, cx+h, cy+h], fill=YELLOW)
        draw.ellipse([cx-h+4, cy, cx+h+8, cy+h+6], fill=(180,180,200))

    elif icon_code.startswith(("03","04")): # cloudy
        draw.ellipse([cx-h, cy-4, cx+h, cy+h], fill=(160,160,180))
        draw.ellipse([cx-h+6, cy-h, cx+h-2, cy+6], fill=(190,190,210))

    elif icon_code.startswith(("09","10")): # rain
        draw.ellipse([cx-h, cy-h+4, cx+h, cy+6], fill=(130,130,160))
        for i, rx in enumerate([cx-8, cx, cx+8]):
            draw.line([rx, cy+8, rx-3, cy+s-2], fill=BLUE_LIGHT, width=2)

    elif icon_code.startswith("11"):        # thunderstorm
        draw.ellipse([cx-h, cy-h+4, cx+h, cy+6], fill=(80,80,100))
        pts = [(cx, cy+6), (cx-6, cy+16), (cx+2, cy+16), (cx-4, cy+s), (cx+8, cy+14), (cx+1, cy+14)]
        draw.polygon(pts, fill=YELLOW)

    elif icon_code.startswith("13"):        # snow
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            x1 = cx + int(3 * math.cos(rad))
            y1 = cy + int(3 * math.sin(rad))
            x2 = cx + int(h * math.cos(rad))
            y2 = cy + int(h * math.sin(rad))
            draw.line([x1, y1, x2, y2], fill=WHITE, width=2)
        draw.ellipse([cx-3, cy-3, cx+3, cy+3], fill=WHITE)

    elif icon_code.startswith("50"):        # mist/fog
        for i, ry in enumerate([cy-6, cy, cy+6]):
            draw.line([cx-h, ry, cx+h, ry], fill=(160,160,180), width=3)

    else:                                   # fallback dot
        draw.ellipse([cx-h, cy-h, cx+h, cy+h], outline=CYAN, width=2)


# --------------------------------------------------
# MAIN WIDGET RENDERER
# --------------------------------------------------
class WidgetRenderer:
    def __init__(self):
        self.weather = WeatherFetcher()
        self.start_time = time.time()

    def render(self):
        self.weather.tick()

        img  = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
        draw = ImageDraw.Draw(img)

        elapsed = time.time() - self.start_time

        # --- Breathing glow pulse ---
        pulse     = (math.sin(elapsed * 1.5) + 1) / 2
        glow_val  = int(180 + pulse * 75)
        cyan_live = (0, glow_val, glow_val)
        glow_col  = (0, int(glow_val * 0.25), int(glow_val * 0.25))

        # ---- TIME ----
        now_str  = time.strftime("%H:%M")
        secs_str = time.strftime("%S")

        # Glow layers
        bbox = draw.textbbox((0,0), now_str, font=FONTS["time"])
        tw   = bbox[2] - bbox[0]
        tx   = (WIDTH - tw) // 2
        ty   = 38

        for off in range(1, 4):
            draw.text((tx - off, ty), now_str, font=FONTS["time"], fill=glow_col)
            draw.text((tx + off, ty), now_str, font=FONTS["time"], fill=glow_col)
            draw.text((tx, ty - off), now_str, font=FONTS["time"], fill=glow_col)
            draw.text((tx, ty + off), now_str, font=FONTS["time"], fill=glow_col)

        draw.text((tx, ty), now_str, font=FONTS["time"], fill=cyan_live)

        # Seconds (small, right-aligned after time)
        draw.text((tx + tw + 4, ty + 28), secs_str, font=FONTS["seconds"], fill=CYAN_DIM)

        # ---- DATE ----
        date_str = time.strftime("%A, %d %B %Y")
        bbox2 = draw.textbbox((0,0), date_str, font=FONTS["date"])
        dw    = bbox2[2] - bbox2[0]
        draw.text(((WIDTH - dw) // 2, 98), date_str, font=FONTS["date"], fill=CYAN_DIM)

        # ---- DIVIDER ----
        draw.line([(20, 122), (220, 122)], fill=(0, 60, 60), width=1)

        # ---- WEATHER ----
        w = self.weather.get()

        if w:
            unit_sym = "°C" if UNITS == "metric" else "°F"

            # Icon
            draw_weather_icon(draw, 38, 158, w["icon"], size=30)

            # Temperature (large)
            temp_str = f"{w['temp']}{unit_sym}"
            draw.text((68, 140), temp_str, font=FONTS["temp"], fill=WHITE)

            # Condition
            draw.text((68, 170), w["desc"], font=FONTS["weather"], fill=GREY)

            # City + humidity
            info_str = f"{w['city']}  💧{w['humidity']}%"
            bbox3 = draw.textbbox((0,0), info_str, font=FONTS["small"])
            iw = bbox3[2] - bbox3[0]
            draw.text(((WIDTH - iw) // 2, 196), info_str, font=FONTS["small"], fill=(80,80,80))

            # Feels like
            feels_str = f"Feels like {w['feels']}{unit_sym}"
            bbox4 = draw.textbbox((0,0), feels_str, font=FONTS["small"])
            fw = bbox4[2] - bbox4[0]
            draw.text(((WIDTH - fw) // 2, 214), feels_str, font=FONTS["small"], fill=(60,60,60))

        else:
            # Weather loading / unavailable
            draw.text((WIDTH//2 - 40, 155), "fetching weather...", font=FONTS["small"], fill=(60,60,60))

        return img
