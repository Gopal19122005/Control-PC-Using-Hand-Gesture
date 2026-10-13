
import pyautogui


class MediaController:
    """Control media playback using hand gestures."""

    def __init__(self):
        self.last_gesture = None

    def get_action(self, fingers):
        index = fingers["INDEX"]
        middle = fingers["MIDDLE"]
        ring = fingers["RING"]
        pinky = fingers["PINKY"]

        # Index + pinky: Play / Pause
        if index and not middle and not ring and pinky:
            return "playpause", "PLAY / PAUSE"

        # Index + middle + ring: Next track
        if index and middle and ring and not pinky:
            return "nexttrack", "NEXT TRACK"

        # Middle + ring: Previous track
        if not index and middle and ring and not pinky:
            return "prevtrack", "PREVIOUS TRACK"

        # Pinky only: Mute / Unmute
        if not index and not middle and not ring and pinky:
            return "volumemute", "MUTE / UNMUTE"

        return None, None

    def handle_gesture(self, fingers):
        """Trigger one media action per gesture."""
        key, label = self.get_action(fingers)

        if key is None:
            self.last_gesture = None
            return None

        if key != self.last_gesture:
            pyautogui.press(key)
            self.last_gesture = key

        return label

    def reset(self):
        """Reset gesture tracking when the hand disappears."""
        self.last_gesture = None
