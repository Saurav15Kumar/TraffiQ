import numpy as np
import random
import pickle

class QLearningAgent:
    def __init__(self, action_space_size, alpha=0.1, gamma=0.99, epsilon=1.0, epsilon_decay=0.995, min_epsilon=0.01):
        self.action_space_size = action_space_size
        self.alpha = alpha # Learning rate
        self.gamma = gamma # Discount factor
        self.epsilon = epsilon # Exploration rate
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.q_table = {} # State -> [Q-values]

    def get_q_values(self, state):
        if state not in self.q_table:
            self.q_table[state] = np.zeros(self.action_space_size)
        return self.q_table[state]

    def choose_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            return random.randint(0, self.action_space_size - 1)
        else:
            return np.argmax(self.get_q_values(state))

    def learn(self, state, action, reward, next_state):
        old_q = self.get_q_values(state)[action]
        next_max_q = np.max(self.get_q_values(next_state))
        
        new_q = old_q + self.alpha * (reward + self.gamma * next_max_q - old_q)
        self.q_table[state][action] = new_q
        
        if self.epsilon > self.min_epsilon:
            self.epsilon *= self.epsilon_decay

    def save(self, filename):
        data = {
            'q_table': self.q_table,
            'epsilon': self.epsilon
        }
        with open(filename, 'wb') as f:
            pickle.dump(data, f)

    def load(self, filename):
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            if isinstance(data, dict) and 'q_table' in data:
                self.q_table = data['q_table']
                self.epsilon = data.get('epsilon', self.epsilon)
            else:
                # Backward compatibility for old files (just q_table)
                self.q_table = data
