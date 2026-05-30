import pvporcupine
import sounddevice as sd
import numpy as np

ACCESS_KEY = "q4JisBewS45WIcWMor0xG7DvlzEAE7nOS1P1MQSc0SluiqFYz2HO3Q=="
KEYWORD_PATH = "dango_en_raspberry-pi_v4_0_0.ppn"

porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keyword_paths=[KEYWORD_PATH]
)

PORCUPINE_RATE = porcupine.sample_rate      # 16000
FRAME_LENGTH = porcupine.frame_length       # 512

MIC_RATE = 48000
DOWNSAMPLE = MIC_RATE // PORCUPINE_RATE

print("Wake system ready.")
print("Listening...")

def callback(indata, frames, time_info, status):
    if status:
        return

    audio = np.frombuffer(indata, dtype=np.int16)

    # Downsample 48k → 16k
    audio = audio[::DOWNSAMPLE]

    for i in range(0, len(audio), FRAME_LENGTH):
        frame = audio[i:i+FRAME_LENGTH]
        if len(frame) == FRAME_LENGTH:
            result = porcupine.process(frame)
            if result >= 0:
                print("Wake word detected!")

with sd.InputStream(
    samplerate=MIC_RATE,
    channels=1,
    dtype="int16",
    blocksize=FRAME_LENGTH * DOWNSAMPLE,
    latency="low",
    callback=callback
):
    while True:
        pass
