import pygame
from .entities import TrafficLight, Vehicle
from src.detection.detector import VehicleDetector
import random

class TrafficSim:
    def __init__(self, width=800, height=600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Adaptive Traffic Light Control")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Intersection coordinates (approximate center)
        self.center_x = width // 2
        self.center_y = height // 2
        
        # Initialize Traffic Lights
        # 0: Top (North), 1: Bottom (South), 2: Right (East), 3: Left (West)
        # Moved to corners of the intersection (offset 60 from center)
        self.lights = [
            TrafficLight(self.center_x - 60, self.center_y - 60, 0), # Top-Left (for N->S)
            TrafficLight(self.center_x + 60, self.center_y + 60, 1), # Bottom-Right (for S->N)
            TrafficLight(self.center_x + 60, self.center_y - 60, 2), # Top-Right (for E->W)
            TrafficLight(self.center_x - 60, self.center_y + 60, 3)  # Bottom-Left (for W->E)
        ]
        
        self.vehicles = []
        self.spawn_timer = 0
        self.green_timer = 0 # Track how long the current light has been green
        self.detector = VehicleDetector()
        
        # Load background
        try:
            self.background = pygame.image.load("assets/background.png")
            self.background = pygame.transform.scale(self.background, (width, height))
        except Exception as e:
            print(f"Could not load background: {e}")
            self.background = None
            
        # Load car sprite
        try:
            self.car_img = pygame.image.load("assets/car.png")
            self.car_img = pygame.transform.scale(self.car_img, (40, 80)) # Scaled to fill lane (40px width)
        except Exception as e:
            print(f"Could not load car sprite: {e}")
            self.car_img = None
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
    def spawn_vehicle(self):
        # Try to spawn in a random lane
        # To ensure traffic from all directions, we can try multiple times
        lanes_to_try = [0, 1, 2, 3]
        random.shuffle(lanes_to_try)
        
        for lane in lanes_to_try:
            if self._is_safe_to_spawn(lane):
                if lane == 0: # N->S
                    start_pos = (self.center_x - 45, -80)
                elif lane == 1: # S->N
                    start_pos = (self.center_x + 5, self.height)
                elif lane == 2: # E->W
                    start_pos = (self.width, self.center_y - 45)
                elif lane == 3: # W->E
                    start_pos = (-80, self.center_y + 5)
                    
                self.vehicles.append(Vehicle(lane, start_pos))
                break # Spawn one per tick (or remove break to spawn multiple)

    def _is_safe_to_spawn(self, lane):
        # Check if any vehicle is too close to the spawn point of this lane
        safe_dist = 100
        spawn_x, spawn_y = 0, 0
        
        if lane == 0: spawn_x, spawn_y = (self.center_x - 45, -80)
        elif lane == 1: spawn_x, spawn_y = (self.center_x + 5, self.height)
        elif lane == 2: spawn_x, spawn_y = (self.width, self.center_y - 45)
        elif lane == 3: spawn_x, spawn_y = (-80, self.center_y + 5)
        
        for v in self.vehicles:
            if v.lane_id == lane:
                dist = ((v.x - spawn_x)**2 + (v.y - spawn_y)**2)**0.5
                if dist < safe_dist:
                    return False
        return True

    def reset(self):
        self.vehicles = []
        self.spawn_timer = 0
        self.green_timer = 0
        for light in self.lights:
            light.set_state("RED")
        # Set one random light to GREEN to start
        self.lights[random.randint(0, 3)].set_state("GREEN")
        return self.get_state()

    def get_state(self):
        # State: Number of vehicles in each lane (queue length)
        # 4 lanes
        queues = [0, 0, 0, 0]
        for v in self.vehicles:
            queues[v.lane_id] += 1
        return tuple(queues)

    def step(self, action):
        # Action: 0=Keep, 1=Next Phase (Green for next lane)
        # Simplified: Action is the index of the light to turn GREEN (0-3)
        
        # Check if we need to switch
        current_green = -1
        for i, light in enumerate(self.lights):
            if light.state == "GREEN":
                current_green = i
                break
        
        if current_green != -1 and current_green != action:
            # Transition needed
            self.green_timer = 0 # Reset timer on switch
            
            # 1. Turn current green to YELLOW
            self.lights[current_green].set_state("YELLOW")
            
            # Simulate Yellow phase (1 second = 60 frames)
            for _ in range(60):
                self.handle_events()
                if not self.running: return self.get_state(), 0, True, {}
                self.update()
                self.draw()
                self.clock.tick(60)
                
            # 2. Turn Yellow to RED (All-Red Clearance)
            self.lights[current_green].set_state("RED")
            
            # Simulate All-Red phase (1 second = 60 frames)
            for _ in range(60):
                self.handle_events()
                if not self.running: return self.get_state(), 0, True, {}
                self.update()
                self.draw()
                self.clock.tick(60)
            
            # 3. Turn new light to GREEN
            self.lights[action].set_state("GREEN")
            
        elif current_green == -1:
             # Initial state or all red
             self.lights[action].set_state("GREEN")
             self.green_timer = 0

        # Run simulation for main duration (10 seconds = 600 frames)
        # Feature: If lane becomes empty, exit early to allow switch
        frames_run = 0
        reward = 0
        for _ in range(600):
            self.handle_events()
            if not self.running: return self.get_state(), reward, True, {}
            self.update()
            self.draw()
            self.clock.tick(60)
            reward += self._calculate_reward()
            frames_run += 1
            
            # Check for early exit (Empty Lane)
            if current_green != -1:
                # Count vehicles in current green lane
                # We need to be careful not to switch TOO fast (flicker), maybe min 2s?
                # But user said "if in this 10 second lane become empty then switch"
                # Let's verify emptiness
                lane_count = 0
                for v in self.vehicles:
                    if v.lane_id == current_green:
                        # Only count vehicles that haven't passed the light yet?
                        # Or just all vehicles in lane. All vehicles is safer.
                        lane_count += 1
                
                if lane_count == 0 and frames_run > 60: # Min 1 second to prevent instant flicker
                    break

        # Update green timer with ACTUAL frames run
        if current_green != -1 and current_green == action:
            self.green_timer += frames_run
            if self.green_timer >= 1800:
                 # Force switch logic...
                 next_action = (current_green + 1) % 4
                 return self.step(next_action)
            
        next_state = self.get_state()
        done = False # Continuous task
        return next_state, reward, done, {}

    def _calculate_reward(self):
        # Negative of total waiting time
        total_wait = sum(v.waiting_time for v in self.vehicles)
        return -total_wait

    def update(self):
        self.spawn_timer += 1
        if self.spawn_timer > 30: # Spawn every 30 frames (0.5s) for higher density
            self.spawn_vehicle()
            self.spawn_timer = 0
            
        for v in self.vehicles:
            v.update(self.lights, self.vehicles)
            
        # Remove off-screen vehicles (with buffer for spawning)
        buffer = 100
        self.vehicles = [v for v in self.vehicles if -buffer <= v.x <= self.width + buffer and -buffer <= v.y <= self.height + buffer]

    def draw(self):
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill((30, 30, 30)) # Fallback
            # Draw Roads
            pygame.draw.rect(self.screen, (50, 50, 50), (self.center_x - 50, 0, 100, self.height)) # Vertical
            pygame.draw.rect(self.screen, (50, 50, 50), (0, self.center_y - 50, self.width, 100)) # Horizontal
            
            # Draw Lane markings (dashed lines)
            for y in range(0, self.height, 40):
                pygame.draw.line(self.screen, (255, 255, 255), (self.center_x, y), (self.center_x, y+20), 2)
            for x in range(0, self.width, 40):
                pygame.draw.line(self.screen, (255, 255, 255), (x, self.center_y), (x+20, self.center_y), 2)

        for light in self.lights:
            light.draw(self.screen)
            
        for v in self.vehicles:
            v.draw(self.screen, self.car_img)
            
        # Run detection on the current frame
        self.detector.process_frame(self.screen)
        
        # UI Overlay
        # Draw semi-transparent panel
        panel = pygame.Surface((200, 100), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        self.screen.blit(panel, (10, 10))
        
        font = pygame.font.SysFont("Arial", 16)
        text_color = (255, 255, 255)
        
        # Stats
        total_vehicles = len(self.vehicles)
        total_wait = sum(v.waiting_time for v in self.vehicles)
        
        self.screen.blit(font.render(f"Vehicles: {total_vehicles}", True, text_color), (20, 20))
        self.screen.blit(font.render(f"Total Wait: {total_wait}", True, text_color), (20, 40))
        self.screen.blit(font.render(f"FPS: {int(self.clock.get_fps())}", True, text_color), (20, 60))
        
        pygame.display.flip()

    def transition(self, target_lane):
        # Find current green
        current_green = -1
        for i, light in enumerate(self.lights):
            if light.state == "GREEN":
                current_green = i
                break
        
        if current_green != -1 and current_green != target_lane:
            # Yellow
            self.lights[current_green].set_state("YELLOW")
            for _ in range(60): # 1 second
                self.handle_events()
                if not self.running: return
                self.update()
                self.draw()
                self.clock.tick(60)
            
            # Red (All-Red Clearance Interval)
            self.lights[current_green].set_state("RED")
            for _ in range(60): # 1 second All-Red
                self.handle_events()
                if not self.running: return
                self.update()
                self.draw()
                self.clock.tick(60)
            
        # Green
        self.lights[target_lane].set_state("GREEN")

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()
