# Dango 🟣

A local AI companion that lives inside a tiny 240×240 screen on a Raspberry Pi. It wakes up when you call its name, listens to you, thinks, and replies with a matching facial expression — all running fully offline.

---

## What it does

- **Idle** — shows a glowing clock and live weather on the display
- **Wake** — say *"Dango"* and it animates to life
- **Listen** — captures your speech via microphone
- **Think** — generates a reply using a local LLM (no internet needed)
- **Reply** — speaks the answer out loud and shows a matching emotion on its face

---

## The Face

Dango has 10 emotions rendered as animated eyes on the display:

| Emotion | Trigger |
|---|---|
| 😐 Neutral | Default, calm replies |
| 😊 Happy | Jokes, cheerful responses |
| 😢 Sad | Empathy, bad news |
| 😠 Angry | Rude or aggressive input |
| 😕 Confused | Uncertain, questions |
| 😲 Surprised | Unexpected or shocking info |
| 😴 Sleepy | Tired, boring topics |
| 🤩 Excited | Great news, energetic replies |
| 😑 Bored | Repetitive or dull topics |
| 😊 Blush | Cute, sweet, affectionate moments |

---

## Hardware

- Raspberry Pi 4 (4GB)
- 240×240 ST7789 SPI display
- USB microphone
- Small speaker

---

## Software Stack

| Component | Technology |
|---|---|
| Wake word | Picovoice Porcupine |
| Speech to text | Google STT (via SpeechRecognition) |
| Local LLM | Ollama — qwen2.5:3b |
| Text to speech | espeak-ng |
| Face renderer | Pillow (PIL) |
| Display driver | SPI via RPi.GPIO + spidev |
| Weather | OpenWeatherMap API |

---

## Project Structure

```
Dango/
├── main_ai.py       — main entry point, state machine
├── brain.py         — LLM via Ollama, emotion detection
├── renderer.py      — animated face, 10 emotions
├── display.py       — ST7789 hardware driver
├── widgets.py       — clock + weather idle screen
├── tts.py           — text to speech
├── simulate.py      — desktop simulator (no Pi needed)
├── modules/
│   └── time_ui.py   — time overlay helper
├── dango_en_raspberry-pi_v4_0_0.ppn  — wake word model
├── requirements.txt
└── .gitignore
```

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/darren98452/Dango.git
cd Dango
```

### 2. Install dependencies
```bash
pip install -r requirements.txt --break-system-packages
sudo apt install espeak-ng flac portaudio19-dev -y
```

### 3. Install Ollama and pull the model
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
```

### 4. Set your weather API key
In `widgets.py` set your city and free API key from [openweathermap.org](https://openweathermap.org/api):
```python
OWM_API_KEY = "your_api_key_here"
CITY        = "London"
```

### 5. Set your mic device index
Find your USB mic index:
```bash
python3 -c "import pyaudio; p = pyaudio.PyAudio(); [print(i, p.get_device_info_by_index(i)['name']) for i in range(p.get_device_count())]"
```
Then set it in `main_ai.py`:
```python
INPUT_DEVICE_INDEX = 1  # change to your mic index
```

---

## Run on Raspberry Pi

```bash
# Terminal 1 — start Ollama
ollama serve

# Terminal 2 — start Dango
python3 main_ai.py
```

Say **"Dango"** to wake it up.

---

## Simulate on Desktop (no Pi needed)

```bash
pip install pygame --break-system-packages
python3 simulate.py
```

| Key | Action |
|---|---|
| `SPACE` | Simulate wake word |
| Click input + type + `ENTER` | Send a message |
| `R` | Reset to idle screen |
| `Q` / `ESC` | Quit |

---

## How the state machine works

```
IDLE (clock + weather)
  ↓ wake word detected
WAKE (animation plays)
  ↓ animation finishes
CAPTURING (mic listening)
  ↓ speech recognised
THINKING (LLM generating, face scans)
  ↓ reply ready
ANSWERING (TTS speaks, face shows emotion)
  ↓ after 2 seconds
IDLE
```

---

## License

See `LICENSE.txt` — wake word model subject to [Picovoice terms](https://picovoice.ai/docs/terms-of-use/).
