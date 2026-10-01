import pandas as pd
from transport.publisher import PublisherFactory, TelemetryPublisher, build_topic
from attacks.engine import FDIEngine
from datetime import timedelta
import uuid
import hashlib
from typing import List

from config.models import RootConfig
from models.occupancy import OccupancyModel
from models.environment import CO2Model, TemperatureModel
from models.hvac import HVACController
from models.power import LightingModel, PlugLoadModel, EnergyModel
from models.sensor import SensorModel
from simulation.state_manager import StateManager, RoomState

def get_room_seed(master_seed: int, location_id: str, component: str) -> int:
    hash_input = f"{master_seed}_{location_id}_{component}".encode()
    return int(hashlib.md5(hash_input).hexdigest(), 16) % (2**32)

class RoomContext:
    def __init__(self, room_config, b_id, f_id, c_id, u_id, schedules, physics, sim_config):
        self.config = room_config
        loc_id = f"{u_id}.{c_id}.{b_id}.{f_id}.{room_config.id}"
        self.state = RoomState(
            university_id=u_id, campus_id=c_id, building_id=b_id, floor_id=f_id, room_id=room_config.id, location_id=loc_id,
            true_co2_ppm=physics.outdoor_co2_ppm, observed_co2_ppm=physics.outdoor_co2_ppm, reported_co2_ppm=physics.outdoor_co2_ppm,
            true_temperature_c=physics.outdoor_temperature_c, observed_temperature_c=physics.outdoor_temperature_c, reported_temperature_c=physics.outdoor_temperature_c,
            humidity_pct=physics.outdoor_humidity_pct, base_power_kw=room_config.power.base_load_kw
        )
        
        schedule = next(s for s in schedules if s.id == room_config.schedule_id)
        seed = sim_config.random_seed
        self.occ_model = OccupancyModel(room_config.capacity, schedule.profile, seed=get_room_seed(seed, loc_id, "occ"))
        self.co2_model = CO2Model(room_config.volume_m3, room_config.co2.generation_rate_m3_s_person, room_config.co2.ventilation_rate_m3_s, initial_co2_ppm=physics.outdoor_co2_ppm)
        self.temp_model = TemperatureModel(room_config.temperature.thermal_mass_j_c, room_config.temperature.thermal_resistance_c_w, room_config.temperature.heat_per_person_w, initial_temp_c=physics.outdoor_temperature_c)
        self.hvac = HVACController(room_config.hvac.cooling_capacity_kw, room_config.hvac.cop, room_config.hvac.setpoint_c, room_config.hvac.upper_deadband_c, room_config.hvac.lower_deadband_c, room_config.hvac.min_on_time_minutes, room_config.hvac.min_off_time_minutes, room_config.hvac.stage_fractions)
        self.light_model = LightingModel(room_config.power.lighting_capacity_kw)
        self.plug_model = PlugLoadModel(room_config.power.plug_load_per_person_kw, seed=get_room_seed(seed, loc_id, "plug"))
        self.energy_model = EnergyModel()
        
        def make_sensor(s_conf, comp):
            if s_conf: return SensorModel(s_conf.bias, s_conf.noise_std, s_conf.drift_rate, s_conf.resolution, get_room_seed(seed, loc_id, comp))
            return SensorModel(0.0, 0.0, 0.0, 0.0, get_room_seed(seed, loc_id, comp))
        
        self.temp_sensor = make_sensor(room_config.sensors.get("temperature"), "temp_sensor")
        self.co2_sensor = make_sensor(room_config.sensors.get("co2"), "co2_sensor")
        self.power_sensor = make_sensor(room_config.sensors.get("power"), "power_sensor")

