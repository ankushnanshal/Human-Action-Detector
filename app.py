import cv2
import threading
import time
import numpy as np
from collections import deque
from flask import Flask, render_template, Response, jsonify
from flask_cors import CORS

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

    def generate_frames(self):
        while True:
            if not self.running:
                time.sleep(0.1)
                continue
            with self.lock:
                if self.frame is None: continue
                ret, buffer = cv2.imencode(".jpg", self.frame)
                frame_bytes = buffer.tobytes()
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
            time.sleep(0.03)

# --- FLASK ROUTES ---
ai_camera = VideoCamera()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start")
def start():
    ai_camera.start()
    return jsonify({"status": "started"})

@app.route("/stop")
def stop():
    ai_camera.stop()
    return jsonify({"status": "stopped"})

@app.route("/status")
def status():
    return jsonify({"status": ai_camera.status})

@app.route("/video_feed")
def video_feed():
    return Response(ai_camera.generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    print("Server starting at http://127.0.0.1:5000")
    app.run(debug=True, port=5000, threaded=True)