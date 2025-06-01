import asyncio
import json
import logging
from typing import Any, Dict, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from processor.database import AnomalySummary, SystemEventsDBHandler
from processor.summarizer import generate_anomaly_summary

INTERVAL_SECONDS: int = 30

scheduler: AsyncIOScheduler = AsyncIOScheduler()
system_event_store: SystemEventsDBHandler = SystemEventsDBHandler()
anomaly_summary_store: AnomalySummary = AnomalySummary()

logger = logging.getLogger("runner.py")


def group_anomalies(intake: List[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, Any] = {"timestamp": None, "stop_timestamp": None}
    all_anomaly_timestamps: List[str] = []

    for entry in intake:
        sensor_id: str = entry.get("sensor_id")  # type: ignore
        anomalies: List[Dict[str, Any]] = entry.get("anomalies", [])  # type: ignore

        # Initialize the list for the sensor if not already present
        if sensor_id not in grouped:
            grouped[sensor_id] = []  # type: ignore

        # Add anomalies for this sensor
        grouped[sensor_id].extend(anomalies)  # type: ignore

        # Collect timestamps for range calculation
        for anomaly in anomalies:
            ts: str = anomaly.get("timestamp")  # type: ignore
            if ts:
                all_anomaly_timestamps.append(ts)

    if all_anomaly_timestamps:
        grouped["timestamp"] = min(all_anomaly_timestamps)
        grouped["stop_timestamp"] = max(all_anomaly_timestamps)

    return grouped


async def summarize() -> None:
    recent: List[Dict[str, Any]] = system_event_store.recent_unprocessed_anomalies()

    if not recent:
        return

    to_model: Dict[str, Any] = group_anomalies(recent)
    latest_summary: str = generate_anomaly_summary(to_model)

    window_start: str = recent[-1]["timestamp"]  # type: ignore
    window_end: str = recent[0]["timestamp"]  # type: ignore

    anomaly_summary_store.add_summary(
        window_start, window_end, len(recent), latest_summary
    )

    system_event_store.set_process(recent)
    # logger.info(f"\n{json.dumps(to_model, indent=2)}\n{latest_summary}\n\n")


async def main() -> None:
    scheduler.add_job(
        summarize,
        trigger=IntervalTrigger(seconds=INTERVAL_SECONDS),
        id="batch-summary-job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started, running every {INTERVAL_SECONDS}s")

    try:
        while True:
            # Keep the loop alive
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    from logs import setup_logging

    setup_logging()
    asyncio.run(main())
