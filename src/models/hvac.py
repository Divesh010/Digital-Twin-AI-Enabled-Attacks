from config.models import HVACState

class HVACController:
    def __init__(self, cooling_capacity_kw: float, cop: float, setpoint_c: float, upper_deadband_c: float, lower_deadband_c: float, min_on_time_minutes: float, min_off_time_minutes: float, stage_fractions: dict):
        self.cooling_capacity_kw = cooling_capacity_kw
        self.cop = cop
        self.setpoint_c = setpoint_c
        self.upper_deadband_c = upper_deadband_c
        self.lower_deadband_c = lower_deadband_c
        self.min_on_seconds = min_on_time_minutes * 60
        self.min_off_seconds = min_off_time_minutes * 60
        self.stages = stage_fractions
        
        self.current_state = HVACState.OFF
        self.time_in_state_seconds = 0
        self.ordered_states = [HVACState.OFF, HVACState.LOW, HVACState.MEDIUM, HVACState.HIGH]

    def step(self, dt_seconds: int, observed_temp_c: float) -> tuple[HVACState, float, float]:
        self.time_in_state_seconds += dt_seconds
        error = observed_temp_c - self.setpoint_c
        
        current_idx = self.ordered_states.index(self.current_state)
        state_changed = False
        
        if error > self.upper_deadband_c:
            can_increase = (self.current_state == HVACState.OFF and self.time_in_state_seconds >= self.min_off_seconds) or \
                           (self.current_state != HVACState.OFF and self.time_in_state_seconds >= self.min_on_seconds)
            if can_increase and current_idx < len(self.ordered_states) - 1:
                self.current_state = self.ordered_states[current_idx + 1]
                state_changed = True
        elif error < -self.lower_deadband_c:
            can_decrease = self.time_in_state_seconds >= self.min_on_seconds
            if can_decrease and current_idx > 0:
                self.current_state = self.ordered_states[current_idx - 1]
                state_changed = True
                
        if state_changed:
            self.time_in_state_seconds = 0
            
        fraction = self.stages[self.current_state]
        hvac_thermal_w = -fraction * self.cooling_capacity_kw * 1000
        hvac_power_kw = abs(hvac_thermal_w) / (self.cop * 1000)
        
        return self.current_state, hvac_power_kw, hvac_thermal_w
