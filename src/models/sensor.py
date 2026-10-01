import numpy as np

class SensorModel:
    def __init__(self, bias: float, noise_std: float, drift_rate: float, resolution: float, seed: int = 42):
        self.bias = bias
        self.noise_std = noise_std
        self.drift_rate = drift_rate
        self.resolution = resolution
        self.rng = np.random.default_rng(seed)
        self.elapsed_time_s = 0

    def step(self, dt_seconds: int, true_value: float) -> float:
        # Calculate drift based on time BEFORE advancing clock (e.g. at t=0, drift is 0)
        drift = self.drift_rate * self.elapsed_time_s
        noise = self.rng.normal(0, self.noise_std)
        observed = true_value + self.bias + drift + noise
        
        if self.resolution > 0:
            observed = round(observed / self.resolution) * self.resolution
            
        # Advance clock for next reading
        self.elapsed_time_s += dt_seconds
        
        return observed
