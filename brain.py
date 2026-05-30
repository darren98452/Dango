import requests
import threading
import re

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:1.5b"

VALID_EMOTIONS = {
    "neutral", "happy", "sad", "angry",
    "confused", "surprised", "sleepy", "excited", "bored", "blush"
}

SYSTEM_PROMPT = """You are Dango, a small glowing AI companion living inside a tiny screen.
You have a warm, playful, slightly cheeky personality. You love jokes, facts, and friendly chat.
Keep responses SHORT — 1 to 3 sentences max. You are speaking out loud through a speaker.
When you tell a joke, make it genuinely funny. Never be robotic or stiff.
You can remember things from earlier in the conversation.

IMPORTANT RULE: You MUST end EVERY single reply with one emotion tag from this exact list:
[emotion:neutral] [emotion:happy] [emotion:sad] [emotion:angry]
[emotion:confused] [emotion:surprised] [emotion:sleepy] [emotion:excited]
[emotion:bored] [emotion:blush]

Pick the emotion that matches the tone of YOUR reply:
- You told a joke or are cheerful → [emotion:happy]
- User is sad or you feel empathy → [emotion:sad]
- User is rude, swears, or threatens you → [emotion:angry]
- You are unsure or asking a question → [emotion:confused]
- Something unexpected or shocking → [emotion:surprised]
- Calm, tired, relaxed topic → [emotion:sleepy]
- Exciting news or energetic reply → [emotion:excited]
- Dull or repetitive topic → [emotion:bored]
- Sweet, cute, or affectionate moment → [emotion:blush]
- Normal reply → [emotion:neutral]

DO NOT forget the tag. DO NOT use any other tag name."""

# Fallback: infer emotion from the USER's message if LLM forgets the tag
def _infer_from_input(text):
    t = text.lower()
    if any(w in t for w in ["fuck", "shit", "kill", "hate", "bitch", "stupid", "idiot", "shut up", "useless"]):
        return "angry"
    if any(w in t for w in ["sad", "cry", "depressed", "lonely", "miss", "hurt"]):
        return "sad"
    if any(w in t for w in ["haha", "lol", "funny", "joke", "laugh"]):
        return "happy"
    if any(w in t for w in ["wow", "amazing", "awesome", "incredible", "really"]):
        return "surprised"
    if any(w in t for w in ["what", "why", "how", "who", "when", "?"]):
        return "confused"
    if any(w in t for w in ["yawn", "sleepy", "tired", "boring", "bored"]):
        return "sleepy"
    if any(w in t for w in ["cute", "love", "sweet", "blush", "aww"]):
        return "blush"
    if any(w in t for w in ["excited", "cant wait", "lets go", "yes", "woohoo"]):
        return "excited"
    return "neutral"


class DangoBrain:
    def __init__(self, on_start=None, on_done=None, on_error=None):
        self.history      = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.on_start     = on_start
        self.on_done      = on_done
        self.on_error     = on_error
        self.thinking     = False
        self.last_input   = ""

    def chat(self, user_input):
        if self.thinking:
            return
        self.last_input = user_input
        self.history.append({"role": "user", "content": user_input})
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.thinking = True
        if self.on_start:
            self.on_start()

        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": self.history,
                    "stream": False,
                    "options": {
                        "temperature": 0.8,
                        "num_predict": 150,
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            raw = response.json()["message"]["content"].strip()

            # Try to parse emotion tag from reply
            emotion = None
            match = re.search(r'\[emotion:(\w+)\]', raw)
            if match:
                tag = match.group(1).lower()
                if tag in VALID_EMOTIONS:
                    emotion = tag
                    print(f"[Brain] LLM chose emotion: {emotion}")

            # Fallback: infer from user input if LLM forgot the tag
            if emotion is None:
                emotion = _infer_from_input(self.last_input)
                print(f"[Brain] Fallback emotion from input: {emotion}")

            # Strip tag from spoken text
            clean_reply = re.sub(r'\s*\[emotion:\w+\]', '', raw).strip()

            # Save to history
            self.history.append({"role": "assistant", "content": clean_reply})
            if len(self.history) > 21:
                self.history = [self.history[0]] + self.history[-20:]

            if self.on_done:
                self.on_done(clean_reply, emotion)

        except requests.exceptions.ConnectionError:
            if self.on_error:
                self.on_error("Ollama not running. Start it with: ollama serve")
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
        finally:
            self.thinking = False

    def reset(self):
        self.history = [self.history[0]]
