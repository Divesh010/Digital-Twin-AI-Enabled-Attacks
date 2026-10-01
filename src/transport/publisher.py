from typing import Dict, Any, List
import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

def build_topic(topic_prefix: str, record: Dict[str, Any]) -> str:
    return f"{topic_prefix}/{record['university_id']}/campus/{record['campus_id']}/building/{record['building_id']}/floor/{record['floor_id']}/room/{record['room_id']}/telemetry"

class TelemetryPublisher(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass
        
    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        pass

class LocalMockPublisher(TelemetryPublisher):
    def __init__(self):
        self.published_messages: List[Dict[str, Any]] = []
        self.connected = False

    def connect(self) -> None:
        self.connected = True
        logger.info("LocalMockPublisher connected")

    def disconnect(self) -> None:
        self.connected = False
        logger.info("LocalMockPublisher disconnected")

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        if not self.connected:
            raise RuntimeError("Cannot publish before connect()")
        message = {
            "topic": topic,
            "payload_json": json.dumps(payload, default=str)
        }
        self.published_messages.append(message)

class MqttPublisher(TelemetryPublisher):
    def __init__(self, host: str, port: int, client_id: str, qos: int = 1):
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            raise ImportError("paho-mqtt is required for MqttPublisher")
            
        self.host = host
        self.port = port
        self.qos = qos
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.connected = False
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.host}:{self.port}")
        else:
            logger.error(f"Failed to connect to MQTT broker, reason: {reason_code}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.connected = False
        if reason_code != 0:
            logger.warning(f"Unexpected disconnection from {self.host}:{self.port} (reason: {reason_code})")

    def connect(self) -> None:
        try:
            self.client.reconnect_delay_set(min_delay=1, max_delay=120)
            self.client.connect_async(self.host, self.port, keepalive=60)
            self.client.loop_start()
            # Mark connected optimistically, but it will truly set upon callback
            # We don't want to block the thread
            self.connected = True
        except Exception as e:
            logger.error(f"MQTT async connection failed: {e}")
            self.connected = False

    def disconnect(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        if not self.connected:
            logger.debug(f"Skipping publish to {topic}, MQTT not connected")
            return
            
        try:
            payload_str = json.dumps(payload, default=str)
            self.client.publish(topic, payload_str, qos=self.qos)
        except Exception as e:
            logger.error(f"Publish failed: {e}")

class PublisherFactory:
    @staticmethod
    def create(config) -> TelemetryPublisher:
        if not config.mqtt.enabled:
            return LocalMockPublisher() 
            
        if config.mqtt.mode == "local":
            return LocalMockPublisher()
        else:
            return MqttPublisher(
                host=config.mqtt.broker_host,
                port=config.mqtt.broker_port,
                client_id=config.mqtt.client_id,
                qos=config.mqtt.qos
            )
