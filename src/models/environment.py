class CO2Model:
    def __init__(self, volume_m3: float, generation_rate_m3_s_person: float, ventilation_rate_m3_s: float, initial_co2_ppm: float = 400.0):
        self.volume_m3 = volume_m3
        self.g_m3_s_p = generation_rate_m3_s_person
        self.q_m3_s = ventilation_rate_m3_s
        self.current_co2_ppm = initial_co2_ppm

    def step(self, dt_seconds: int, occupancy: int, outdoor_co2_ppm: float) -> float:
        g_ppm = self.g_m3_s_p * 1e6
        term1 = (g_ppm * occupancy) / self.volume_m3
        term2 = (self.q_m3_s / self.volume_m3) * (outdoor_co2_ppm - self.current_co2_ppm)
        self.current_co2_ppm += dt_seconds * (term1 + term2)
        self.current_co2_ppm = max(0.0, self.current_co2_ppm)
        return self.current_co2_ppm

class TemperatureModel:
    def __init__(self, thermal_mass_j_c: float, thermal_resistance_c_w: float, heat_per_person_w: float, initial_temp_c: float = 24.0):
        self.c_th = thermal_mass_j_c
        self.r_th = thermal_resistance_c_w
        self.heat_per_person_w = heat_per_person_w
        self.current_temp_c = initial_temp_c

    def step(self, dt_seconds: int, occupancy: int, lighting_power_w: float, plug_power_w: float, hvac_thermal_w: float, outdoor_temp_c: float) -> float:
        h_occ = occupancy * self.heat_per_person_w
        h_env = (outdoor_temp_c - self.current_temp_c) / self.r_th
        h_total = h_occ + lighting_power_w + plug_power_w + h_env + hvac_thermal_w
        
        self.current_temp_c += (dt_seconds / self.c_th) * h_total
        return self.current_temp_c
