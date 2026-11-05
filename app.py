from flask import Flask, render_template, Response, jsonify, request
import cv2
import numpy as np
import time
import threading
from src.detection.detector import VehicleDetector

app = Flask(__name__)

# Global State
class TrafficSystem:
    def __init__(self):
        self.detectors = [VehicleDetector(use_bg_subtractor=True) for _ in range(4)]
        self.caps = []
        self.queues = [0, 0, 0, 0]
        self.current_green = 0
        self.phase_start_time = time.time()
        self.min_time = 5  # seconds (reduced for testing)
        self.max_time = 30 # seconds
        self.mode = "AUTO" # AUTO, MANUAL, STOP
        self.lock = threading.Lock()
        
        # Initialize Cameras
        for i in range(4):
            cap = cv2.VideoCapture(i)
            self.caps.append(cap)
            
    def get_frame(self):
        grid_w, grid_h = 320, 240
        frames = []
        
        with self.lock:
            for i, cap in enumerate(self.caps):
                if cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        frame = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
                        cv2.putText(frame, f"Cam {i} Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    else:
                        frame = cv2.resize(frame, (grid_w, grid_h))
                else:
                    frame = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
                    cv2.putText(frame, f"No Cam {i}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                # Detection
                count, _ = self.detectors[i].detect_from_frame(frame, min_contour_area=500)
                self.queues[i] = count
                
                # Overlay Info
                cv2.putText(frame, f"Lane {i}: {count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                
                # Traffic Light
                color = (0, 0, 255) # Red
                if i == self.current_green:
                    color = (0, 255, 0) # Green
                cv2.circle(frame, (grid_w - 30, 30), 15, color, -1)
                
                frames.append(frame)
            
            # Stitch
            top_row = np.hstack((frames[0], frames[2]))
            bottom_row = np.hstack((frames[3], frames[1]))
            composite = np.vstack((top_row, bottom_row))
            
            # Logic Update (Only if AUTO)
            if self.mode == "AUTO":
                self.update_logic()
                
            elapsed_time = int(time.time() - self.phase_start_time)
            
            # Global Overlay
            cv2.putText(composite, f"Mode: {self.mode}", (10, composite.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(composite, f"Timer: {elapsed_time}s", (10, composite.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            ret, jpeg = cv2.imencode('.jpg', composite)
            return jpeg.tobytes()

    def update_logic(self):
        elapsed_time = time.time() - self.phase_start_time
        
        current_q = self.queues[self.current_green]
        other_queues = [q for i, q in enumerate(self.queues) if i != self.current_green]
        max_other_q = max(other_queues) if other_queues else 0
        
        should_switch = False
        
        # Rule: Switch if time > min_time AND (no cars in current lane OR max_time exceeded)
        # Added safety: Make sure there IS traffic elsewhere before cutting short green light
        if elapsed_time > self.min_time:
            if current_q == 0 and max_other_q > 0:
                 should_switch = True
            elif elapsed_time > self.max_time:
                 should_switch = True
            
        if should_switch:
            best_lane = -1
            max_q = -1
            # Simple Greedy: find lane with MOST cars
            for i in range(1, 4):
                idx = (self.current_green + i) % 4
                if self.queues[idx] > max_q:
                    max_q = self.queues[idx]
                    best_lane = idx
            
            if best_lane != -1:
                self.current_green = best_lane
                self.phase_start_time = time.time()

    def set_mode(self, mode):
        with self.lock:
            self.mode = mode
            if mode == 'MANUAL': # Reset timer when switching to Manual just in case
                 self.phase_start_time = time.time()
            
    def force_switch(self, lane_id):
        with self.lock:
            self.current_green = lane_id
            self.phase_start_time = time.time()

system = TrafficSystem()

def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen(system),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stats')
def stats():
    elapsed_time = int(time.time() - system.phase_start_time)
    return jsonify({
        'queues': system.queues,
        'current_green': system.current_green,
        'timer': elapsed_time,
        'mode': system.mode
    })

@app.route('/api/control', methods=['POST'])
def control():
    data = request.json
    action = data.get('action')
    
    if action == 'set_mode':
        system.set_mode(data.get('mode'))
    elif action == 'switch_lane':
        system.force_switch(int(data.get('lane')))
        
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    # Disable reloader to prevent double initialization of cameras
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False, threaded=True)
