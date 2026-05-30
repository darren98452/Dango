import time
import random
from renderer import JarvisRenderer
from display import ST7789Display
from PIL import Image

def main():

    henry = JarvisRenderer()
    henry.set_mode("IDLE")

    disp = ST7789Display()

    print("Dango display test mode started.")

    state = "IDLE"
    state_timer = time.time()

    emotions = [
        "neutral",
        "happy",
        "sad",
        "angry",
        "confused",
        "surprised",
        "sleepy",
        "excited",
        "bored",
        "blush"
    ]

    try:
        while True:

            now = time.time()

            # ----------------------------
            # STATE FLOW FOR TESTING
            # ----------------------------

            if state == "IDLE" and now - state_timer > 4:
                print("Wake triggered")
                henry.trigger_wake()
                state = "WAKE"
                state_timer = now

            elif state == "WAKE" and not henry.wake_active:
                print("Listening")
                henry.set_mode("LISTENING")
                state = "LISTENING"
                state_timer = now

            elif state == "LISTENING" and now - state_timer > 3:
                print("Thinking")
                henry.set_mode("THINKING")
                henry.set_emotion("neutral")
                state = "THINKING"
                state_timer = now

            elif state == "THINKING" and now - state_timer > 3:
                print("Answering")
                henry.set_mode("ANSWERING")

                chosen_emotion = random.choice(emotions)
                henry.set_emotion(chosen_emotion)

                print("Emotion:", chosen_emotion)

                state = "ANSWERING"
                state_timer = now

            elif state == "ANSWERING" and now - state_timer > 4:
                print("Back to idle")
                henry.set_mode("IDLE")
                henry.set_emotion("neutral")
                state = "IDLE"
                state_timer = now

            # ----------------------------
            # RENDER TO DISPLAY
            # ----------------------------

            frame = henry.render()

            # Flip if using hologram reflection
            frame = frame.transpose(Image.FLIP_LEFT_RIGHT)

            disp.display_image(frame)

            time.sleep(0.016)  # ~60 FPS

    except KeyboardInterrupt:
        print("\nShutting down Dango.")


if __name__ == "__main__":
    main()
