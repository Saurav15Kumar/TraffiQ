import pygame
import math
import random

class TrafficLight:
    def __init__(self, x, y, lane_id):
        self.x = x
        self.y = y
        self.lane_id = lane_id
        self.state = "RED"  # RED, GREEN, YELLOW
        self.timer = 0
        self.green_duration = 10
        self.yellow_duration = 3
        
    def set_state(self, state):
        self.state = state
        self.timer = 0
        
    def update(self, dt):
        self.timer += dt
        
    def draw(self, screen):
        # Draw housing
        pygame.draw.rect(screen, (20, 20, 20), (self.x - 15, self.y - 15, 30, 30), 0, 5)
        pygame.draw.rect(screen, (100, 100, 100), (self.x - 15, self.y - 15, 30, 30), 2, 5)

        color = (50, 0, 0) # Dim red
        if self.state == "RED":
            color = (255, 0, 0)
        elif self.state == "GREEN":
            color = (0, 255, 0)
        elif self.state == "YELLOW":
            color = (255, 255, 0)
            
        # Draw light
        pygame.draw.circle(screen, color, (self.x, self.y), 10)
        
        # Glow effect (only if active)
        if self.state in ["GREEN", "YELLOW", "RED"]:
            s = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, 50), (30, 30), 15)
            pygame.draw.circle(s, (*color, 20), (30, 30), 25)
            screen.blit(s, (self.x - 30, self.y - 30))

class Vehicle:
    def __init__(self, lane_id, start_pos, speed=2):
        self.x, self.y = start_pos
        self.lane_id = lane_id
        self.speed = speed
        self.max_speed = speed
        self.stopped = False
        self.waiting_time = 0
        self.direction = self._get_direction(lane_id)
        
        if self.direction[0] != 0: # Horizontal
            self.width = 80
            self.height = 40
        else: # Vertical
            self.width = 40
            self.height = 80

    def _get_direction(self, lane_id):
        # 0: North->South, 1: South->North, 2: East->West, 3: West->East
        if lane_id == 0: return (0, 1)
        if lane_id == 1: return (0, -1)
        if lane_id == 2: return (-1, 0)
        if lane_id == 3: return (1, 0)
        return (0, 0)

    def update(self, traffic_lights, vehicles_ahead):
        # 1. Check for vehicles ahead (Simple collision avoidance)
        safe_distance = 100 # Increased for larger cars (length 80)
        self.stopped = False
        
        for v in vehicles_ahead:
            if v.lane_id == self.lane_id:
                dist = math.sqrt((self.x - v.x)**2 + (self.y - v.y)**2)
                # Check if v is ahead of self
                is_ahead = False
                if self.lane_id == 0 and v.y > self.y: is_ahead = True
                elif self.lane_id == 1 and v.y < self.y: is_ahead = True
                elif self.lane_id == 2 and v.x < self.x: is_ahead = True
                elif self.lane_id == 3 and v.x > self.x: is_ahead = True
                
                if is_ahead and dist < safe_distance:
                    self.stopped = True
                    break
        
        # 2. Check Traffic Lights
        if not self.stopped:
            light = traffic_lights[self.lane_id]
            
            # Intersection boundaries (Stop lines)
            # Assuming screen center is passed in or accessible, but we can infer from light positions or pass it.
            # Actually, we don't have center_x/y here easily without passing it.
            # But we know light positions are at corners: center +/- 60.
            # So intersection edge is roughly light position +/- 10 (since road is 100 wide, center +/- 50).
            
            # Let's use the light position as a reference for the stop line.
            # Lane 0 (N->S): Light at (cx-60, cy-60). Stop line at cy-50. Light.y + 10.
            # Lane 1 (S->N): Light at (cx+60, cy+60). Stop line at cy+50. Light.y - 10.
            # Lane 2 (E->W): Light at (cx+60, cy-60). Stop line at cx+50. Light.x - 10.
            # Lane 3 (W->E): Light at (cx-60, cy+60). Stop line at cx-50. Light.x + 10.
            
            stop_threshold = 10 # Distance before stop line to start stopping
            should_stop = False
            
            if self.lane_id == 0: # N->S (Moving Down)
                stop_line = light.y + 10
                front_bumper = self.y + self.height
                dist = stop_line - front_bumper
                if 0 < dist < stop_threshold + 40: should_stop = True # +40 for smooth stop
                if front_bumper > stop_line: should_stop = False # Passed
                
            elif self.lane_id == 1: # S->N (Moving Up)
                stop_line = light.y - 10
                front_bumper = self.y
                dist = front_bumper - stop_line
                if 0 < dist < stop_threshold + 40: should_stop = True
                if front_bumper < stop_line: should_stop = False # Passed
                
            elif self.lane_id == 2: # E->W (Moving Left)
                stop_line = light.x - 10
                front_bumper = self.x
                dist = front_bumper - stop_line
                if 0 < dist < stop_threshold + 40: should_stop = True
                if front_bumper < stop_line: should_stop = False # Passed
                
            elif self.lane_id == 3: # W->E (Moving Right)
                stop_line = light.x + 10
                front_bumper = self.x + self.width
                dist = stop_line - front_bumper
                if 0 < dist < stop_threshold + 40: should_stop = True
                if front_bumper > stop_line: should_stop = False # Passed
                
            if should_stop and light.state in ["RED", "YELLOW"]:
                self.stopped = True

        if self.stopped:
            self.waiting_time += 1
        else:
            self.waiting_time = 0
            self.x += self.direction[0] * self.speed
            self.y += self.direction[1] * self.speed
        
    def draw(self, screen, car_img=None):
        if car_img:
            # Rotate image based on direction
            angle = 0
            if self.direction == (0, 1): angle = 180 # Down
            elif self.direction == (0, -1): angle = 0 # Up
            elif self.direction == (-1, 0): angle = 90 # Left
            elif self.direction == (1, 0): angle = -90 # Right
            
            rotated_img = pygame.transform.rotate(car_img, angle)
            rect = rotated_img.get_rect(center=(self.x + self.width//2, self.y + self.height//2))
            screen.blit(rotated_img, rect.topleft)
        else:
            # Fallback
            if self.direction[0] != 0: # Horizontal
                pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
            else: # Vertical
                pygame.draw.rect(screen, self.color, (self.x, self.y, self.height, self.width))
