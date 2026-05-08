import cv2
import threading
import time
import numpy as np
from collections import deque
from flask import Flask, render_template, Response, jsonify
from flask_cors import CORS
<<<<<<< HEAD
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
=======

# --- FLASK SETUP ---
app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
CORS(app)

# --- YOUR AI CAMERA CLASS ---
class VideoCamera:
    def __init__(self, src=0):
        self.src = src
        self.cap = None
        self.frame = None
        self.prev_gray = None
        self.lock = threading.Lock()
        self.running = False
        self.status = "stopped"
        self.thread = None
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.net = None
        self.output_layers = []
        self.classes = []
        self._load_yolo()
        self.motion_history = deque(maxlen=5)
        self.motion_threshold = 1500

    def _load_yolo(self):
        try:
            self.net = cv2.dnn.readNet("yolov4-tiny.weights", "yolov4-tiny.cfg")
            with open("coco.names", "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
            layer_names = self.net.getLayerNames()
            self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers().flatten()]
            print("[Camera] YOLO loaded successfully.")
        except Exception as e:
            print(f"[Camera] YOLO not loaded: {e}")
            self.net = None

    def start(self):
        if self.running: return
        self.cap = cv2.VideoCapture(self.src)
        if not self.cap.isOpened():
            self.status = "error: cannot open camera"
            return
        self.running = True
        self.status = "running"
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print("[Camera] Started.")

    def stop(self):
        self.running = False
        self.status = "stopped"
        if self.cap: self.cap.release()
        print("[Camera] Stopped.")

    def _capture_loop(self):
        while self.running:
            ret, raw = self.cap.read()
            if not ret: continue
            processed = self._process_frame(raw)
            with self.lock: self.frame = processed

    def _process_frame(self, frame):
        frame = self._detect_motion(frame)
        frame = self._detect_faces(frame)
        if self.net: frame = self._detect_objects(frame)
        return frame

    def _detect_motion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if self.prev_gray is None:
            self.prev_gray = gray
            return frame
        diff = cv2.absdiff(self.prev_gray, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        motion_score = int(np.sum(thresh) / 255)
        self.motion_history.append(motion_score)
        avg_motion = sum(self.motion_history) / len(self.motion_history)
        self.prev_gray = gray
        if avg_motion > self.motion_threshold:
            cv2.putText(frame, "MOTION DETECTED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        return frame

    def _detect_faces(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        return frame

    def _detect_objects(self, frame):
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward(self.output_layers)
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                cid = np.argmax(scores)
                if scores[cid] > 0.45:
                    cx, cy, bw, bh = (detection[:4] * np.array([w, h, w, h])).astype(int)
                    cv2.rectangle(frame, (cx-bw//2, cy-bh//2), (cx+bw//2, cy+bh//2), (0, 255, 0), 2)
        return frame
>>>>>>> 8cc50a40e23d187c9bc3ae684cc5be9cbdbbbba7

    def generate_frames(self):
        while True:
            if not self.running:
                time.sleep(0.1)
                continue
<<<<<<< HEAD

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

=======
            with self.lock:
                if self.frame is None: continue
                ret, buffer = cv2.imencode(".jpg", self.frame)
                frame_bytes = buffer.tobytes()
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
            time.sleep(0.03)

# --- FLASK ROUTES ---
ai_camera = VideoCamera()

>>>>>>> 8cc50a40e23d187c9bc3ae684cc5be9cbdbbbba7
@app.route("/")
def index():
    return render_template("index.html")

<<<<<<< HEAD

@app.route("/start")
def start():
    ai_camera.start()
    return jsonify({"status": ai_camera.status})

=======
@app.route("/start")
def start():
    ai_camera.start()
    return jsonify({"status": "started"})
>>>>>>> 8cc50a40e23d187c9bc3ae684cc5be9cbdbbbba7

@app.route("/stop")
def stop():
    ai_camera.stop()
<<<<<<< HEAD
    return jsonify({"status": ai_camera.status})

=======
    return jsonify({"status": "stopped"})
>>>>>>> 8cc50a40e23d187c9bc3ae684cc5be9cbdbbbba7

@app.route("/status")
def status():
    return jsonify({"status": ai_camera.status})

<<<<<<< HEAD

@app.route("/video_feed")
def video_feed():
    return Response(
        ai_camera.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    print("Server running at: http://127.0.0.1:5000")
    app.run(debug=False, port=5000, threaded=True)
=======
@app.route("/video_feed")
def video_feed():
    return Response(ai_camera.generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    print("Server starting at http://127.0.0.1:5000")
    app.run(debug=True, port=5000, threaded=True)
>>>>>>> 8cc50a40e23d187c9bc3ae684cc5be9cbdbbbba7
