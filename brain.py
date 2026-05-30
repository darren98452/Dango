import requests
import threading
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:0.5b"

SYSTEM_PROMPT = """You are Dango, a small glowing AI companion living inside a tiny screen.
You have a warm, playful, slightly cheeky personality. You love jokes, facts, and friendly chat.
Keep responses SHORT — 1 to 3 sentences max. You are speaking out loud through a speaker.
When you tell a joke, make it genuinely funny. Never be robotic or stiff.
You can remember things from earlier in the conversation."""


class DangoBrain:
    def __init__(self, on_start=None, on_done=None, on_error=None):
        """
        Callbacks:
          on_start()           — called when thinking begins
          on_done(text, emotion) — called with the response text + suggested emotion
          on_error(msg)        — called on failure
        """
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.on_start = on_start
        self.on_done = on_done
        self.on_error = on_error
        self.thinking = False

    def chat(self, user_input):
        """Non-blocking: fires off the LLM call in a background thread."""
        if self.thinking:
            return  # Already processing

        self.history.append({"role": "user", "content": user_input})
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

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
                        "num_predict": 120,   # Keep replies short
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            reply = data["message"]["content"].strip()

            self.history.append({"role": "assistant", "content": reply})

            # Keep conversation history from growing too large
            if len(self.history) > 21:  # system + 10 turns
                self.history = [self.history[0]] + self.history[-20:]

            emotion = self._infer_emotion(reply)

            if self.on_done:
                self.on_done(reply, emotion)

        except requests.exceptions.ConnectionError:
            if self.on_error:
                self.on_error("Ollama not running. Start it with: ollama serve")
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
        finally:
            self.thinking = False

    def _infer_emotion(self, text):
        """Guess an emotion from the reply text to animate Dango's face."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["haha", "lol", "funny", "joke", "laugh", "😄", "😂"]):
            return "happy"
        if any(w in text_lower for w in ["sorry", "sad", "unfortunate", "miss", "lonely"]):
            return "sad"
        if any(w in text_lower for w in ["wow", "amazing", "incredible", "whoa", "!"]):
            return "excited"
        if any(w in text_lower for w in ["hmm", "thinking", "not sure", "maybe", "perhaps", "?"]):
            return "confused"
        if any(w in text_lower for w in ["oh!", "really?", "what!", "surprising"]):
            return "surprised"
        if any(w in text_lower for w in ["sleepy", "tired", "yawn", "zzz", "night"]):
            return "sleepy"
        if any(w in text_lower for w in ["remember", "noted", "saved", "got it", "sure"]):
            return "blush"

        return "neutral"

    def reset(self):
        """Clear conversation history but keep the system prompt."""
        self.history = [self.history[0]]
