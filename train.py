from src.simulation.environment import TrafficSim
from src.rl.agent import QLearningAgent
import time

def train():
    env = TrafficSim() # Note: This will open a window. For headless, we'd need to modify TrafficSim.
    agent = QLearningAgent(action_space_size=4)
    
    episodes = 50
    for episode in range(episodes):
        state = env.reset()
        # Discretize/Cap state
        state = tuple(min(x, 5) for x in state)
        
        total_reward = 0
        done = False
        step_count = 0
        max_steps = 100 # Steps per episode
        
        print(f"Episode {episode+1} started")
        
        while not done and step_count < max_steps:
            # Handle Pygame events to keep window responsive
            env.handle_events()
            if not env.running:
                done = True
                break
                
            action = agent.choose_action(state)
            next_state_raw, reward, done, _ = env.step(action)
            next_state = tuple(min(x, 5) for x in next_state_raw)
            
            agent.learn(state, action, reward, next_state)
            
            state = next_state
            total_reward += reward
            step_count += 1
            
            # Optional: Render is built into step() in our simplified env, but usually separate
            env.draw()
            
        print(f"Episode {episode+1} finished. Total Reward: {total_reward}")
        
    agent.save("q_table.pkl")
    print("Training finished. Model saved.")
    env.run()

if __name__ == "__main__":
    train()
