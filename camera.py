import cv2
import mediapipe as mp
import numpy as np
from collections import deque

class VideoCamera:
    def __init__(self):
        self.cap = None
        self.running = False
        self.status = "Camera Off"
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        self.mp_draw = mp.solutions.drawing_utils
        self.hip_history = deque(maxlen=10)
        self.status_history = deque(maxlen=5)

    def start(self):
        if not self.running:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.status = "Camera Error"
                return
            self.running = True
            self.status = "Detecting..."

    def stop(self):
        self.running = False
        self.status = "Camera Off"
        if self.cap:
            self.cap.release()
            self.cap = None

    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        return 360 - angle if angle > 180 else angle

    def detect_action(self, landmarks, h, w):
        try:
            l_knee = self.calculate_angle(
                [landmarks[23].x * w, landmarks[23].y * h],
                [landmarks[25].x * w, landmarks[25].y * h],
                [landmarks[27].x * w, landmarks[27].y * h]
            )
            r_knee = self.calculate_angle(
                [landmarks[24].x * w, landmarks[24].y * h],
                [landmarks[26].x * w, landmarks[26].y * h],
                [landmarks[28].x * w, landmarks[28].y * h]
            )

            avg_knee = (l_knee + r_knee) / 2
            hip_y = (landmarks[23].y + landmarks[24].y) / 2 * h
            self.hip_history.append(hip_y)

            movement = max(self.hip_history) - min(self.hip_history) if len(self.hip_history) > 2 else 0

            if movement > 20:
                action = "Walking"
            elif avg_knee < 140:
                action = "Sitting"
            else:
                action = "Standing"

            self.status_history.append(action)
            return max(set(self.status_history), key=self.status_history.count)
        except:
            return "Detecting..."

    def get_frame(self):
        if not self.running or self.cap is None:
            return None
        success, frame = self.cap.read()
        if not success:
            return None

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        if results.pose_landmarks:
            self.mp_draw.draw_landmarks(frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
            self.status = self.detect_action(results.pose_landmarks.landmark, frame.shape[0], frame.shape[1])
        else:
            self.status = "No Person Detected"

        cv2.putText(frame, self.status, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()

    def generate_frames(self):
        while True:
            if self.running:
                frame = self.get_frame()
                if frame:
                    yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')