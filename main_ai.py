"""
main_ai.py — Full Dango AI mode with clock/weather idle screen

Flow:
  IDLE      → shows clock + weather widget
  Wake word → WAKE animation (face appears)
  LISTENING → mic captures speech
  THINKING  → SLM generates reply (face animates)
  ANSWERING → TTS speaks + face shows emotion
  IDLE      → back to clock/weather

Requirements:
    pip install pvporcupine pyaudio speechrecognition requests numpy pillow sounddevice --break-system-packages
    sudo apt install espeak-ng flac portaudio19-dev -y
    ollama pull qwen2.5:0.5b
"""

import time
import numpy as np
import pvporcupine
import pyaudio
import speech_recognition as sr
from PIL import Image

from renderer import JarvisRenderer
from display import ST7789Display
from brain import DangoBrain
from tts import speak
from widgets import WidgetRenderer

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------
ACCESS_KEY         = "q4JisBewS45WIcWMor0xG7DvlzEAE7nOS1P1MQSc0SluiqFYz2HO3Q=="
KEYWORD_PATH       = "dango_en_raspberry-pi_v4_0_0.ppn"

MIC_RATE           = 48000
PORCUPINE_RATE     = 16000
DOWNSAMPLE_FACTOR  = 3
INPUT_DEVICE_INDEX = 1        # Change to your USB mic index

LISTEN_TIMEOUT     = 5
LISTEN_PHRASE_TIME = 6

# How long to show the face after answering before returning to widget
FACE_LINGER_SECS   = 2.0

# --------------------------------------------------
# INIT
# --------------------------------------------------
dango   = JarvisRenderer()
dango.set_mode("IDLE")
disp    = ST7789Display()
widgets = WidgetRenderer()

recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keyword_paths=[KEYWORD_PATH]
)

pa = pyaudio.PyAudio()
audio_stream = pa.open(
    rate=MIC_RATE,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    input_device_index=INPUT_DEVICE_INDEX,
    frames_per_buffer=porcupine.frame_length * DOWNSAMPLE_FACTOR
)

# State machine
# IDLE       -> widget screen (clock + weather)
# WAKE       -> wake animation playing
# CAPTURING  -> listening for speech
# THINKING   -> LLM processing (managed by brain callbacks)
# ANSWERING  -> TTS speaking (managed by brain callbacks)
# LINGER     -> brief pause showing face before returning to widget
state       = "IDLE"
linger_time = None

# --------------------------------------------------
# BRAIN CALLBACKS
# --------------------------------------------------
def on_thinking_start():
    global state
    dango.set_mode("THINKING")
    dango.set_emotion("neutral")
    state = "THINKING"

def on_reply(text, emotion):
    global state, linger_time
    print(f"[Dango] {text}  (emotion: {emotion})")
    dango.set_mode("ANSWERING")
    dango.set_emotion(emotion)
    state = "ANSWERING"
    speak(text)
    linger_time = time.time()
    state = "LINGER"

def on_error(msg):
    global state, linger_time
    print(f"[Brain Error] {msg}")
    speak("Sorry, I had a brain blip.")
    dango.set_mode("IDLE")
    dango.set_emotion("sad")
    linger_time = time.time()
    state = "LINGER"

brain = DangoBrain(
    on_start=on_thinking_start,
    on_done=on_reply,
    on_error=on_error
)

# --------------------------------------------------
# SPEECH RECOGNITION
# --------------------------------------------------
def capture_speech():
    print("[Dango] Listening for speech...")
    with sr.Microphone(device_index=INPUT_DEVICE_INDEX) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = recognizer.listen(
                source,
                timeout=LISTEN_TIMEOUT,
                phrase_time_limit=LISTEN_PHRASE_TIME
            )
            text = recognizer.recognize_google(audio)
            print(f"[You] {text}")
            return text
        except sr.WaitTimeoutError:
            print("[Dango] No speech heard.")
            return None
        except sr.UnknownValueError:
            print("[Dango] Couldn't understand.")
            return None

# --------------------------------------------------
# RENDER HELPERS
# --------------------------------------------------
def render_widget():
    frame = widgets.render()
    frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
    disp.display_image(frame)

def render_face():
    frame = dango.render()
    frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
    disp.display_image(frame)

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------
print("Dango started. Showing clock. Say 'Dango' to wake up.")

try:
    while True:

        # IDLE: show widget, listen for wake word
        if state == "IDLE":
            render_widget()

            pcm = audio_stream.read(
                porcupine.frame_length * DOWNSAMPLE_FACTOR,
                exception_on_overflow=False
            )
            pcm    = np.frombuffer(pcm, dtype=np.int16)[::DOWNSAMPLE_FACTOR]
            result = porcupine.process(pcm)

            if result >= 0:
                print("[Dango] Wake word detected!")
                dango.set_mode("IDLE")
                dango.set_emotion("neutral")
                dango.trigger_wake()
                state = "WAKE"

        # WAKE: play wake animation, then go to listening
        elif state == "WAKE":
            render_face()
            if not dango.wake_active:
                dango.set_mode("LISTENING")
                state = "CAPTURING"

        # CAPTURING: listen for speech
        elif state == "CAPTURING":
            render_face()
            text = capture_speech()
            if text:
                brain.chat(text)
            else:
                dango.set_mode("IDLE")
                state = "IDLE"

        # THINKING / ANSWERING: managed by brain callbacks
        elif state in ("THINKING", "ANSWERING"):
            render_face()
            time.sleep(0.016)

        # LINGER: show face briefly before returning to widget
        elif state == "LINGER":
            render_face()
            if linger_time and time.time() - linger_time > FACE_LINGER_SECS:
                dango.set_mode("IDLE")
                dango.set_emotion("neutral")
                state = "IDLE"
            else:
                time.sleep(0.016)

except KeyboardInterrupt:
    print("\nShutting down Dango.")

finally:
    audio_stream.close()
    pa.terminate()
    porcupine.delete()
