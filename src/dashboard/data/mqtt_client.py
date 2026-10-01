import paho.mqtt.client as mqtt
import json
import threading
import time
import pandas as pd
from typing import List, Dict, Any

class LiveMQTTClient:
    def __init__(self, host: str, port: int, topic: str):
        self.host = host
        self.port = port
        self.topic = topic
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        self.is_connected = False
        self.messages: List[Dict[str, Any]] = []
        self._thread = None
        self._stop_event = threading.Event()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            self.client.subscribe(self.topic)
        else:
            self.is_connected = False

    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if 'timestamp' in payload and 'room_id' in payload:
                self.messages.append(payload)
                if len(self.messages) > 1000:
                    self.messages = self.messages[-1000:]
        except Exception:
            pass

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
            
        self._stop_event.clear()
        
        def run():
            try:
                self.client.connect(self.host, self.port, keepalive=60)
                self.client.loop_start()
            except Exception:
                self.is_connected = False
                
            while not self._stop_event.is_set():
                time.sleep(1)
                
            self.client.loop_stop()
            self.client.disconnect()
            
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            
    def get_latest_data(self) -> pd.DataFrame:
        if not self.messages:
            return pd.DataFrame()
        df = pd.DataFrame(self.messages)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df