"""
simulate.py — Dango Desktop Simulator

Runs the full Dango state machine on your desktop with NO hardware needed.
Mocks: RPi.GPIO, spidev, pvporcupine, pyaudio, speechrecognition, espeak

Controls:
  SPACE     — simulate wake word detection
  ENTER     — submit typed text as speech input
  R         — force return to IDLE (widget screen)
  Q / ESC   — quit

Layout:
  Left  — 240x240 Dango display (scaled 3x = 720x720)
  Right — debug panel: state, log, text input box
"""

import sys
import os
import time
import math
import threading
import queue

# ── Mock hardware modules before anything imports them ──────────────────────
import types

# Mock RPi.GPIO
gpio = types.ModuleType("RPi.GPIO")
gpio.BCM = gpio.OUT = gpio.HIGH = gpio.LOW = 0
gpio.setmode = gpio.setwarnings = gpio.setup = gpio.output = lambda *a, **k: None
sys.modules["RPi"] = types.ModuleType("RPi")
sys.modules["RPi.GPIO"] = gpio

# Mock spidev
spidev_mod = types.ModuleType("spidev")
class FakeSpiDev:
    max_speed_hz = 0
    mode = 0
    def open(self, *a): pass
    def writebytes(self, *a): pass
spidev_mod.SpiDev = FakeSpiDev
sys.modules["spidev"] = spidev_mod

# Mock sounddevice
sd_mod = types.ModuleType("sounddevice")
sd_mod.InputStream = lambda **k: type("S", (), {"start": lambda s: None, "stop": lambda s: None})()
sys.modules["sounddevice"] = sd_mod

# Mock pvporcupine
pv_mod = types.ModuleType("pvporcupine")
class FakePorcupine:
    sample_rate = 16000
    frame_length = 512
    def process(self, pcm): return -1
    def delete(self): pass
pv_mod.create = lambda **k: FakePorcupine()
sys.modules["pvporcupine"] = pv_mod

# Mock pyaudio
pa_mod = types.ModuleType("pyaudio")
pa_mod.paInt16 = 8
class FakePyAudio:
    def open(self, **k):
        class FakeStream:
            def read(self, n, **k): return b"\x00" * n * 2
            def close(self): pass
        return FakeStream()
    def get_device_count(self): return 1
    def get_device_info_by_index(self, i): return {"name": "Fake Mic"}
    def terminate(self): pass
pa_mod.PyAudio = FakePyAudio
sys.modules["pyaudio"] = pa_mod

# Mock speech_recognition
sr_mod = types.ModuleType("speech_recognition")
class FakeRecognizer:
    energy_threshold = 300
    dynamic_energy_threshold = True
    def adjust_for_ambient_noise(self, *a, **k): pass
    def listen(self, *a, **k): return object()
    def recognize_google(self, audio): raise Exception("sim")
sr_mod.Recognizer = FakeRecognizer
sr_mod.Microphone = lambda **k: type("M", (), {"__enter__": lambda s,*a: s, "__exit__": lambda s,*a: None})()
sr_mod.WaitTimeoutError = Exception
sr_mod.UnknownValueError = Exception
sys.modules["speech_recognition"] = sr_mod

# ── Now safe to import Dango modules ────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from renderer import JarvisRenderer
from widgets import WidgetRenderer

import pygame
from PIL import Image

# ── Sim config ───────────────────────────────────────────────────────────────
SCALE        = 3          # 240 * 3 = 720px display
DISPLAY_SIZE = 240 * SCALE
PANEL_W      = 400
WIN_W        = DISPLAY_SIZE + PANEL_W
WIN_H        = DISPLAY_SIZE
FPS          = 60

# Colours for the debug panel
C_BG         = (10,  12,  18)
C_PANEL      = (16,  20,  30)
C_BORDER     = (0,   80,  80)
C_CYAN       = (0,   255, 255)
C_CYAN_DIM   = (0,   140, 140)
C_WHITE      = (230, 230, 230)
C_GREY       = (100, 110, 120)
C_GREEN      = (50,  220, 100)
C_YELLOW     = (255, 210, 50)
C_RED        = (255, 80,  80)
C_INPUT_BG   = (20,  28,  40)

STATE_COLOURS = {
    "IDLE":      C_CYAN_DIM,
    "WAKE":      C_YELLOW,
    "CAPTURING": C_GREEN,
    "THINKING":  (160, 100, 255),
    "ANSWERING": (255, 140, 50),
    "LINGER":    C_CYAN,
}

# ── Brain (optional — works if Ollama is running) ───────────────────────────
try:
    from brain import DangoBrain
    BRAIN_AVAILABLE = True
