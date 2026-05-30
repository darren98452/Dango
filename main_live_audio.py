import time
import numpy as np
import sounddevice as sd
from renderer import JarvisRenderer
from display import ST7789Display
from PIL import Image

SAMPLE_RATE = 16000
BLOCK_SIZE = 1024
VOLUME_THRESHOLD = 0.01
SILENCE_TIMEOUT = 1.2
THINK_DURATION = 1.5

dango = JarvisRenderer()
dango.set_mode("IDLE")

disp = ST7789Display()

last_sound_time = time.time()
thinking_start = None
current_state = "IDLE"

print("Dango live mic mode started.")

def audio_callback(indata, frames, time_info, status):
    global last_sound_time
    volume = np.sqrt(np.mean(indata**2))
    if volume > VOLUME_THRESHOLD:
        last_sound_time = time.time()

stream = sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    blocksize=BLOCK_SIZE,
    callback=audio_callback
)

stream.start()

try:
    while True:

        now = time.time()

        if now - last_sound_time < 0.2:
            if current_state != "LISTENING":
                dango.set_mode("LISTENING")
                dango.set_emotion("neutral")
                current_state = "LISTENING"

        elif now - last_sound_time > SILENCE_TIMEOUT:
            if current_state == "LISTENING":
                dango.set_mode("THINKING")
                current_state = "THINKING"
                thinking_start = now

        if current_state == "THINKING":
            if now - thinking_start > THINK_DURATION:
                dango.set_mode("IDLE")
                current_state = "IDLE"

        frame = dango.render()
        frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
        disp.display_image(frame)

        time.sleep(0.016)

except KeyboardInterrupt:
    print("\nShutting down Dango.")
    stream.stop()