class DigitalTwinSimulator:
    def __init__(self, config: RootConfig):
        self.config = config
        self.sim_run_id = str(uuid.uuid4())
        self.publisher = PublisherFactory.create(config)
        self.publisher.connect()
        self.fdi_engine = FDIEngine(config.attacks)
        self.state_manager = StateManager()
        self.rooms: List[RoomContext] = []
        self._init_campus()
        
    def _init_campus(self):
        c = self.config
        u_id = c.university_id
        c_id = c.campus.id
        for b in c.campus.buildings:
            for f in b.floors:
                for r in f.rooms:
                    ctx = RoomContext(r, b.id, f.id, c_id, u_id, c.schedules, c.physics, c.simulation)
                    self.rooms.append(ctx)
                    self.state_manager.add_room(ctx.state)

    def simulate(self) -> pd.DataFrame:
        records = []
        dt_seconds = self.config.simulation.dt_seconds
        current_time = self.config.simulation.start_datetime
        end_time = self.config.simulation.end_datetime
        phys = self.config.physics
        
        while current_time < end_time:
            for ctx in self.rooms:
                st = ctx.state
                
                occ = ctx.occ_model.step(current_time)
                st.occupancy = occ
                st.occupancy_pct = (occ / ctx.config.capacity) * 100.0 if ctx.config.capacity > 0 else 0.0
                
                t_obs = ctx.temp_sensor.step(dt_seconds, st.true_temperature_c)
                st.observed_temperature_c = t_obs
                
                hvac_st, hvac_p_kw, hvac_th_w = ctx.hvac.step(dt_seconds, t_obs)
                st.hvac_state = hvac_st.value
                st.hvac_power_kw = hvac_p_kw
                
                p_light = ctx.light_model.step(occ)
                p_plug = ctx.plug_model.step(occ)
                st.lighting_power_kw = p_light
                st.plug_power_kw = p_plug
                
                co2_true = ctx.co2_model.step(dt_seconds, occ, phys.outdoor_co2_ppm)
                st.true_co2_ppm = co2_true
                
                t_true = ctx.temp_model.step(dt_seconds, occ, p_light*1000, p_plug*1000, hvac_th_w, phys.outdoor_temperature_c)
                st.true_temperature_c = t_true
                
                p_tot, e_int, e_cum = ctx.energy_model.step(dt_seconds, st.base_power_kw, p_light, p_plug, hvac_p_kw)
                st.true_power_kw = p_tot
                st.energy_interval_kwh = e_int
                st.energy_cumulative_kwh = e_cum
                
                st.observed_co2_ppm = ctx.co2_sensor.step(dt_seconds, co2_true)
                st.observed_power_kw = ctx.power_sensor.step(dt_seconds, p_tot)
                
                # Causal lock: reported equals observed, never fed back into physics
                st.reported_temperature_c = st.observed_temperature_c
                st.reported_co2_ppm = st.observed_co2_ppm
                st.reported_power_kw = st.observed_power_kw
                
                if hasattr(self, 'post_step_hook'): self.post_step_hook(ctx.state)
                record = {
                    "timestamp": current_time.isoformat(),
                    "university_id": st.university_id, "campus_id": st.campus_id, "building_id": st.building_id,
                    "floor_id": st.floor_id, "room_id": st.room_id, "location_id": st.location_id, 
                    "sensor_id": f"{st.location_id}.multi_sensor",
                    "occupancy": st.occupancy, "occupancy_pct": st.occupancy_pct,
                    "true_co2_ppm": st.true_co2_ppm, "observed_co2_ppm": st.observed_co2_ppm, "reported_co2_ppm": st.reported_co2_ppm,
                    "true_temperature_c": st.true_temperature_c, "observed_temperature_c": st.observed_temperature_c, "reported_temperature_c": st.reported_temperature_c,
                    "humidity_pct": st.humidity_pct, "hvac_state": st.hvac_state, "hvac_power_kw": st.hvac_power_kw,
                    "lighting_power_kw": st.lighting_power_kw, "plug_power_kw": st.plug_power_kw, "base_power_kw": st.base_power_kw,
                    "true_power_kw": st.true_power_kw, "observed_power_kw": st.observed_power_kw, "reported_power_kw": st.reported_power_kw,
                    "energy_interval_kwh": st.energy_interval_kwh, "energy_cumulative_kwh": st.energy_cumulative_kwh,
                    "outdoor_temperature_c": phys.outdoor_temperature_c, "outdoor_humidity_pct": phys.outdoor_humidity_pct, "outdoor_co2_ppm": phys.outdoor_co2_ppm,
                    "data_source": "SYNTHETIC", "is_missing": False, "is_imputed": False, "is_sensor_fault": False, "is_outlier": False, "is_manipulated": False,
                    "sim_run_id": self.sim_run_id, "model_version": self.config.model_version, "config_version": self.config.config_version, "random_seed": self.config.simulation.random_seed
                }
                
                # Observe history for Replay attacks BEFORE applying
                self.fdi_engine.observe(record, current_time)
                
                # Apply FDI attacks (manipulates only reported_* fields)
                record = self.fdi_engine.apply_attacks(record, current_time)
                
                records.append(record)
                
                if self.config.mqtt.enabled:
                    topic = build_topic(self.config.mqtt.topic_prefix, record)
                    self.publisher.publish(topic, record)
            current_time += timedelta(seconds=dt_seconds)
            
        self.publisher.disconnect()
        return pd.DataFrame(records)