except Exception:
    BRAIN_AVAILABLE = False

# ── Simulator ────────────────────────────────────────────────────────────────
class DangoSimulator:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Dango Simulator")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock  = pygame.time.Clock()

        # Fonts
        self.font_title  = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_body   = pygame.font.SysFont("monospace", 12)
        self.font_small  = pygame.font.SysFont("monospace", 11)
        self.font_state  = pygame.font.SysFont("monospace", 18, bold=True)

        # Dango modules
        self.dango   = JarvisRenderer()
        self.dango.set_mode("IDLE")
        self.widgets = WidgetRenderer()

        # State
        self.state       = "IDLE"
        self.linger_time = None
        self.FACE_LINGER = 2.0

        # Log
        self.log    = []
        self.max_log = 18

        # Text input
        self.input_text     = ""
        self.input_active   = False
        self.input_box_rect = None
        self.input_submit_queue = queue.Queue()

        # Brain
        if BRAIN_AVAILABLE:
            self.brain = DangoBrain(
                on_start = self._on_thinking,
                on_done  = self._on_reply,
                on_error = self._on_error,
            )
            self._log("Brain: Ollama connected", C_GREEN)
        else:
            self.brain = None
            self._log("Brain: Ollama not found (text echo mode)", C_YELLOW)

        self._log("SPACE = wake  |  ENTER = send text  |  R = reset", C_GREY)

    # ── Logging ──────────────────────────────────────────────────────────────
    def _log(self, msg, colour=None):
        ts = time.strftime("%H:%M:%S")
        self.log.append((f"[{ts}] {msg}", colour or C_WHITE))
        if len(self.log) > self.max_log:
            self.log.pop(0)
        print(msg)

    # ── Brain callbacks ───────────────────────────────────────────────────────
    def _on_thinking(self):
        self.state = "THINKING"
        self.dango.set_mode("THINKING")
        self.dango.set_emotion("neutral")
        self._log("Thinking...", (160, 100, 255))

    def _on_reply(self, text, emotion):
        self._log(f"Dango: {text}", C_CYAN)
        self._log(f"Emotion: {emotion}", C_CYAN_DIM)
        self.dango.set_mode("ANSWERING")
        self.dango.set_emotion(emotion)
        self.state = "LINGER"
        self.linger_time = time.time()

    def _on_error(self, msg):
        self._log(f"Error: {msg}", C_RED)
        self.dango.set_mode("IDLE")
        self.dango.set_emotion("sad")
        self.state = "LINGER"
        self.linger_time = time.time()

    # ── Fake speech input ─────────────────────────────────────────────────────
    def _handle_text_submit(self, text):
        if not text.strip():
            return
        self._log(f"You: {text}", C_GREEN)
        if self.brain:
            self.brain.chat(text)
        else:
            # Echo mode — fake a reply
            def _fake_reply():
                time.sleep(1.2)
                self._on_thinking()
                time.sleep(1.5)
                self._on_reply(f"You said: {text}", "happy")
            threading.Thread(target=_fake_reply, daemon=True).start()
            self.state = "THINKING"
            self.dango.set_mode("THINKING")

    # ── Render Dango display → pygame surface ─────────────────────────────────
    def _get_display_surface(self):
        if self.state == "IDLE":
            pil_img = self.widgets.render()
        else:
            pil_img = self.dango.render()

        # Mirror (as Pi does for beam splitter)
        pil_img = pil_img.transpose(Image.FLIP_LEFT_RIGHT)

        # PIL → pygame
        pil_img = pil_img.convert("RGB")
        raw = pil_img.tobytes()
        surf = pygame.image.fromstring(raw, (240, 240), "RGB")
        surf = pygame.transform.scale(surf, (DISPLAY_SIZE, DISPLAY_SIZE))
        return surf

    # ── Draw debug panel ──────────────────────────────────────────────────────
    def _draw_panel(self):
        px = DISPLAY_SIZE
        panel = pygame.Rect(px, 0, PANEL_W, WIN_H)
        pygame.draw.rect(self.screen, C_PANEL, panel)
        pygame.draw.line(self.screen, C_BORDER, (px, 0), (px, WIN_H), 2)

        x = px + 16
        y = 16

        # Title
        title = self.font_title.render("DANGO SIMULATOR", True, C_CYAN)
        self.screen.blit(title, (x, y)); y += 22
        pygame.draw.line(self.screen, C_BORDER, (x, y), (px + PANEL_W - 16, y), 1)
        y += 10

        # State badge
        sc = STATE_COLOURS.get(self.state, C_WHITE)
        badge_surf = self.font_state.render(f"● {self.state}", True, sc)
        self.screen.blit(badge_surf, (x, y)); y += 34

        # Controls
        controls = [
            ("SPACE", "Simulate wake word"),
            ("ENTER", "Send typed text"),
            ("R",     "Reset to IDLE"),
            ("Q/ESC", "Quit"),
        ]
        for key, desc in controls:
            k = self.font_small.render(f"[{key}]", True, C_YELLOW)
            d = self.font_small.render(desc, True, C_GREY)
            self.screen.blit(k, (x, y))
            self.screen.blit(d, (x + 60, y))
            y += 16
        y += 8
        pygame.draw.line(self.screen, C_BORDER, (x, y), (px + PANEL_W - 16, y), 1)
        y += 10

        # Input box
        label = self.font_title.render("TYPE INPUT:", True, C_CYAN_DIM)
        self.screen.blit(label, (x, y)); y += 18

        box_rect = pygame.Rect(x, y, PANEL_W - 32, 28)
        self.input_box_rect = box_rect          # store for click detection
        box_col  = C_CYAN_DIM if self.input_active else C_BORDER
        pygame.draw.rect(self.screen, C_INPUT_BG, box_rect, border_radius=4)
        pygame.draw.rect(self.screen, box_col, box_rect, 1, border_radius=4)

        display_text = self.input_text
        if self.input_active and int(time.time() * 2) % 2 == 0:
            display_text += "|"
        inp_surf = self.font_body.render(display_text[:38], True, C_WHITE)
        self.screen.blit(inp_surf, (x + 6, y + 6))
        y += 38

        hint = self.font_small.render("Click box to type, ENTER to send", True, C_GREY)
        self.screen.blit(hint, (x, y)); y += 20
        pygame.draw.line(self.screen, C_BORDER, (x, y), (px + PANEL_W - 16, y), 1)
        y += 10

        # Log
        log_label = self.font_title.render("LOG:", True, C_CYAN_DIM)
        self.screen.blit(log_label, (x, y)); y += 18

        for msg, col in self.log[-(self.max_log):]:
            surf = self.font_small.render(msg[:44], True, col)
            self.screen.blit(surf, (x, y))
            y += 15
            if y > WIN_H - 10:
                break

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            # ── Events ────────────────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        pygame.quit(); sys.exit()

                    elif event.key == pygame.K_SPACE and self.state == "IDLE":
                        self._log("Wake word simulated!", C_YELLOW)
                        self.dango.set_mode("IDLE")
                        self.dango.set_emotion("neutral")
                        self.dango.trigger_wake()
                        self.state = "WAKE"

                    elif event.key == pygame.K_r:
                        self._log("Reset to IDLE", C_GREY)
                        self.dango.set_mode("IDLE")
                        self.dango.set_emotion("neutral")
                        self.state = "IDLE"

                    elif event.key == pygame.K_RETURN and self.input_active:
                        text = self.input_text.strip()
                        self.input_text = ""
                        if text:
                            self._handle_text_submit(text)
                            self.dango.set_mode("THINKING")
                            self.state = "THINKING"

                    elif event.key == pygame.K_BACKSPACE and self.input_active:
                        self.input_text = self.input_text[:-1]

                    elif self.input_active and event.unicode.isprintable():
                        self.input_text += event.unicode

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    box = getattr(self, "input_box_rect", None)
                    if box:
                        self.input_active = box.collidepoint(x, y)
                    else:
                        self.input_active = False

            # ── State machine ─────────────────────────────────────────────────
            if self.state == "WAKE":
                if not self.dango.wake_active:
                    self._log("Listening... (type + ENTER)", C_GREEN)
                    self.dango.set_mode("LISTENING")
                    self.state = "CAPTURING"

            elif self.state == "LINGER":
                if self.linger_time and time.time() - self.linger_time > self.FACE_LINGER:
                    self.dango.set_mode("IDLE")
                    self.dango.set_emotion("neutral")
                    self.state = "IDLE"
                    self._log("Back to idle screen", C_GREY)

            # ── Draw ──────────────────────────────────────────────────────────
            self.screen.fill(C_BG)

            # Dango display
            display_surf = self._get_display_surface()
            self.screen.blit(display_surf, (0, 0))

            # Thin border around display
            pygame.draw.rect(self.screen, C_BORDER,
                             pygame.Rect(0, 0, DISPLAY_SIZE, DISPLAY_SIZE), 2)

            # Debug panel
            self._draw_panel()

            pygame.display.flip()


if __name__ == "__main__":
    sim = DangoSimulator()
    sim.run()
