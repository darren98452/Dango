import time

class StateManager:

    def __init__(self):
        self.state = "idle"
        self.last_change = time.time()

    def set_state(self, new_state):
        self.state = new_state
        self.last_change = time.time()
