"""
Lightweight TTS for Dango using piper-tts (fully local, fast on Pi 4).

Install:
    pip install piper-tts
    python -m piper --download-dir models en_US-lessac-medium

Or use espeak as a fallback (already on most Pi installs):
    sudo apt install espeak-ng
"""

import subprocess
import os
import threading

# --- Choose your TTS backend ---
# Options: "piper" | "espeak"
TTS_BACKEND = "espeak"

PIPER_MODEL = "models/en_US-lessac-medium.onnx"


def speak(text, blocking=False):
    """Speak text aloud. Non-blocking by default."""
    thread = threading.Thread(target=_speak, args=(text,), daemon=True)
    thread.start()
    if blocking:
        thread.join()


def _speak(text):
    try:
        if TTS_BACKEND == "piper":
            _speak_piper(text)
        else:
            _speak_espeak(text)
    except Exception as e:
        print(f"[TTS Error] {e}")


def _speak_piper(text):
    """Piper TTS — better quality, ~0.3s latency on Pi 4."""
    proc = subprocess.Popen(
        ["python", "-m", "piper", "--model", PIPER_MODEL, "--output-raw"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    audio, _ = proc.communicate(input=text.encode())

    # Play raw 22050Hz mono s16 audio via aplay
    play = subprocess.Popen(
        ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    play.communicate(input=audio)


def _speak_espeak(text):
    """espeak-ng — lower quality but zero setup, already on Pi."""
    subprocess.run(
        ["espeak-ng", "-s", "155", "-p", "60", "-a", "180", text],
        stderr=subprocess.DEVNULL
    )
