import numpy as np
from datetime import datetime

class OccupancyModel:
    def __init__(self, capacity: int, schedule_profile: dict, alpha: float = 0.2, noise_std: float = 2.0, seed: int = 42):
        self.capacity = capacity
        self.profile = schedule_profile
        self.alpha = alpha
        self.noise_std = noise_std
        self.rng = np.random.default_rng(seed)
        self.current_occupancy = 0.0

    def _get_scheduled_fraction(self, current_time: datetime) -> float:
        time_str = current_time.strftime("%H:%M")
        fraction = 0.0
        for k, v in self.profile.items():
            if time_str >= k:
                fraction = v
            else:
                break
        return fraction

    def step(self, current_time: datetime) -> int:
        expected = self._get_scheduled_fraction(current_time) * self.capacity
        noise = self.rng.normal(0, self.noise_std)
        o_prime = self.current_occupancy + self.alpha * (expected - self.current_occupancy) + noise
        o_prime = max(0.0, min(float(self.capacity), o_prime))
        self.current_occupancy = o_prime
        return int(round(self.current_occupancy))
