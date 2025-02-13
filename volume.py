import cv2
import mediapipe as mp
import math
import numpy as np
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import GUID

def main():
    # Initialize MediaPipe hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    mp_drawing = mp.solutions.drawing_utils

    # Get default audio device using PyCaw
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        GUID("{5CDF2C82-841E-4546-9722-0CF74078229A}"), CLSCTX_ALL, None
    )
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    # Get volume range (typically between -65.25 and 0.0 dB)
    vol_min, vol_max = volume.GetVolumeRange()[:2]

    # Start capturing video from the webcam
    cap = cv2.VideoCapture(0)

    # Smoothing factor for volume changes
    smooth_factor = 0.1
    prev_volume = volume.GetMasterVolumeLevel()

    while True:
        success, frame = cap.read()
        if not success:
            break

        # Flip frame horizontally for a "mirror" effect
        frame = cv2.flip(frame, 1)

        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        # Get frame dimensions
        h, w, _ = frame.shape

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
                )

                # Get landmark positions for thumb tip (id=4) and index finger tip (id=8)
                thumb_tip = hand_landmarks.landmark[4]
                index_tip = hand_landmarks.landmark[8]

                # Convert normalized landmark coordinates to actual pixel values
                thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
                index_x, index_y = int(index_tip.x * w), int(index_tip.y * h)

                # Draw circles for visualization
                cv2.circle(frame, (thumb_x, thumb_y), 10, (255, 0, 0), cv2.FILLED)
                cv2.circle(frame, (index_x, index_y), 10, (255, 0, 0), cv2.FILLED)
                cv2.line(frame, (thumb_x, thumb_y), (index_x, index_y), (0, 255, 0), 3)

                # Calculate the distance between thumb and index finger
                distance = math.hypot(index_x - thumb_x, index_y - thumb_y)

                # Define min and max distances for volume mapping
                min_dist = 30   # Minimum distance (volume 0%)
                max_dist = 200  # Maximum distance (volume 100%)

                # Clamp the distance to avoid out-of-range values
                distance = np.clip(distance, min_dist, max_dist)

                # Map distance to volume range
                target_volume = np.interp(distance, [min_dist, max_dist], [vol_min, vol_max])

                # Smooth volume changes to avoid abrupt jumps
                smooth_volume = (1 - smooth_factor) * prev_volume + smooth_factor * target_volume
                volume.SetMasterVolumeLevel(smooth_volume, None)
                prev_volume = smooth_volume

                # Convert distance to percentage for UI
                vol_percent = np.interp(distance, [min_dist, max_dist], [0, 100])

                # Draw volume level text
                cv2.putText(
                    frame, f"Volume: {int(vol_percent)}%", (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
                )

                # Draw a volume level bar on the screen
                bar_x, bar_y = 50, 100
                bar_width, bar_height = 40, 300
                fill_height = int(bar_height * (vol_percent / 100))
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (255, 255, 255), 2)
                cv2.rectangle(frame, (bar_x, bar_y + bar_height - fill_height), (bar_x + bar_width, bar_y + bar_height), (0, 255, 0), -1)

        # Show the processed frame
        cv2.imshow("Hand Volume Control", frame)

        # Exit if the ESC key is pressed
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
