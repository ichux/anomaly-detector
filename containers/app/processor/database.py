import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union

import typesense
from typesense.exceptions import ObjectNotFound

ts_client = typesense.Client(
    {
        "nodes": [
            {
                # pyright: ignore
                "host": os.getenv("TYPESENSE_HOST"),
                "port": os.getenv("TYPESENSE_PORT"),
                "protocol": os.getenv("TYPESENSE_PROTOCOL"),
            }
        ],
        "api_key": os.getenv("TYPESENSE_API"),
        "connection_timeout_seconds": 30,
    }
)


def iso_from_int(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def int_from_iso(iso_str: str) -> int:
    dt = datetime.fromisoformat(iso_str.rstrip("Z"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


class SystemEventsDBHandler:
    def __init__(self) -> None:
        self.collection_name: str = "system_events"
        self.ts_client = ts_client
        self.create_collection()

    def create_collection(self):
        if not self.get_collection(collection_name=self.collection_name):
            self.ts_client.collections.create(
                {
                    "name": self.collection_name,
                    "enable_nested_fields": True,
                    "fields": [
                        {"name": "timestamp", "type": "int64"},
                        {"name": "sensor_id", "type": "string"},
                        {"name": "temperature", "type": "float"},
                        {"name": "pressure", "type": "float"},
                        {"name": "flow", "type": "float"},
                        {"name": "is_anomaly", "type": "bool"},
                        {"name": "anomalies", "type": "object[]"},
                    ],
                }
            )
        return self.ts_client.collections[self.collection_name].retrieve()

    def delete_collection(self, collection_name: Union[str, None] = None):
        try:
            return self.ts_client.collections[
                collection_name or self.collection_name
            ].delete()
        except ObjectNotFound:
            return False

    def get_collection(self, collection_name: Union[str, None] = None):
        try:
            return self.ts_client.collections[
                collection_name or self.collection_name
            ].retrieve()
        except ObjectNotFound:
            return False

    def add_event(self, event: dict):
        iso_ts = event.get("timestamp")
        if iso_ts:
            event["timestamp"] = int_from_iso(iso_ts)
            return self.ts_client.collections[self.collection_name].documents.create(
                event
            )
        return {"message": "No timestamp provided"}

    def recent_anomalies(self, duration: int | None) -> List[dict]:
        cutoff_ms = int(
            (
                datetime.now(timezone.utc) - timedelta(seconds=duration or 24 * 60 * 60)
            ).timestamp()
            * 1000
        )

        base_search = {
            "q": "*",
            "query_by": "anomalies",
            "filter_by": f"is_anomaly:true && timestamp:>={cutoff_ms}",
            "sort_by": "timestamp:desc",
            "per_page": 250,
        }

        all_docs = []
        page = 1

        while True:
            try:
                # pyright: ignore
                resp = self.ts_client.collections[
                    self.collection_name
                ].documents.search({**base_search, "page": page})
            except ObjectNotFound:
                return []

            hits = resp.get("hits", [])
            docs = [hit["document"] for hit in hits]
            if not docs:
                break

            # Convert timestamp on each document
            for doc in docs:
                if isinstance(doc.get("timestamp"), int):
                    # pyright: ignore
                    doc["timestamp"] = iso_from_int(doc["timestamp"])

            all_docs.extend(docs)
            if len(docs) < base_search["per_page"]:
                break
            page += 1

        return all_docs


class AnomalySummary:
    def __init__(self) -> None:
        self.collection_name = "anomaly_summary"
        self.ts = ts_client
        self.create_collection()

    def create_collection(self):
        if not self.get_collection():
            self.ts.collections.create(
                {
                    "name": self.collection_name,
                    "enable_nested_fields": True,
                    "fields": [
                        {"name": "window_start_ms", "type": "int64"},
                        {"name": "window_end_ms", "type": "int64"},
                        {"name": "count", "type": "int32"},
                        {"name": "summary", "type": "string"},
                    ],
                }
            )

    def get_collection(self):
        try:
            return self.ts.collections[self.collection_name].retrieve()
        except (Exception,):
            return False

    def add_summary(
        self,
        window_start: str,
        window_end: str,
        count: int,
        summary: str,
    ):
        return self.ts.collections[self.collection_name].documents.create(
            {
                "window_start_ms": int_from_iso(window_start),
                "window_end_ms": int_from_iso(window_end),
                "count": count,
                "summary": summary,
            }
        )

    def recent_summaries(
        self,
        limit: Optional[int] = None,
    ) -> List[dict]:
        """
        Return the `limit` most recent summary docs, sorted by window_start_ms descending.
        If `limit` is None, defaults to 10.
        """
        # default to 10 if caller passed None or 0/False-y value
        limit = limit or 10

        # enforce Typesense's max per_page (e.g. 250) but never request more than we need
        per_page = min(limit, 250)

        base_search = {
            "q": "*",
            "query_by": "summary",
            "sort_by": "window_start_ms:desc",
            "per_page": per_page,
        }

        collected: List[dict] = []
        page = 1

        while len(collected) < limit:
            try:
                resp = self.ts.collections[self.collection_name].documents.search(
                    {**base_search, "page": page}
                )
            except (Exception,):
                # e.g. collection not found
                return []

            hits = resp.get("hits", [])
            docs = [h["document"] for h in hits]
            if not docs:
                break

            for d in docs:
                # convert ms fields into ISO strings
                if isinstance(d.get("window_start_ms"), int):
                    d["window_start"] = iso_from_int(d.pop("window_start_ms"))
                if isinstance(d.get("window_end_ms"), int):
                    d["window_end"] = iso_from_int(d.pop("window_end_ms"))

                collected.append(d)
                if len(collected) >= limit:
                    break

            # no more pages?
            if len(docs) < per_page:
                break

            page += 1

        return collected[:limit]
