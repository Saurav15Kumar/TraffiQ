import cv2
import numpy as np
import time
from src.detection.detector import VehicleDetector

def run_live():
    # Initialize detector with background subtraction
    # We might need 4 detectors if they maintain state (BackgroundSubtractor)
    # Yes, MOG2 maintains a background model, so we need 4 separate instances.
    detectors = [VehicleDetector(use_bg_subtractor=True) for _ in range(4)]
    
    # Open webcams
    # We attempt to open indices 0, 1, 2, 3
    caps = []
    for i in range(4):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Camera {i} opened successfully.")
        else:
            print(f"Warning: Camera {i} could not be opened. Using placeholder.")
        caps.append(cap)

    print("Press 'q' to quit.")
    
    # Traffic Light State
    # 0: Top-Left (N), 1: Bottom-Right (S), 2: Top-Right (E), 3: Bottom-Left (W)
    current_green = 0
    timer = 0
    min_time = 60 # frames
    max_time = 1800 # 30 seconds (frames)
    
    # Display settings
    grid_w, grid_h = 320, 240
    
    while True:
        frames = []
        queues = [0, 0, 0, 0]
        
        for i, cap in enumerate(caps):
            if cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    # Failed to read, use black frame
                    frame = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
                    cv2.putText(frame, f"Cam {i} Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    frame = cv2.resize(frame, (grid_w, grid_h))
            else:
                # Camera not open, use black frame
                frame = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
                cv2.putText(frame, f"No Cam {i}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Process frame
            # We pass the frame to the specific detector for this lane
            count, detections = detectors[i].detect_from_frame(frame, min_contour_area=500)
            queues[i] = count
            
            # Draw info on individual frame
            cv2.putText(frame, f"Lane {i}: {count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
            # Draw Traffic Light Status
            color = (0, 0, 255) # Red
            if i == current_green:
                color = (0, 255, 0) # Green
            cv2.circle(frame, (grid_w - 30, 30), 15, color, -1)
            
            frames.append(frame)
            
        # Stitch frames into a 2x2 grid
        # Top Row: Lane 0, Lane 2 (North, East) - Adjusted to match typical layout or just 0,1,2,3
        # Let's stick to the index order:
        # Row 1: Cam 0, Cam 2 (Top-Left, Top-Right)
        # Row 2: Cam 3, Cam 1 (Bottom-Left, Bottom-Right) -> This matches the visual quadrant layout better
        # 0: Top-Left, 1: Bottom-Right, 2: Top-Right, 3: Bottom-Left
        
        top_row = np.hstack((frames[0], frames[2]))
        bottom_row = np.hstack((frames[3], frames[1]))
        composite = np.vstack((top_row, bottom_row))
        
        # Adaptive Logic
        timer += 1
        current_q = queues[current_green]
        other_queues = [q for i, q in enumerate(queues) if i != current_green]
        max_other_q = max(other_queues) if other_queues else 0
        
        # Draw Global Info
        cv2.putText(composite, f"Timer: {timer}/{max_time}", (10, composite.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        should_switch = False
        if timer > min_time and current_q == 0 and max_other_q > 0:
            should_switch = True
            cv2.putText(composite, "Switch: Empty Lane", (composite.shape[1]//2 - 100, composite.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        elif timer > max_time:
            should_switch = True
            cv2.putText(composite, "Switch: Max Time", (composite.shape[1]//2 - 100, composite.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
        if should_switch:
             # Pick next lane
            best_lane = -1
            max_q = -1
            for i in range(1, 4):
                idx = (current_green + i) % 4
                if queues[idx] > max_q:
                    max_q = queues[idx]
                    best_lane = idx
            
            if best_lane != -1:
                current_green = best_lane
                timer = 0
        
        cv2.imshow("Multi-Camera Traffic Control", composite)
        
        if cv2.waitKey(1) == ord('q'):
            break
            
    for cap in caps:
        if cap.isOpened():
            cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_live()
