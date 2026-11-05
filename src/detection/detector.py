import cv2
import numpy as np
import pygame

class VehicleDetector:
    def __init__(self, use_bg_subtractor=False):
        self.use_bg_subtractor = use_bg_subtractor
        if self.use_bg_subtractor:
            self.fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=True)
        
    def process_frame(self, surface):
        # Convert Pygame surface to OpenCV image (numpy array)
        view = pygame.surfarray.array3d(surface)
        view = view.transpose([1, 0, 2]) # Pygame is (w, h, c), Numpy/CV2 is (h, w, c)
        img_bgr = cv2.cvtColor(view, cv2.COLOR_RGB2BGR)
        
        return self.detect_from_frame(img_bgr)

    def detect_from_frame(self, frame, min_contour_area=500, max_contour_area=40000):
        if self.use_bg_subtractor:
            # Background subtraction method (better for real camera)
            fgmask = self.fgbg.apply(frame)
            _, mask = cv2.threshold(fgmask, 250, 255, cv2.THRESH_BINARY)
            # Remove noise
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        else:
            # Color based detection (for simulation)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower_val = np.array([0, 50, 50]) 
            upper_val = np.array([179, 255, 255])
            mask = cv2.inRange(hsv, lower_val, upper_val)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        vehicle_count = 0
        detections = [] # List of (x, y, w, h)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_contour_area: # Filter small noise
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                
                # Filter: Max Area and Aspect Ratio (Cars are roughly rectangular, not long lines or whole screen)
                # Max Area: 40000 (approx 200x200 or half screen in one dim)
                # Aspect Ratio: 0.5 (exclude humans <0.5) to 5.0 (wide truck/side view)
                if area < max_contour_area and 0.5 < aspect_ratio < 5.0:
                     # Valid Vehicle: Green
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    vehicle_count += 1
                    detections.append((x, y, w, h))
                
        # Display the OpenCV window
        cv2.imshow("Vehicle Detection", frame)
        cv2.waitKey(1)
        
        return vehicle_count, detections
