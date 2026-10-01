import numpy as np

class LightingModel:
    def __init__(self, capacity_kw: float):
        self.capacity_kw = capacity_kw

    def step(self, occupancy: int) -> float:
        return self.capacity_kw if occupancy > 0 else 0.0

class PlugLoadModel:
    def __init__(self, plug_load_per_person_kw: float, noise_std: float = 0.01, seed: int = 42):
        self.load_per_person_kw = plug_load_per_person_kw
        self.noise_std = noise_std
        self.rng = np.random.default_rng(seed)

    def step(self, occupancy: int) -> float:
        # Plug load depends only on occupancy/activity
        base = occupancy * self.load_per_person_kw
        noise = self.rng.normal(0, self.noise_std) if occupancy > 0 else 0.0
        return max(0.0, base + noise)

class EnergyModel:
    def __init__(self):
        self.cumulative_energy_kwh = 0.0

    def step(self, dt_seconds: int, p_base_kw: float, p_light_kw: float, p_plug_kw: float, p_hvac_kw: float) -> tuple[float, float, float]:
        # Exact summation of mutually exclusive components
        p_total_kw = p_base_kw + p_light_kw + p_plug_kw + p_hvac_kw
        interval_kwh = p_total_kw * (dt_seconds / 3600.0)
        self.cumulative_energy_kwh += interval_kwh
        return p_total_kw, interval_kwh, self.cumulative_energy_kwh
