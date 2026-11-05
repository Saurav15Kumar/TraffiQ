from src.simulation.environment import TrafficSim
import time

if __name__ == "__main__":
    sim = TrafficSim()
    sim.reset()
    
    # Initial state
    current_lane = 0
    sim.lights[current_lane].set_state("GREEN")
    
    timer = 0
    min_time = 120 # 2 seconds (frames)
    max_time = 1800 # 30 seconds (frames)
    
    while sim.running:
        sim.handle_events()
        if not sim.running: break
        
        sim.update()
        sim.draw()
        sim.clock.tick(60)
        
        timer += 1
        
        # Adaptive Logic
        queues = sim.get_state()
        current_q = queues[current_lane]
        
        # Check other queues
        other_queues = [q for i, q in enumerate(queues) if i != current_lane]
        max_other_q = max(other_queues) if other_queues else 0
        
        should_switch = False
        
        # Condition 1: Current lane is empty and others are waiting
        if timer > min_time and current_q == 0 and max_other_q > 0:
            should_switch = True
            
        # Condition 2: Max time reached
        elif timer > max_time:
            should_switch = True
            
        if should_switch:
            # Pick next lane: The one with the longest queue
            # If multiple have same max, pick the one that comes next in cycle (0->1->2->3)
            # to prevent starvation if possible, or just simple max.
            
            best_lane = -1
            max_q = -1
            
            # Check lanes in cyclic order starting from next
            for i in range(1, 4):
                idx = (current_lane + i) % 4
                if queues[idx] > max_q:
                    max_q = queues[idx]
                    best_lane = idx
            
            if best_lane != -1:
                sim.transition(best_lane)
                current_lane = best_lane
                timer = 0
        
    pygame.quit()
