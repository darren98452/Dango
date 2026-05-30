# Dango 🟣

An AI companion that lives on a Raspberry Pi with a 240x240 ST7789 display.

## Features
- Animated face with 10 emotions
- Wake word detection ("Dango") via Picovoice Porcupine
- Local LLM via Ollama (qwen2.5:3b)
- Clock + weather idle screen
- Text-to-speech via espeak

## Setup
```bash
pip install -r requirements.txt --break-system-packages
sudo apt install espeak-ng flac portaudio19-dev -y
ollama pull qwen2.5:3b
```

## Run (Pi)
```bash
python3 main_ai.py
```

## Simulate (desktop)
```bash
pip install pygame --break-system-packages
python3 simulate.py
```

## Controls (simulator)
- `SPACE` — trigger wake word
- Click input box + type + `ENTER` — send message
- `R` — reset to idle
- `Q` — quit
