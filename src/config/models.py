from datetime import datetime
from enum import Enum
import hashlib
import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, AwareDatetime, model_validator

class HVACState(str, Enum):
    OFF = "OFF"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

def default_hvac_stages():
    return {HVACState.OFF: 0.0, HVACState.LOW: 0.35, HVACState.MEDIUM: 0.65, HVACState.HIGH: 1.0}

class SensorConfig(BaseModel):
    bias: float = 0.0
    noise_std: float = Field(0.0, ge=0.0)
    drift_rate: float = 0.0
    resolution: float = Field(0.01, gt=0.0)

class CO2Config(BaseModel):
    generation_rate_m3_s_person: float = Field(5e-6, gt=0.0)
    ventilation_rate_m3_s: float = Field(..., ge=0.0)

class TemperatureConfig(BaseModel):
    thermal_mass_j_c: float = Field(..., gt=0.0)
    thermal_resistance_c_w: float = Field(..., gt=0.0)
    heat_per_person_w: float = Field(100.0, ge=0.0)

class HVACConfig(BaseModel):
    cooling_capacity_kw: float = Field(..., gt=0.0)
    cop: float = Field(3.0, gt=1.0)
    setpoint_c: float = Field(24.0, gt=0.0)
    upper_deadband_c: float = Field(1.0, gt=0.0)
    lower_deadband_c: float = Field(1.0, gt=0.0)
    min_on_time_minutes: float = Field(5.0, ge=0.0)
    min_off_time_minutes: float = Field(5.0, ge=0.0)
    stage_fractions: Dict[HVACState, float] = Field(default_factory=default_hvac_stages)

    @model_validator(mode='after')
    def validate_stages(self):
        s = self.stage_fractions
        off = s.get(HVACState.OFF, 0.0)
        low = s.get(HVACState.LOW, 0.0)
        med = s.get(HVACState.MEDIUM, 0.0)
        high = s.get(HVACState.HIGH, 1.0)
        if off != 0.0 or high != 1.0:
            raise ValueError("HVAC OFF must be 0.0 and HIGH must be 1.0")
        if not (0.0 < low < med < 1.0):
            raise ValueError("HVAC stage fractions must be strictly 0.0 < LOW < MEDIUM < 1.0")
        return self

class PowerConfig(BaseModel):
    base_load_kw: float = Field(0.0, ge=0.0)
    lighting_capacity_kw: float = Field(..., ge=0.0)
    plug_load_per_person_kw: float = Field(0.05, ge=0.0)

class RoomConfig(BaseModel):
    id: str
    capacity: int = Field(..., gt=0)
    volume_m3: float = Field(..., gt=0.0)
    schedule_id: str
    co2: CO2Config
    temperature: TemperatureConfig
    hvac: HVACConfig
    power: PowerConfig
    sensors: Dict[str, SensorConfig] = Field(default_factory=dict)

class FloorConfig(BaseModel):
    id: str
    rooms: List[RoomConfig]

    @model_validator(mode='after')
    def validate_unique_rooms(self):
        ids = [r.id for r in self.rooms]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate room IDs found within floor")
        return self

class BuildingConfig(BaseModel):
    id: str
    floors: List[FloorConfig]

    @model_validator(mode='after')
    def validate_unique_floors(self):
        ids = [f.id for f in self.floors]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate floor IDs found within building")
        return self

class CampusConfig(BaseModel):
    id: str
    buildings: List[BuildingConfig]

    @model_validator(mode='after')
    def validate_unique_buildings(self):
        ids = [b.id for b in self.buildings]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate building IDs found within campus")
        return self

class ScheduleConfig(BaseModel):
    id: str
    profile: Dict[str, float]

    @model_validator(mode='after')
    def validate_profile(self):
        if not self.profile:
            raise ValueError("Schedule profile must have at least one point")
        time_pattern = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
        for k, v in self.profile.items():
            if not time_pattern.match(k):
                raise ValueError(f"Invalid time format in schedule: {k}")
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"Schedule value must be between 0.0 and 1.0")
        
        # Explicitly normalize/sort schedule chronologically
        self.profile = {k: self.profile[k] for k in sorted(self.profile.keys())}
        return self

class PhysicsConfig(BaseModel):
    outdoor_temperature_c: float = 30.0
    outdoor_humidity_pct: float = 50.0
    outdoor_co2_ppm: float = 400.0

