
import cv2
import pyautogui
import math
import time

from vision.hand_detector import HandDetector
from core.controller import MouseController


def main():
    camera = cv2.VideoCapture(0)
    detector = HandDetector()
    mouse = MouseController(smoothing=0.30)

    dragging = False
    was_scrolling = False
    last_click_gesture_time = 0.0

    # Briefly freeze cursor movement while a pinch is detected.
    click_freeze_seconds = 0.20

    if not camera.isOpened():
        print("Error: Could not open webcam.")
        detector.close()
        return

    print("=" * 45)
    print("CONTROL PC USING HAND GESTURE")
    print("=" * 45)
    print("Palm               : Move mouse")
    print("Thumb-index pinch  : Left-click")
    print("Thumb-middle pinch : Right-click")
    print("Closed fist        : Drag and drop")
    print("Ring + thumb pinch : Drag and drop")
    print("Index + middle up  : Scroll")
    print("Open hand          : Release drag")
    print("Q                  : Quit")
    print("=" * 45)

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("Error: Could not read webcam frame.")
                break

            frame = cv2.flip(frame, 1)
            frame, results = detector.detect(frame)

            status = "SHOW YOUR HAND"
            debug_text = ""

            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks[0].landmark
                fingers = mouse.finger_states(landmarks)

                debug_text = (
                    f"I:{int(fingers['INDEX'])} "
                    f"M:{int(fingers['MIDDLE'])} "
                    f"R:{int(fingers['RING'])} "
                    f"P:{int(fingers['PINKY'])}"
                )

                # Fist detection.
                is_fist = not any(fingers.values())

                # Ring fingertip + thumb drag detection.
                thumb = landmarks[4]
                ring = landmarks[16]
                ring_thumb_distance = math.hypot(
                    thumb.x - ring.x,
                    thumb.y - ring.y,
                )

                ring_threshold = 0.075 if dragging else 0.055
                is_ring_drag = ring_thumb_distance < ring_threshold
                is_drag_gesture = is_fist or is_ring_drag

                is_scroll = mouse.is_scroll_gesture(landmarks)

                # Drag gestures take priority over clicking and scrolling.
                if is_drag_gesture:
                    was_scrolling = False
                    mouse.reset_scroll()

                    mouse.move_from_palm(landmarks)

                    if not dragging:
                        pyautogui.mouseDown(button="left")
                        dragging = True

                    mouse.is_pinching = True
                    mouse.right_is_pinching = True

                    if is_fist:
                        status = "FIST DRAGGING - OPEN HAND TO DROP"
                    else:
                        status = "RING + THUMB DRAGGING"

                elif is_scroll:
                    if dragging:
                        pyautogui.mouseUp(button="left")
                        dragging = False

                    if not was_scrolling:
                        mouse.reset_scroll()
                        mouse.previous_x = None
                        mouse.previous_y = None
                        mouse.is_pinching = False
                        mouse.right_is_pinching = False

                    was_scrolling = True
                    amount = mouse.scroll_from_palm(landmarks)
                    status = f"SCROLL MODE | {amount}"

                else:
                    was_scrolling = False
                    mouse.reset_scroll()

                    just_released_drag = dragging

                    if dragging:
                        pyautogui.mouseUp(button="left")
                        dragging = False
                        mouse.is_pinching = False
                        mouse.right_is_pinching = False
                        last_click_gesture_time = time.monotonic()

                    # Keep the cursor steady briefly after a click or drag.
                    can_move = (
                        time.monotonic() - last_click_gesture_time
                        > click_freeze_seconds
                    )

                    if can_move and not just_released_drag:
                        mouse.move_from_palm(landmarks)

                    right_clicked = False
                    clicked = False

                    if (
                        not just_released_drag
                        and can_move
                    ):
                        right_clicked = mouse.handle_right_pinch(
                            landmarks
                        )

                        if not right_clicked:
                            clicked = mouse.handle_pinch(landmarks)

                        if clicked or right_clicked:
                            last_click_gesture_time = time.monotonic()

                    if right_clicked:
                        status = "RIGHT CLICK!"
                    elif clicked:
                        status = "LEFT CLICK!"
                    elif just_released_drag:
                        status = "DRAG RELEASED"
                    else:
                        status = "PALM MOUSE MODE"

                # Palm position marker.
                palm_ids = [0, 5, 9, 13, 17]
                height, width = frame.shape[:2]

                palm_x = int(
                    sum(landmarks[i].x for i in palm_ids)
                    / len(palm_ids) * width
                )
                palm_y = int(
                    sum(landmarks[i].y for i in palm_ids)
                    / len(palm_ids) * height
                )

                cv2.circle(
                    frame, (palm_x, palm_y), 8,
                    (0, 255, 255), -1
                )

                # Fingertip markers.
                for landmark_id, color in [
                    (4, (255, 0, 0)),
                    (8, (0, 255, 0)),
                    (12, (255, 255, 0)),
                    (16, (0, 165, 255)),
                ]:
                    point = landmarks[landmark_id]
                    cv2.circle(
                        frame,
                        (
                            int(point.x * width),
                            int(point.y * height),
                        ),
                        6,
                        color,
                        -1,
                    )

            else:
                if dragging:
                    pyautogui.mouseUp(button="left")
                    dragging = False

                mouse.reset()
                was_scrolling = False
                last_click_gesture_time = time.monotonic()
                status = "NO HAND DETECTED"

            # Status panel.
            cv2.rectangle(
                frame, (10, 10), (610, 125),
                (35, 35, 35), -1
            )

            cv2.putText(
                frame, status, (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60, (0, 255, 0), 2
            )

            cv2.putText(
                frame, debug_text, (20, 85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65, (0, 255, 255), 2
            )

            cv2.putText(
                frame, "Press Q to quit", (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45, (255, 255, 255), 1
            )

            cv2.imshow("Control PC Using Hand Gesture", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except pyautogui.FailSafeException:
        print("Mouse failsafe activated.")

    except KeyboardInterrupt:
        print("Application interrupted.")

    finally:
        if dragging:
            pyautogui.mouseUp(button="left")

        camera.release()
        detector.close()
        cv2.destroyAllWindows()
        print("Application stopped.")


if __name__ == "__main__":
    main()
