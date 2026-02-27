import cv2
import mediapipe as mp
import numpy as np
import math
import time
import pyautogui
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7, max_num_hands=2)
mp_draw = mp.solutions.drawing_utils
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
cap = cv2.VideoCapture(0)
prev_angle = None
left_hold_start = None
right_hold_start = None
both_hands_start = None
is_paused = False
hold_duration = 1
is_muted = False
mute_toggle_cooldown = 0
finger_tips = {
    'thumb': 4,
    'index': 8,
    'middle': 12,
    'ring': 16,
    'pinky': 20
}
while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)
    h, w, _ = frame.shape
    num_hands = 0
    hand_types = []
    if result.multi_hand_landmarks:
        num_hands = len(result.multi_hand_landmarks)

        for idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            if result.multi_handedness:
                hand_type = result.multi_handedness[idx].classification[0].label
                hand_types.append(hand_type)
        if num_hands == 2:
            if both_hands_start is None:
                both_hands_start = time.time()
            elif time.time() - both_hands_start >= hold_duration:
                if not is_paused:
                    print("⏸️ Music Paused")
                    pyautogui.press('playpause')
                    is_paused = True
                else:
                    print("▶️ Music Played")
                    pyautogui.press('playpause')
                    is_paused = False
                both_hands_start = None
        else:
            both_hands_start = None
        if num_hands == 2:
            cv2.putText(frame, "Pause/Play (Both Hands)", (50, 100), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 0, 255), 2)
            cv2.imshow("Gesture Music Controller", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue
        for hand_landmarks in result.multi_hand_landmarks:
            landmarks = hand_landmarks.landmark
            wrist_x = int(landmarks[0].x * w)
            wrist_y = int(landmarks[0].y * h)
            cv2.circle(frame, (wrist_x, wrist_y), 10, (0, 0, 255), -1)
            if wrist_x < 50:
                if left_hold_start is None:
                    left_hold_start = time.time()
                elif time.time() - left_hold_start >= 1:
                    print("⏮️ Previous Track")
                    pyautogui.press('prevtrack')
                    left_hold_start = None
            else:
                left_hold_start = None

            if wrist_x > w - 50:
                if right_hold_start is None:
                    right_hold_start = time.time()
                elif time.time() - right_hold_start >= 1:
                    print("⏭️ Next Track")
                    pyautogui.press('nexttrack')
                    right_hold_start = None
            else:
                right_hold_start = None
            tip_points = {finger: (int(landmarks[finger_tips[finger]].x * w), 
                                  int(landmarks[finger_tips[finger]].y * h)) 
                          for finger in finger_tips}
            center_x = sum([p[0] for p in tip_points.values()]) // 5
            center_y = sum([p[1] for p in tip_points.values()]) // 5
            dx = tip_points['middle'][0] - center_x
            dy = tip_points['middle'][1] - center_y
            angle = math.degrees(math.atan2(dy, dx))
            current_volume = np.interp(volume.GetMasterVolumeLevel(), [-65, 0], [0, 100])
            if prev_angle is not None:
                angle_diff = angle - prev_angle
                if angle_diff > 5 and current_volume < 100:
                    new_volume = min(current_volume + 5, 100)
                    volume.SetMasterVolumeLevel(np.interp(new_volume, [0, 100], [-65, 0]), None)
                elif angle_diff < -5 and current_volume > 0:
                    new_volume = max(current_volume - 5, 0)
                    volume.SetMasterVolumeLevel(np.interp(new_volume, [0, 100], [-65, 0]), None)
            prev_angle = angle
            finger_up = []
            for finger in ['index', 'middle', 'ring', 'pinky']:
                if landmarks[finger_tips[finger]].y < landmarks[finger_tips[finger] - 2].y:
                    finger_up.append(True)
                else:
                    finger_up.append(False)
            index_up = landmarks[finger_tips['index']].y < landmarks[finger_tips['index'] - 2].y
            other_down = all(landmarks[finger_tips[finger]].y > landmarks[finger_tips[finger] - 2].y for finger in ['middle', 'ring', 'pinky'])
            if index_up and other_down:
                if time.time() - mute_toggle_cooldown > 1.5:
                    if not is_muted:
                        volume.SetMasterVolumeLevel(np.interp(0, [0, 100], [-65, 0]), None)
                        print("🔇 Muted")
                        is_muted = True
                    else:
                        volume.SetMasterVolumeLevel(np.interp(70, [0, 100], [-65, 0]), None)
                        print("🔊 Unmuted")
                        is_muted = False
                    mute_toggle_cooldown = time.time()
            cv2.putText(frame, f'Volume: {int(current_volume)}%',
                        (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    else:
        both_hands_start = None
    cv2.imshow("Gesture Music Controller", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