class SimulationConfig(BaseModel):
    start_datetime: AwareDatetime
    end_datetime: AwareDatetime
    dt_seconds: int = Field(300, gt=0)
    random_seed: int = 42

    @model_validator(mode='after')
    def validate_timing(self):
        duration_sec = (self.end_datetime - self.start_datetime).total_seconds()
        if duration_sec <= 0:
            raise ValueError("end_datetime must be strictly greater than start_datetime")
        if duration_sec % self.dt_seconds != 0:
            raise ValueError(f"Simulation duration ({duration_sec}s) is not an exact multiple of dt_seconds ({self.dt_seconds}s)")
        return self

class CalibrationConfig(BaseModel):
    enable_calibration: bool = False
    target_dataset_path: Optional[str] = None

class ScenarioConfig(BaseModel):
    id: str
    occupancy_multiplier: float = Field(1.0, ge=0.0)
    hvac_setpoint_offset_c: float = 0.0

class MqttConfig(BaseModel):
    enabled: bool = False
    mode: str = Field('local', pattern='^(local|cloud)$')
    broker_host: str = Field('localhost', min_length=1)
    broker_port: int = Field(1883, ge=1, le=65535)
    client_id: str = Field('dt_simulator', min_length=1)
    topic_prefix: str = Field('dt', min_length=1)
    qos: int = Field(1, ge=0, le=2)

    @model_validator(mode='after')
    def validate_whitespace(self):
        if not self.topic_prefix.strip():
            raise ValueError('topic_prefix cannot be whitespace only')
        if not self.client_id.strip():
            raise ValueError('client_id cannot be whitespace only')
        return self

from typing import Literal, Any, Union
from pydantic import Field

class OffsetAttackConfig(BaseModel):
    attack_type: Literal['OFFSET'] = 'OFFSET'
    offset_value: float

class SlowDripAttackConfig(BaseModel):
    attack_type: Literal['SLOW_DRIP'] = 'SLOW_DRIP'
    initial_offset: float
    ramp_rate_per_second: float

class ReplayAttackConfig(BaseModel):
    attack_type: Literal['REPLAY'] = 'REPLAY'
    replay_window_seconds: int = Field(..., gt=0)

class FDIAttackConfig(BaseModel):
    attack_id: str = Field(..., min_length=1)
    enabled: bool = True
    target_location: str = Field(..., min_length=1)
    target_variable: Literal['reported_co2_ppm', 'reported_temperature_c', 'reported_power_kw']
    start_time: AwareDatetime
    end_time: AwareDatetime
    parameters: Union[OffsetAttackConfig, SlowDripAttackConfig, ReplayAttackConfig]
    random_seed: int = 42

    @model_validator(mode='after')
    def validate_timing(self):
        duration_sec = (self.end_time - self.start_time).total_seconds()
        if duration_sec <= 0:
            raise ValueError("end_time must be strictly greater than start_time")
        return self


class RootConfig(BaseModel):
    campus: CampusConfig
    schedules: List[ScheduleConfig]
    physics: PhysicsConfig
    simulation: SimulationConfig
    scenarios: List[ScenarioConfig] = Field(default_factory=list)
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)
    mqtt: MqttConfig = Field(default_factory=MqttConfig)
    attacks: List[FDIAttackConfig] = Field(default_factory=list)
    university_id: str = "bennett_uni"
    model_version: str = "v1.0.0"

    @model_validator(mode='after')
    def validate_cross_references(self):
        schedule_ids = {s.id for s in self.schedules}
        valid_locations = set()
        
        for b in self.campus.buildings:
            for f in b.floors:
                for r in f.rooms:
                    if r.schedule_id not in schedule_ids:
                        raise ValueError(f"Room {r.id} references undefined schedule_id: {r.schedule_id}")
                    loc = f"{self.university_id}.{self.campus.id}.{b.id}.{f.id}.{r.id}"
                    valid_locations.add(loc)
                    
        # Validate FDI configurations
        attack_ids = set()
        for attack in self.attacks:
            if not attack.enabled:
                continue
            if attack.attack_id in attack_ids:
                raise ValueError(f"Duplicate attack_id: {attack.attack_id}")
            attack_ids.add(attack.attack_id)
            
            if attack.target_location not in valid_locations:
                raise ValueError(f"Invalid FDI target_location: {attack.target_location}")
                
        return self

    @property
    def config_version(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()[:16]
