
import math
import time

import pyautogui


class MouseController:
    """Mouse movement, clicking, drag-and-drop, and scrolling."""

    PALM_POINTS = [0, 5, 9, 13, 17]

    def __init__(self, smoothing=0.30):
        self.screen_width, self.screen_height = pyautogui.size()
        self.smoothing = smoothing

        # Cursor smoothing
        self.previous_x = None
        self.previous_y = None

        self.min_x = 0.20
        self.max_x = 0.80
        self.min_y = 0.20
        self.max_y = 0.80
        
        # Thumb-index pinch
        self.pinch_threshold = 0.28
        self.release_threshold = 0.42
        self.click_cooldown = 0.45
        self.is_pinching = False
        self.last_click_time = 0.0

        # Thumb-middle pinch
        self.right_pinch_threshold = 0.28
        self.right_release_threshold = 0.42
        self.right_is_pinching = False
        self.last_right_click_time = 0.0
        self.right_click_cooldown = 0.45

        # Scroll configuration
        self.previous_scroll_y = None
        self.filtered_scroll_y = None
        self.scroll_sensitivity = 3500
        self.scroll_threshold = 0.0007
        self.scroll_smoothing = 0.35
        self.max_scroll_per_frame = 8

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.02

    def palm_center(self, landmarks):
        """Calculate the normalized palm center."""
        palm_x = sum(
            landmarks[i].x for i in self.PALM_POINTS
        ) / len(self.PALM_POINTS)

        palm_y = sum(
            landmarks[i].y for i in self.PALM_POINTS
        ) / len(self.PALM_POINTS)

        return palm_x, palm_y

    def move_from_palm(self, landmarks):
        """Move the cursor using the palm center."""
        palm_x, palm_y = self.palm_center(landmarks)

        x = max(self.min_x, min(self.max_x, palm_x))
        y = max(self.min_y, min(self.max_y, palm_y))

        target_x = int(
            (x - self.min_x)
            / (self.max_x - self.min_x)
            * (self.screen_width - 1)
        )

        target_y = int(
            (y - self.min_y)
            / (self.max_y - self.min_y)
            * (self.screen_height - 1)
        )

        if self.previous_x is None:
            self.previous_x = target_x
            self.previous_y = target_y

        current_x = self.previous_x + self.smoothing * (
            target_x - self.previous_x
        )

        current_y = self.previous_y + self.smoothing * (
            target_y - self.previous_y
        )

        current_x = max(
            0, min(self.screen_width - 1, int(current_x))
        )

        current_y = max(
            0, min(self.screen_height - 1, int(current_y))
        )

        pyautogui.moveTo(current_x, current_y)

        self.previous_x = current_x
        self.previous_y = current_y

        return current_x, current_y

    @staticmethod
    def landmark_distance(landmarks, first, second):
        """Calculate distance between two hand landmarks."""
        a = landmarks[first]
        b = landmarks[second]

        return math.hypot(
            a.x - b.x,
            a.y - b.y,
        )

    def handle_pinch(self, landmarks):
        """Thumb-index pinch: click once per pinch."""
        distance = self.landmark_distance(
            landmarks, 4, 8
        )

        palm_width = self.landmark_distance(
            landmarks, 5, 17
        )

        if palm_width < 0.001:
            return False

        ratio = distance / palm_width
        now = time.monotonic()

        # Wait for the previous pinch to be released.
        if self.is_pinching:
            if ratio > self.release_threshold:
                self.is_pinching = False
            return False

        if (
            ratio < self.pinch_threshold
            and now - self.last_click_time
            >= self.click_cooldown
        ):
            self.is_pinching = True
            self.last_click_time = now

            # Approximate taskbar detection for a bottom taskbar.
            _, cursor_y = pyautogui.position()
            taskbar_height = 65

            if cursor_y >= self.screen_height - taskbar_height:
                # Taskbar icons normally need one click.
                pyautogui.click(button="left")
            else:
                # Desktop shortcuts normally need a double-click.
                pyautogui.doubleClick(
                    button="left",
                    interval=0.12,
                )

            return True

        return False

    def handle_right_pinch(self, landmarks):
        """Thumb-middle pinch: right-click once per pinch."""
        distance = self.landmark_distance(
            landmarks, 4, 12
        )

        palm_width = self.landmark_distance(
            landmarks, 5, 17
        )

        if palm_width < 0.001:
            return False

        ratio = distance / palm_width
        now = time.monotonic()

        if self.right_is_pinching:
            if ratio > self.right_release_threshold:
                self.right_is_pinching = False
            return False

        if (
            ratio < self.right_pinch_threshold
            and now - self.last_right_click_time
            >= self.right_click_cooldown
        ):
            self.right_is_pinching = True
            self.last_right_click_time = now

            pyautogui.click(button="right")
            return True

        return False

    @staticmethod
    def finger_states(landmarks):
        """Detect whether each non-thumb finger is extended."""

        def extended(tip, pip):
            return landmarks[tip].y < landmarks[pip].y

        return {
            "INDEX": extended(8, 6),
            "MIDDLE": extended(12, 10),
            "RING": extended(16, 14),
            "PINKY": extended(20, 18),
        }

    def is_scroll_gesture(self, landmarks):
        """Index and middle fingers up; ring and pinky down."""
        fingers = self.finger_states(landmarks)

        return (
            fingers["INDEX"]
            and fingers["MIDDLE"]
            and not fingers["RING"]
            and not fingers["PINKY"]
        )

    def scroll_from_palm(self, landmarks):
        """Scroll based on vertical palm movement."""
        _, palm_y = self.palm_center(landmarks)

        if self.filtered_scroll_y is None:
            self.filtered_scroll_y = palm_y
            self.previous_scroll_y = palm_y
            return 0

        self.filtered_scroll_y += self.scroll_smoothing * (
            palm_y - self.filtered_scroll_y
        )

        movement = (
            self.previous_scroll_y - self.filtered_scroll_y
        )

        self.previous_scroll_y = self.filtered_scroll_y

        if abs(movement) < self.scroll_threshold:
            return 0

        amount = int(
            movement * self.scroll_sensitivity
        )

        if amount == 0:
            return 0

        amount = max(
            -self.max_scroll_per_frame,
            min(self.max_scroll_per_frame, amount),
        )

        pyautogui.scroll(amount)
        return amount

    def reset_scroll(self):
        """Reset the scroll reference and filter."""
        self.previous_scroll_y = None
        self.filtered_scroll_y = None

    def reset(self):
        """Reset tracking state when no hand is detected."""
        self.previous_x = None
        self.previous_y = None
        self.reset_scroll()
        self.is_pinching = False
        self.right_is_pinching = False
