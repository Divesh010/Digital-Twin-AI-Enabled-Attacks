from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
from config.models import FDIAttackConfig, OffsetAttackConfig, SlowDripAttackConfig, ReplayAttackConfig

class FDIAttack(ABC):
    def __init__(self, config: FDIAttackConfig):
        self.config = config

    def is_active(self, current_time: datetime, location_id: str) -> bool:
        if not self.config.enabled:
            return False
        if location_id != self.config.target_location:
            return False
        return self.config.start_time <= current_time < self.config.end_time

    def apply(self, record: Dict[str, Any], current_time: datetime) -> Dict[str, Any]:
        if not self.is_active(current_time, record["location_id"]):
            return record
        
        # Mark as manipulated
        record["is_manipulated"] = True
        record["attack_id"] = self.config.attack_id
        record["attack_type"] = self.config.parameters.attack_type
        record["attack_target"] = self.config.target_variable
        record["attack_start"] = self.config.start_time.isoformat()
        record["attack_end"] = self.config.end_time.isoformat()

        # Apply specific manipulation
        target_var = self.config.target_variable
        original_value = record[target_var]
        
        manipulated_value = self._calculate_manipulated_value(original_value, current_time, record)
        
        record[target_var] = manipulated_value
        record["attack_magnitude"] = manipulated_value - original_value
        
        return record

    @abstractmethod
    def _calculate_manipulated_value(self, original_value: float, current_time: datetime, record: Dict[str, Any]) -> float:
        pass
        
    def observe(self, record: Dict[str, Any], current_time: datetime):
        # Used for stateful attacks like replay to record history
        pass


class OffsetAttack(FDIAttack):
    def _calculate_manipulated_value(self, original_value: float, current_time: datetime, record: Dict[str, Any]) -> float:
        params: OffsetAttackConfig = self.config.parameters
        return original_value + params.offset_value


class SlowDripAttack(FDIAttack):
    def _calculate_manipulated_value(self, original_value: float, current_time: datetime, record: Dict[str, Any]) -> float:
        params: SlowDripAttackConfig = self.config.parameters
        elapsed_seconds = (current_time - self.config.start_time).total_seconds()
        offset = params.initial_offset + (params.ramp_rate_per_second * elapsed_seconds)
        return original_value + offset


class ReplayAttack(FDIAttack):
    def __init__(self, config: FDIAttackConfig):
        super().__init__(config)
        self.history: Dict[datetime, float] = {}

    def observe(self, record: Dict[str, Any], current_time: datetime):
        if record["location_id"] == self.config.target_location:
            self.history[current_time] = record[self.config.target_variable]

    def _calculate_manipulated_value(self, original_value: float, current_time: datetime, record: Dict[str, Any]) -> float:
        params: ReplayAttackConfig = self.config.parameters
        # We need to find the value from exact replay_window_seconds ago
        target_replay_time = current_time - pd.Timedelta(seconds=params.replay_window_seconds)
        
        # If we have it in history, return it. Otherwise, return original (or a fallback)
        if target_replay_time in self.history:
            return self.history[target_replay_time]
        else:
            return original_value


class FDIEngine:
    def __init__(self, attack_configs: list[FDIAttackConfig]):
        self.attacks: list[FDIAttack] = []
        for config in attack_configs:
            if not config.enabled:
                continue
            if config.parameters.attack_type == 'OFFSET':
                self.attacks.append(OffsetAttack(config))
            elif config.parameters.attack_type == 'SLOW_DRIP':
                self.attacks.append(SlowDripAttack(config))
            elif config.parameters.attack_type == 'REPLAY':
                self.attacks.append(ReplayAttack(config))

    def observe(self, record: Dict[str, Any], current_time: datetime):
        """Allow stateful attacks to record baseline history."""
        for attack in self.attacks:
            attack.observe(record, current_time)

    def apply_attacks(self, record: Dict[str, Any], current_time: datetime) -> Dict[str, Any]:
        """Apply all active attacks to the reported telemetry record."""
        # Baseline explicit labels if not manipulated
        record["is_manipulated"] = False
        record["attack_id"] = None
        record["attack_type"] = None
        record["attack_target"] = None
        record["attack_start"] = None
        record["attack_end"] = None
        record["attack_magnitude"] = None
        
        # Track original baseline values to enforce strict non-cascading math
        # Precedence: Last attack wins (overwrites previous manipulations for the same variable)
        baseline_values = {
            "reported_co2_ppm": record.get("reported_co2_ppm", 0.0),
            "reported_temperature_c": record.get("reported_temperature_c", 0.0),
            "reported_power_kw": record.get("reported_power_kw", 0.0)
        }
        
        for attack in self.attacks:
            if attack.is_active(current_time, record["location_id"]):
                target = attack.config.target_variable
                original_val = baseline_values[target] # Always use ground truth for math
                
                manipulated_val = attack._calculate_manipulated_value(original_val, current_time, record)
                
                record["is_manipulated"] = True
                record["attack_id"] = attack.config.attack_id
                record["attack_type"] = attack.config.parameters.attack_type
                record["attack_target"] = target
                record["attack_start"] = attack.config.start_time.isoformat()
                record["attack_end"] = attack.config.end_time.isoformat()
                record[target] = manipulated_val
                record["attack_magnitude"] = manipulated_val - original_val
                
        return record
