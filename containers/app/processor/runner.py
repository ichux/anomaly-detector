import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from processor.database import AnomalySummary, SystemEventsDBHandler
from processor.summarizer import generate_anomaly_summary

INTERVAL_SECONDS = 30

scheduler = AsyncIOScheduler()
system_event_store = SystemEventsDBHandler()
anomaly_summary_store = AnomalySummary()


logger = logging.getLogger("runner.py")


async def summarize():
    recent = system_event_store.recent_anomalies(INTERVAL_SECONDS)
    if not recent:
        return

    latest_summary = generate_anomaly_summary(recent)
    logger.info(latest_summary)

    window_start = recent[-1]["timestamp"]
    window_end = recent[0]["timestamp"]

    anomaly_summary_store.add_summary(
        window_start, window_end, len(recent), latest_summary
    )


async def main():
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
