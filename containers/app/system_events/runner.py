import http.client
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from typing import Dict, Union

logger = logging.getLogger("runner.py")

ENDPOINT_URL: str = f"{os.getenv('APP_INTERNAL_HOST')}:80"
ENDPOINT_PATH: str = "/system_event"
STAGES = ["normal", "spike", "drift", "dropout"]
WEIGHTS = [0.6, 0.12, 0.09, 0.04]


def generate_normal_data(sensor_id: str) -> Dict[str, Union[str, float]]:
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "sensor_id": sensor_id,
        "temperature": round(random.uniform(10.0, 35.0), 1),
        "pressure": round(random.uniform(1.0, 3.0), 1),
        "flow": round(random.uniform(20.0, 100.0), 1),
    }


def generate_spike(sensor_id: str) -> Dict[str, Union[str, float]]:
    spike_type: str = random.choice(["pressure", "flow"])
    data: Dict[str, Union[str, float]] = generate_normal_data(sensor_id)
    match spike_type:
        case "pressure":
            data["pressure"] = round(random.uniform(4.1, 5.0), 1)
        case "flow":
            data["flow"] = round(random.uniform(121.0, 140.0), 1)
    return data


def generate_drift(sensor_id: str) -> Dict[str, Union[str, float]]:
    data: Dict[str, Union[str, float]] = generate_normal_data(sensor_id)
    data["temperature"] = round(random.uniform(38.1, 40.0), 1)
    return data


def simulate_dropout() -> None:
    # Dropout: No data for >10s, so just sleep for a random duration
    duration: int = random.randint(11, 60)
    time.sleep(duration)


def send_data(data: Dict[str, Union[str, float]]) -> None:
    logger.info(f"\n{data}\n")
    try:
        conn: http.client.HTTPConnection = http.client.HTTPConnection(ENDPOINT_URL)
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        conn.request("POST", ENDPOINT_PATH, json.dumps(data), headers)
        conn.close()
    except (http.client.HTTPException, ConnectionError) as exc:
        logger.error(f"Failed to send data: {exc}")


def main() -> None:
    while True:
        # Fixed to match assignment specification
        # sensor_id: str = "wtf-pipe-1"

        sensor_id: str = f"wtf-pipe-{random.randint(1, 10)}"
        anomaly_type: str = random.choices(STAGES, weights=WEIGHTS, k=1)[0]

        match anomaly_type:
            case "normal":
                send_data(generate_normal_data(sensor_id))
                time.sleep(2)
            case "spike":
                send_data(generate_spike(sensor_id))
                time.sleep(2)
            case "drift":
                send_data(generate_drift(sensor_id))
                time.sleep(2)
            case "dropout":
                simulate_dropout()


if __name__ == "__main__":
    from logs import setup_logging

    setup_logging()
    main()
