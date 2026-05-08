import cv2
import threading
import time
import numpy as np
from collections import deque
import mediapipe as mp


class VideoCamera:
    def __init__(self):
        self.cap = None
        self.running = False
        self.status = "Camera Off"
        self.lock = threading.Lock()
        self._frame_bytes = None
        self.thread = None

        # MediaPipe Pose
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_style = mp.solutions.drawing_styles

        # Buffers for smoothing
        self.hip_history = deque(maxlen=10)
        self.status_history = deque(maxlen=7)

    # =========================
    # START CAMERA
    # =========================
    def start(self):
        if self.running:
            return

        self.cap = cv2.VideoCapture(0)

        # fallback camera
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(1)

        if not self.cap.isOpened():
            self.status = "Camera Error"
            return

        # Optimize resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.running = True
        self.status = "Detecting..."

        self.thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )
        self.thread.start()

    # =========================
    # STOP CAMERA
    # =========================
    def stop(self):
        self.running = False

        if self.cap:
            self.cap.release()
            self.cap = None

        self.thread = None

        self.status = "Camera Off"

        with self.lock:
            self._frame_bytes = None

        self.hip_history.clear()
        self.status_history.clear()

    # =========================
    # CAMERA LOOP
    # =========================
    def _capture_loop(self):
        while self.running:
            if not self.cap or not self.cap.isOpened():
                self.status = "Camera Error"
                break

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.03)
                continue

            frame = cv2.flip(frame, 1)
            frame = self._process(frame)

            ret2, buf = cv2.imencode(
                '.jpg', frame,
                [cv2.IMWRITE_JPEG_QUALITY, 85]
            )

            if ret2:
                with self.lock:
                    self._frame_bytes = buf.tobytes()

            time.sleep(0.03)  # ~30 FPS

    # =========================
    # PROCESS FRAME
    # =========================
    def _process(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        if results.pose_landmarks:
            # Draw skeleton
            self.mp_draw.draw_landmarks(
                frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                self.mp_style.get_default_pose_landmarks_style()
            )

            action = self._detect_action(
                results.pose_landmarks.landmark,
                frame.shape[0],
                frame.shape[1]
            )

            if action != "Detecting...":
                self.status_history.append(action)

            if len(self.status_history) > 0:
                self.status = max(
                    set(self.status_history),
                    key=self.status_history.count
                )
        else:
            # FIXED BUG HERE
            self.status = "No Person Detected"
            self.status_history.clear()
            self.hip_history.clear()

        # Display status
        cv2.putText(
            frame,
            f"Status: {self.status}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        return frame

    # =========================
    # ANGLE CALCULATION
    # =========================
    def _angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        rad = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        ang = np.abs(rad * 180.0 / np.pi)
        return 360 - ang if ang > 180 else ang

    # =========================
    # ACTION DETECTION
    # =========================
    def _detect_action(self, lm, h, w):
        try:
            def pt(idx):
                return [lm[idx].x * w, lm[idx].y * h]

            # Knee angles
            l_knee = self._angle(pt(23), pt(25), pt(27))
            r_knee = self._angle(pt(24), pt(26), pt(28))
            avg_knee = (l_knee + r_knee) / 2

            # Hip movement
            hip_y = (lm[23].y + lm[24].y) / 2 * h
            self.hip_history.append(hip_y)

            movement = (
                max(self.hip_history) - min(self.hip_history)
                if len(self.hip_history) > 2 else 0
            )

            # Decision logic
            if movement > 40:
                return "Walking"
            elif avg_knee < 135:
                return "Sitting"
            else:
                return "Standing"

        except Exception as e:
            print("Detection Error:", e)
            return "Detecting..."

    # =========================
    # FRAME GENERATOR (FLASK)
    # =========================
    def generate_frames(self):
        while True:
            if not self.running:
                time.sleep(0.1)
                continue

            with self.lock:
                fb = self._frame_bytes

            if fb is None:
                time.sleep(0.03)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                fb +
                b"\r\n"
            )