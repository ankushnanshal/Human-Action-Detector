import cv2
import threading
import time
import numpy as np
from collections import deque
from flask import Flask, render_template, Response, jsonify
from flask_cors import CORS
import mediapipe as mp

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
CORS(app)


class VideoCamera:
    def __init__(self):
        self.cap = None
        self.running = False
        self.status = "Camera Off"
        self.lock = threading.Lock()
        self._frame_bytes = None
        self.thread = None

        # ✅ MediaPipe Pose (STABLE VERSION)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_style = mp.solutions.drawing_styles

        self.hip_history = deque(maxlen=10)
        self.status_history = deque(maxlen=7)

    def start(self):
        if self.running:
            return

        self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(1)

        if not self.cap.isOpened():
            self.status = "Camera Error"
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.running = True
        self.status = "Detecting..."

        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

        if self.cap:
            self.cap.release()
            self.cap = None

        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None

        self.status = "Camera Off"

        with self.lock:
            self._frame_bytes = None

        self.hip_history.clear()
        self.status_history.clear()

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

            ret2, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

            if ret2:
                with self.lock:
                    self._frame_bytes = buf.tobytes()

            time.sleep(0.02)

    def _process(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        if results.pose_landmarks:
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
                self.status = max(set(self.status_history), key=self.status_history.count)
        else:
            self.status_history.clear()
            self.status = "No Person Detected"

        return frame

    def _angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)

        rad = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        ang = np.abs(rad * 180.0 / np.pi)

        return 360 - ang if ang > 180 else ang

    def _detect_action(self, lm, h, w):
        try:
            def pt(idx):
                return [lm[idx].x * w, lm[idx].y * h]

            l_knee = self._angle(pt(23), pt(25), pt(27))
            r_knee = self._angle(pt(24), pt(26), pt(28))

            avg_knee = (l_knee + r_knee) / 2

            hip_y = (lm[23].y + lm[24].y) / 2 * h
            self.hip_history.append(hip_y)

            movement = (
                max(self.hip_history) - min(self.hip_history)
                if len(self.hip_history) > 2 else 0
            )

            if movement > 25:
                return "Walking"
            elif avg_knee < 135:
                return "Sitting"
            else:
                return "Standing"

        except:
            return "Detecting..."

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

            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + fb + b"\r\n")


# ✅ Initialize Camera
ai_camera = VideoCamera()


# ✅ ROUTES

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start")
def start():
    ai_camera.start()
    return jsonify({"status": ai_camera.status})


@app.route("/stop")
def stop():
    ai_camera.stop()
    return jsonify({"status": ai_camera.status})


@app.route("/status")
def status():
    return jsonify({"status": ai_camera.status})


@app.route("/video_feed")
def video_feed():
    return Response(
        ai_camera.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    print("Server running at: http://127.0.0.1:5000")
    app.run(debug=False, port=5000, threaded=True)