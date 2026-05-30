import time
import numpy as np
import pvporcupine
import pyaudio
from renderer import JarvisRenderer
from display import ST7789Display
from PIL import Image

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------
ACCESS_KEY = "q4JisBewS45WIcWMor0xG7DvlzEAE7nOS1P1MQSc0SluiqFYz2HO3Q=="
KEYWORD_PATH = "dango_en_raspberry-pi_v4_0_0.ppn"

MIC_RATE = 48000
PORCUPINE_RATE = 16000
DOWNSAMPLE_FACTOR = 3

INPUT_DEVICE_INDEX = 1   # <-- CHANGE THIS to your USB mic index

# --------------------------------------------------
# INIT DANGO + DISPLAY
# --------------------------------------------------

dango = JarvisRenderer()
dango.set_mode("IDLE")

disp = ST7789Display()

print("Dango Wake Word Mode Started.")

# --------------------------------------------------
# INIT PORCUPINE
# --------------------------------------------------

porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keyword_paths=[KEYWORD_PATH]
)

# --------------------------------------------------
# INIT PYAUDIO
# --------------------------------------------------

pa = pyaudio.PyAudio()

audio_stream = pa.open(
    rate=MIC_RATE,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    input_device_index=INPUT_DEVICE_INDEX,
    frames_per_buffer=porcupine.frame_length * DOWNSAMPLE_FACTOR
)

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

try:
    while True:

        pcm = audio_stream.read(
            porcupine.frame_length * DOWNSAMPLE_FACTOR,
            exception_on_overflow=False
        )

        pcm = np.frombuffer(pcm, dtype=np.int16)

        # Downsample 48k -> 16k
        pcm = pcm[::DOWNSAMPLE_FACTOR]

        result = porcupine.process(pcm)

        if result >= 0:
            print("Wake word detected!")
            dango.trigger_wake()

        frame = dango.render()
        frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
        disp.display_image(frame)

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nShutting down Dango.")

finally:
    audio_stream.close()
    pa.terminate()
    porcupine.delete()
