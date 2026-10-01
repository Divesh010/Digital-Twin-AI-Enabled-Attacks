from dataclasses import dataclass
from typing import Dict

@dataclass
class RoomState:
    university_id: str
    campus_id: str
    building_id: str
    floor_id: str
    room_id: str
    location_id: str
    
    occupancy: int = 0
    occupancy_pct: float = 0.0
    true_co2_ppm: float = 400.0
    observed_co2_ppm: float = 400.0
    reported_co2_ppm: float = 400.0
    true_temperature_c: float = 24.0
    observed_temperature_c: float = 24.0
    reported_temperature_c: float = 24.0
    humidity_pct: float = 50.0
    hvac_state: str = "OFF"
    hvac_power_kw: float = 0.0
    lighting_power_kw: float = 0.0
    plug_power_kw: float = 0.0
    base_power_kw: float = 0.0
    true_power_kw: float = 0.0
    observed_power_kw: float = 0.0
    reported_power_kw: float = 0.0
    energy_interval_kwh: float = 0.0
    energy_cumulative_kwh: float = 0.0

class StateManager:
    def __init__(self):
        self._rooms: Dict[str, RoomState] = {}
        
    def add_room(self, state: RoomState):
        self._rooms[state.location_id] = state
        
    def get_room_state(self, location_id: str) -> RoomState:
        return self._rooms[location_id]
