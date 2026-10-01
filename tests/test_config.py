import pytest
from pydantic import ValidationError
from src.config.models import (
    HVACConfig, ScheduleConfig, SimulationConfig, RoomConfig, 
    FloorConfig, BuildingConfig, CampusConfig, RootConfig, MqttConfig, HVACState,
    CO2Config, TemperatureConfig, PowerConfig
)

def test_hvac_stage_ordering():
    with pytest.raises(ValidationError) as exc_info:
        HVACConfig(
            cooling_capacity_kw=10.0,
            stage_fractions={HVACState.OFF: 0.0, HVACState.LOW: 0.8, HVACState.MEDIUM: 0.5, HVACState.HIGH: 1.0}
        )
    assert 'strictly 0.0 < LOW < MEDIUM < 1.0' in str(exc_info.value)

def test_invalid_schedule_time():
    with pytest.raises(ValidationError):
        ScheduleConfig(id='test', profile={'25:00': 0.5})

def test_invalid_schedule_profile_value():
    with pytest.raises(ValidationError):
        ScheduleConfig(id='test', profile={'08:00': 1.5})

def test_invalid_simulation_date_range():
    with pytest.raises(ValidationError):
        SimulationConfig(start_datetime='2026-09-02T00:00:00+05:30', end_datetime='2026-09-01T00:00:00+05:30', dt_seconds=300)

def test_timezone_naive_datetime():
    with pytest.raises(ValidationError):
        SimulationConfig(start_datetime='2026-09-01T00:00:00', end_datetime='2026-09-02T00:00:00', dt_seconds=300)

def get_valid_room(room_id):
    return RoomConfig(
        id=room_id, capacity=10, volume_m3=100.0, schedule_id='s1',
        co2=CO2Config(ventilation_rate_m3_s=0.1),
        temperature=TemperatureConfig(thermal_mass_j_c=1000000.0, thermal_resistance_c_w=0.02),
        hvac=HVACConfig(cooling_capacity_kw=5.0),
        power=PowerConfig(lighting_capacity_kw=1.0)
    )

def test_duplicate_hierarchy_ids():
    r1 = get_valid_room('A101')
    r2 = get_valid_room('A101')
    with pytest.raises(ValidationError) as exc:
        FloorConfig(id='f1', rooms=[r1, r2])
    assert 'Duplicate room IDs' in str(exc.value)

def test_missing_schedule_reference():
    r = get_valid_room('A101')
    r.schedule_id = 'non_existent'
    f = FloorConfig(id='f1', rooms=[r])
    b = BuildingConfig(id='b1', floors=[f])
    c = CampusConfig(id='campus1', buildings=[b])
    s = ScheduleConfig(id='s1', profile={'08:00': 0.5})
    
    with pytest.raises(ValidationError) as exc:
        RootConfig(
            campus=c,
            schedules=[s],
            simulation={'start_datetime': '2026-09-01T00:00:00Z', 'end_datetime': '2026-09-02T00:00:00Z', 'dt_seconds': 300},
            physics={}
        )
    assert 'references undefined schedule_id' in str(exc.value)

def test_deterministic_hash():
    r = get_valid_room('A101')
    c = CampusConfig(id='campus1', buildings=[BuildingConfig(id='b1', floors=[FloorConfig(id='f1', rooms=[r])])])
    s = ScheduleConfig(id='s1', profile={'08:00': 0.5})
    sim = {'start_datetime': '2026-09-01T00:00:00Z', 'end_datetime': '2026-09-02T00:00:00Z', 'dt_seconds': 300}
    
    r1 = RootConfig(campus=c, schedules=[s], simulation=sim, physics={})
    r2 = RootConfig(campus=c, schedules=[s], simulation=sim, physics={})
    assert r1.config_version == r2.config_version
    
    sim2 = {'start_datetime': '2026-09-01T00:00:00Z', 'end_datetime': '2026-09-03T00:00:00Z', 'dt_seconds': 300}
    r3 = RootConfig(campus=c, schedules=[s], simulation=sim2, physics={})
    assert r1.config_version != r3.config_version

def test_invalid_simulation_duration_multiple():
    with pytest.raises(ValidationError) as exc:
        SimulationConfig(start_datetime='2026-09-01T00:00:00+00:00', end_datetime='2026-09-01T00:04:00+00:00', dt_seconds=300)
    assert 'not an exact multiple of dt_seconds' in str(exc.value)

def test_mqtt_config_validation():
    with pytest.raises(ValidationError):
        MqttConfig(broker_port=0)
    with pytest.raises(ValidationError):
        MqttConfig(broker_port=65536)
    with pytest.raises(ValidationError):
        MqttConfig(qos=3)
    with pytest.raises(ValidationError):
        MqttConfig(qos=-1)
    with pytest.raises(ValidationError):
        MqttConfig(mode='invalid')
    with pytest.raises(ValidationError):
        MqttConfig(topic_prefix='   ')
    with pytest.raises(ValidationError):
        MqttConfig(client_id='')
