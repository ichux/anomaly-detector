#!/bin/sh

set -e

python3 <<END
import logging
import time
from typing import Callable

from processor.database import AnomalySummary, SystemEventsDBHandler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def wait_for_collection(
    check_fn: Callable[[], bool], name: str, timeout: int = 3, interval: float = 1.0
) -> bool:
    """Waits for a collection to become available.

    Args:
        check_fn: Function that returns a boolean indicating if the collection is ready.
        name: Name of the collection (for logging).
        timeout: Max time to wait in seconds.
        interval: Time between checks in seconds.

    Returns:
        True if the collection becomes available, False if timed out.
    """
    logging.info(f"Waiting for collection: {name}")
    start_time = time.time()

    while not check_fn():
        if time.time() - start_time > timeout:
            logging.error(f"Timeout while waiting for collection: {name}")
            return False
        time.sleep(interval)
        logging.debug(f"Still waiting: {name}")

    logging.info(f"Collection ready: {name}")
    return True


wait_for_collection(lambda: AnomalySummary().get_collection(), "anomaly_summary")
wait_for_collection(lambda: SystemEventsDBHandler().get_collection(), "system_events")

END

uvicorn web.main:app --host 0.0.0.0 --port 80 --reload
