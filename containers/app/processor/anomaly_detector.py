import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class SystemEventTracker:
    def __init__(self) -> None:
        self.last_event_times: Dict[str, Optional[datetime]] = {}
        self.drift_start_times: Dict[str, Optional[datetime]] = {}

    def process_event(
        self, event: Dict[str, Any]
    ) -> Dict[str, Union[List[Dict[str, Any]], bool]]:
        anomalies: List[Dict[str, Any]] = []
        sensor_id: str = event.get("sensor_id")  # type: ignore

        try:
            curr_time: datetime = datetime.fromisoformat(
                event["timestamp"].replace("Z", "+00:00")  # type: ignore
            )
        except (Exception,) as exc:
            logging.error(f"Invalid timestamp {event.get('timestamp')}: {exc}")
            return {"anomalies": [], "is_anomaly": False}

        # Dropout detection
        last_time: Optional[datetime] = self.last_event_times.get(sensor_id)
        if last_time:
            delta: float = (curr_time - last_time).total_seconds()
            if delta > 10:
                anomalies.append(
                    {
                        "type": "dropout",
                        "timestamp": event["timestamp"],
                        "sensor_id": sensor_id,
                        "parameter": None,
                        "value": None,
                        "duration_seconds": int(delta),
                        "message": f"No data for {delta:.1f}s (threshold 10s) on {sensor_id}",
                    }
                )

        # Update last event time
        self.last_event_times[sensor_id] = curr_time

        # Spike detection
        pressure: float = event.get("pressure", 0.0)  # type: ignore
        flow: float = event.get("flow", 0.0)  # type: ignore
        if pressure > 4.0:
            anomalies.append(
                {
                    "type": "spike",
                    "timestamp": event["timestamp"],
                    "sensor_id": sensor_id,
                    "parameter": "pressure",
                    "value": pressure,
                    "message": f"Pressure spike: {pressure:.2f} bar (threshold 4.0 bar)",
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

        # Drift detection
        temp: float = event.get("temperature", 0.0)  # type: ignore
        drift_start: Optional[datetime] = self.drift_start_times.get(sensor_id)
        if temp > 38.0:
            if drift_start is None:
                self.drift_start_times[sensor_id] = curr_time
            else:
                duration: float = (curr_time - drift_start).total_seconds()
                if duration > 15:
                    anomalies.append(
                        {
                            "type": "drift",
                            "timestamp": event["timestamp"],
                            "sensor_id": sensor_id,
                            "parameter": "temperature",
                            "value": temp,
                            "duration_seconds": int(duration),
                            "message": f"Temperature drift: {temp:.1f} °C for {int(duration)}s (threshold 15s)",
                        }
                    )
        else:
            self.drift_start_times[sensor_id] = None

        return {"anomalies": anomalies, "is_anomaly": bool(anomalies)}
