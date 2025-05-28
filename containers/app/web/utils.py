import logging
import os
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


class SystemEventTracker:
    """
    Tracks system events and computes the time difference between consecutive events.
    Detects Spike, Drift, and Dropout anomalies and returns detailed records.
    """

    def __init__(self):
        self.last_event_time: Optional[datetime] = None
        self.drift_start_time: Optional[datetime] = None

    def process_event(
        self, event: Dict[str, Any]
    ) -> list[Any] | dict[str, list[dict[str, Any]] | bool]:
        """
        Process an incoming event and return any anomalies detected.
        """
        anomalies: List[Dict[str, Any]] = []
        sensor_id = event.get("sensor_id")

        try:
            curr_time = datetime.fromisoformat(
                event["timestamp"].replace("Z", "+00:00")
            )
        except (Exception,) as e:
            logging.error(f"Invalid timestamp {event.get('timestamp')}: {e}")
            return []

        if self.last_event_time:
            delta = (curr_time - self.last_event_time).total_seconds()
            if delta > 10:
                anomalies.append(
                    {
                        "type": "dropout",
                        "timestamp": event["timestamp"],
                        "sensor_id": sensor_id,
                        "parameter": None,
                        "value": None,
                        "duration_seconds": int(delta),
                        "message": (
                            f"No data for {delta:.1f}s (threshold 10s) on {sensor_id}"
                        ),
                    }
                )

        self.last_event_time = curr_time

        pressure = event.get("pressure", 0.0)
        flow = event.get("flow", 0.0)
        if pressure > 4.0:
            anomalies.append(
                {
                    "type": "spike",
                    "timestamp": event["timestamp"],
                    "sensor_id": sensor_id,
                    "parameter": "pressure",
                    "value": pressure,
                    "message": (
                        f"Pressure spike: {pressure:.2f} bar (threshold 4.0 bar)"
                    ),
                }
            )
        if flow > 120.0:
            anomalies.append(
                {
                    "type": "spike",
                    "timestamp": event["timestamp"],
                    "sensor_id": sensor_id,
                    "parameter": "flow",
                    "value": flow,
                    "message": f"Flow spike: {flow:.1f} L/min (threshold 120 L/min)",
                }
            )

        temp = event.get("temperature", 0.0)
        if temp > 38.0:
            # start or continue drift
            if self.drift_start_time is None:
                self.drift_start_time = curr_time
            else:
                duration = (curr_time - self.drift_start_time).total_seconds()
                if duration > 15:
                    anomalies.append(
                        {
                            "type": "drift",
                            "timestamp": event["timestamp"],
                            "sensor_id": sensor_id,
                            "parameter": "temperature",
                            "value": temp,
                            "duration_seconds": int(duration),
                            "message": (
                                f"Temperature drift: {temp:.1f} °C for "
                                f"{int(duration)}s (threshold 15s)"
                            ),
                        }
                    )
        else:
            self.drift_start_time = None

        return {"anomalies": anomalies, "is_anomaly": bool(anomalies)}


def llm_active():
    ollama_url = urlparse(os.getenv("OLLAMA_API"))
    host = ollama_url.hostname
    port = ollama_url.port
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False
