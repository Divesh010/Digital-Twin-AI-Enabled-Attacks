import pytest
import json
import pandas as pd
from config.loader import load_config
from simulation.engine import DigitalTwinSimulator
from transport.publisher import LocalMockPublisher, MqttPublisher, build_topic
import paho.mqtt.client as mqtt

@pytest.fixture
def base_config():
    config = load_config("config/root.yaml")
    # Quick 1 interval
    config.simulation.end_datetime = config.simulation.start_datetime + pd.Timedelta(minutes=5)
    config.mqtt.enabled = True
    config.mqtt.mode = "local"
    return config

def test_build_topic():
    record = {
        "university_id": "U1",
        "campus_id": "C1",
        "building_id": "B1",
        "floor_id": "F1",
        "room_id": "R1"
    }
    topic = build_topic("test_prefix", record)
    assert topic == "test_prefix/U1/campus/C1/building/B1/floor/F1/room/R1/telemetry"
    
    parts = topic.split("/")
    assert parts[0] == "test_prefix"
    assert parts[1] == "U1"
    assert parts[2] == "campus"
    assert parts[3] == "C1"
    assert parts[4] == "building"
    assert parts[5] == "B1"
    assert parts[6] == "floor"
    assert parts[7] == "F1"
    assert parts[8] == "room"
    assert parts[9] == "R1"
    assert parts[10] == "telemetry"
    assert len(parts) == 11

def test_transport_mock_semantics(base_config):
    sim = DigitalTwinSimulator(base_config)
    assert isinstance(sim.publisher, LocalMockPublisher)
    
    # 1. connect succeeds
    assert sim.publisher.connected
    
    df = sim.simulate()
    
    # 2. publish preserves topic exactly, JSON payload can be decoded
    # 3. message ordering is preserved
    # 4. number of published messages equals number of canonical simulation records
    messages = sim.publisher.published_messages
    assert len(messages) == len(df)
    
    for i, msg in enumerate(messages):
        row = df.iloc[i].to_dict()
        expected_topic = build_topic(base_config.mqtt.topic_prefix, row)
        assert msg["topic"] == expected_topic
        
        decoded = json.loads(msg["payload_json"])
        assert decoded["location_id"] == row["location_id"]
        # Numeric values preserved without accidental string conversion
        assert isinstance(decoded["true_temperature_c"], float)
        assert abs(decoded["true_temperature_c"] - row["true_temperature_c"]) < 1e-9

    # 5. disconnect is clean
    assert not sim.publisher.connected

def test_transport_payload_semantics(base_config):
    sim = DigitalTwinSimulator(base_config)
    sim.simulate()
    
    msg = sim.publisher.published_messages[0]
    payload = json.loads(msg["payload_json"])
    
    # Explicitly verify all required schema fields
    required_fields = [
        "timestamp", "university_id", "campus_id", "building_id", 
        "floor_id", "room_id", "location_id", "sensor_id",
        "true_co2_ppm", "observed_co2_ppm", "reported_co2_ppm",
        "true_temperature_c", "observed_temperature_c", "reported_temperature_c",
        "hvac_state", "hvac_power_kw", "energy_interval_kwh", "energy_cumulative_kwh",
        "is_manipulated", "sim_run_id", "model_version", "config_version", "random_seed"
    ]
    
    for field in required_fields:
        assert field in payload
        
    assert payload["is_manipulated"] is False

def test_transport_mqtt_connection_failure_fast(base_config):
    # 1 interval
    base_config.mqtt.mode = "cloud"
    base_config.mqtt.broker_host = "invalid.local"
    
    sim = DigitalTwinSimulator(base_config)
    assert isinstance(sim.publisher, MqttPublisher)
    
    df = sim.simulate()
    assert len(df) > 0 # Completed without exception

def test_transport_mqtt_connection_failure_7_day():
    config = load_config("config/root.yaml")
    config.simulation.end_datetime = config.simulation.start_datetime + pd.Timedelta(days=7)
    config.mqtt.enabled = True
    config.mqtt.mode = "cloud"
    config.mqtt.broker_host = "invalid.local"
    
    sim = DigitalTwinSimulator(config)
    df = sim.simulate()
    
    # dynamically calculate expected rows
    expected_rows = int((config.simulation.end_datetime - config.simulation.start_datetime).total_seconds() / config.simulation.dt_seconds) * len(sim.rooms)
    assert len(df) == expected_rows
    assert not df['true_temperature_c'].isnull().any()

def test_transport_causal_isolation():
    config = load_config("config/root.yaml")
    config.simulation.end_datetime = config.simulation.start_datetime + pd.Timedelta(days=1)
    
    # 1. No transport
    config.mqtt.enabled = False
    config.simulation.random_seed = 42
    simA = DigitalTwinSimulator(config)
    dfA = simA.simulate()
    
    # 2. Local mock transport
    config.mqtt.enabled = True
    config.mqtt.mode = "local"
    config.simulation.random_seed = 42
    simB = DigitalTwinSimulator(config)
    dfB = simB.simulate()
    
    # 3. Failing transport
    config.mqtt.mode = "cloud"
    config.mqtt.broker_host = "invalid.local"
    config.simulation.random_seed = 42
    simC = DigitalTwinSimulator(config)
    dfC = simC.simulate()
    
    pd.testing.assert_frame_equal(dfA.drop(columns=['sim_run_id', 'config_version']), dfB.drop(columns=['sim_run_id', 'config_version']))
    pd.testing.assert_frame_equal(dfA.drop(columns=['sim_run_id', 'config_version']), dfC.drop(columns=['sim_run_id', 'config_version']))

class _MockMqttClient:
    def __init__(self, *args, **kwargs):
        self.connected = False
        self.published = 0
        self.on_connect = None
        self.on_disconnect = None
    def reconnect_delay_set(self, min_delay, max_delay):
        pass
    def connect_async(self, host, port, keepalive):
        self.connected = True
    def loop_start(self):
        pass
    def loop_stop(self):
        pass
    def disconnect(self):
        self.connected = False
        if self.on_disconnect: self.on_disconnect(self, None, 0, 0, None)
    def publish(self, topic, payload, qos):
        if not self.connected: raise RuntimeError("Simulated disconnected publish")
        self.published += 1

def test_reconnect_handling(monkeypatch):
    import transport.publisher
    monkeypatch.setattr(mqtt, "Client", _MockMqttClient)
    
    pub = MqttPublisher("localhost", 1883, "test")
    # Simulate async connect callback
    pub.connect()
    pub._on_connect(pub.client, None, 0, 0, None)
    assert pub.connected
    
    # Simulate publish success
    pub.publish("topic", {"data": 1})
    assert pub.client.published == 1
    
    # Simulate unexpected disconnect
    pub._on_disconnect(pub.client, None, 0, 1, None)
    assert not pub.connected
    
    # Simulate publish while disconnected (best-effort skips without crash)
    pub.publish("topic", {"data": 2})
    assert pub.client.published == 1 # Unchanged
    
    # Clean disconnect
    pub.disconnect()
    assert not pub.connected

