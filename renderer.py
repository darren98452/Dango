import time
import math
import random
from PIL import Image, ImageDraw

WIDTH = 240
HEIGHT = 240
CX, CY = WIDTH // 2, HEIGHT // 2
CYAN = (0, 255, 255)
PINK = (255, 182, 193)

class JarvisRenderer:
    def __init__(self):
        self.mode = "IDLE"
        self.emotion = "neutral"

        self.eye_open = 0.4
        self.target_eye_open = 0.4
        self.eye_offset_x = 0
        self.target_offset_x = 0
        
        self.breath_y = 0
        self.jitter_x = 0
        
        self.start_time = time.time()
        self.last_update = time.time()
        self.blink_timer = time.time()
        self.is_blinking = False

        self.wake_active = False
        self.wake_step = 0
        self.wake_timer = 0

    def lerp(self, current, target, speed, dt):
        return current + (target - current) * min(speed * dt, 1)

    def set_mode(self, mode):
        self.mode = mode
        if mode == "IDLE": self.target_eye_open = 0.4
        elif mode == "LISTENING": self.target_eye_open = 1.1
        elif mode == "THINKING": self.target_eye_open = 0.8
        elif mode == "ANSWERING": self.target_eye_open = 1.0

    def set_emotion(self, emotion):
        self.emotion = emotion

    def trigger_wake(self):
        self.wake_active = True
        self.wake_step = 0
        self.wake_timer = time.time()

    def update(self):
        now = time.time()
        dt = now - self.last_update
        elapsed = now - self.start_time
        self.last_update = now

        # Base smoothing
        self.eye_open = self.lerp(self.eye_open, self.target_eye_open, 6, dt)
        self.eye_offset_x = self.lerp(self.eye_offset_x, self.target_offset_x, 6, dt)

        if not self.wake_active:

            # Breathing only in calm states
            if self.mode in ["IDLE", "LISTENING"]:
                self.breath_y = math.sin(elapsed * 1.2) * 3
            else:
                self.breath_y = 0

            # Softer thinking scan (less vibration)
            if self.mode == "THINKING":
                self.jitter_x = math.sin(elapsed * 6) * 4
            else:
                self.jitter_x = 0

            # Blink only in IDLE or ANSWERING
            if self.mode in ["IDLE", "ANSWERING"]:
                if not self.is_blinking and now - self.blink_timer > random.uniform(3, 7):
                    self.is_blinking = True
                    self.blink_timer = now

                if self.is_blinking:
                    self.eye_open = self.lerp(self.eye_open, 0.0, 18, dt)
                    if self.eye_open < 0.05:
                        self.is_blinking = False

        if self.wake_active:
            self.handle_wake_sequence(now)

    def handle_wake_sequence(self, now):
        # Slightly smoother timing (less robotic)
        if self.wake_step == 0:
            self.target_eye_open = 0.0
            if now - self.wake_timer > 0.12:
                self.wake_step, self.wake_timer = 1, now

        elif self.wake_step == 1:
            self.target_eye_open = 1.3
            if now - self.wake_timer > 0.18:
                self.wake_step, self.wake_timer = 2, now

        elif self.wake_step == 2:
            self.target_offset_x = -20
            if now - self.wake_timer > 0.25:
                self.wake_step, self.wake_timer = 3, now

        elif self.wake_step == 3:
            self.target_offset_x = 20
            if now - self.wake_timer > 0.25:
                self.wake_step, self.wake_timer = 4, now

        elif self.wake_step == 4:
            self.target_offset_x = 0
            if now - self.wake_timer > 0.25:
                self.wake_active = False
                self.set_mode("LISTENING")

    def render(self):
        self.update()
        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        ey = CY - 10 + self.breath_y
        lx = CX - 55 + self.eye_offset_x + self.jitter_x
        rx = CX + 55 + self.eye_offset_x + self.jitter_x
        
        self.draw_emotional_eyes(draw, lx, rx, ey)
        return img

    def draw_emotional_eyes(self, draw, lx, rx, y):
        w, h = 40, int(30 * self.eye_open)

        if self.emotion == "happy":
            draw.arc([lx-w, y-h, lx+w, y+h], 180, 360, fill=CYAN, width=14)
            draw.arc([rx-w, y-h, rx+w, y+h], 180, 360, fill=CYAN, width=14)

        elif self.emotion == "sad":
            draw.arc([lx-w, y-h, lx+w, y+h], 0, 180, fill=CYAN, width=14)
            draw.arc([rx-w, y-h, rx+w, y+h], 0, 180, fill=CYAN, width=14)

        elif self.emotion == "angry":
            draw.polygon([(lx-w, y-h), (lx+w, y), (lx-w, y+h)], fill=CYAN)
            draw.polygon([(rx+w, y-h), (rx-w, y), (rx+w, y+h)], fill=CYAN)

        elif self.emotion == "confused":
            draw.line([lx-w, y, lx+w, y], fill=CYAN, width=8)
            draw.ellipse([rx-20, y-20, rx+20, y+20], outline=CYAN, width=8)

        elif self.emotion == "surprised":
            draw.ellipse([lx-w, y-h, lx+w, y+h], outline=CYAN, width=10)
            draw.ellipse([rx-w, y-h, rx+w, y+h], outline=CYAN, width=10)

        elif self.emotion == "sleepy":
            sh = 6
            draw.rounded_rectangle([lx-w, y-sh, lx+w, y+sh], radius=6, fill=CYAN)
            draw.rounded_rectangle([rx-w, y-sh, rx+w, y+sh], radius=6, fill=CYAN)

        elif self.emotion == "excited":
            draw.line([lx-w, y+h, lx, y-h], fill=CYAN, width=10)
            draw.line([lx, y-h, lx+w, y+h], fill=CYAN, width=10)
            draw.line([rx-w, y+h, rx, y-h], fill=CYAN, width=10)
            draw.line([rx, y-h, rx+w, y+h], fill=CYAN, width=10)

        elif self.emotion == "bored":
            draw.rectangle([lx-w, y, lx+w, y+(h//2)], fill=CYAN)
            draw.rectangle([rx-w, y, rx+w, y+(h//2)], fill=CYAN)

        elif self.emotion == "blush":
            draw.arc([lx-w, y-h, lx+w, y+h], 180, 360, fill=CYAN, width=14)
            draw.arc([rx-w, y-h, rx+w, y+h], 180, 360, fill=CYAN, width=14)
            draw.ellipse([lx-20, y+25, lx+20, y+45], fill=PINK)
            draw.ellipse([rx-20, y+25, rx+20, y+45], fill=PINK)

        else:  # Neutral
            draw.rounded_rectangle([lx-w, y-h, lx+w, y+h], radius=22, fill=CYAN)
            draw.rounded_rectangle([rx-w, y-h, rx+w, y+h], radius=22, fill=CYAN)
