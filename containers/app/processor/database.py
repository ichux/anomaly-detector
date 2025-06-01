import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import typesense
from typesense.exceptions import ObjectNotFound

logger = logging.getLogger("database.py")

ts_client: typesense.Client = typesense.Client(
    {
        "nodes": [
            {
                "host": os.getenv("TYPESENSE_HOST"),  # type: ignore
                "port": os.getenv("TYPESENSE_PORT"),  # type: ignore
                "protocol": os.getenv("TYPESENSE_PROTOCOL"),  # type: ignore
            }
        ],
        "api_key": os.getenv("TYPESENSE_API"),  # type: ignore
        "connection_timeout_seconds": 30,
    }
)


def iso_from_int(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def int_from_iso(iso_str: str) -> int:
    dt: datetime = datetime.fromisoformat(iso_str.rstrip("Z"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


class SystemEventsDBHandler:
    def __init__(self) -> None:
        self.collection_name: str = "system_events"
        self.ts_client: typesense.Client = ts_client

    def create_collection(self) -> Any:
        if not self.get_collection():
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
                        {"name": "processed", "type": "bool"},
                    ],
                }
            )
        return self.ts_client.collections[self.collection_name].retrieve()

    def delete_collection(
        self, collection_name: Optional[str] = None
    ) -> Union[bool, Any]:
        try:
            return self.ts_client.collections[
                collection_name or self.collection_name
            ].delete()
        except ObjectNotFound:
            return False

    def get_collection(self, collection_name: Optional[str] = None) -> Union[bool, Any]:
        try:
            return self.ts_client.collections[
                collection_name or self.collection_name
            ].retrieve()
        except ObjectNotFound:
            return False

    def add_event(self, event: Dict[str, Any]) -> Any:
        iso_ts: Optional[str] = event.get("timestamp")
        if iso_ts:
            event["timestamp"] = int_from_iso(iso_ts)  # type: ignore
            event["processed"] = False
            return self.ts_client.collections[self.collection_name].documents.create(
                event  # type: ignore
            )
        return {"message": "No timestamp provided"}

    def set_process(self, events: List[Dict[str, Any]]) -> None:
        for event in events:
            event["timestamp"] = int_from_iso(event.get("timestamp"))  # type: ignore
            event["processed"] = True
            self.ts_client.collections[self.collection_name].documents.upsert(event)  # type: ignore

    def _search_anomalies(
        self, filter_by: str, sort_by: str, duration: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Internal helper to search anomalies with specified filters and sorting.

        Args:
            filter_by: Typesense filter_by string.
            sort_by: Typesense sort_by string.
            duration: If provided, used to compute cutoff for timestamp filtering.

        Returns:
            List of documents with anomaly data (timestamps converted to ISO).
        """
        # If duration is given, compute cutoff and extend filter
        if duration is not None:
            timed: datetime = datetime.now(timezone.utc) - timedelta(seconds=duration)
            cutoff_ms: int = int(timed.timestamp() * 1000)
            # Append timestamp filter for duration-based methods
            filter_by = f"{filter_by} && timestamp:>={cutoff_ms}"

        base_search: Dict[str, Any] = {
            "q": "*",
            "query_by": "anomalies",
            "filter_by": filter_by,
            "sort_by": sort_by,
            "per_page": 250,
        }

        all_docs: List[Dict[str, Any]] = []
        page: int = 1

        while True:
            try:
                resp: Dict[str, Any] = self.ts_client.collections[
                    self.collection_name
                ].documents.search(
                    {**base_search, "page": page}
                )  # type: ignore
            except ObjectNotFound:
                return []

            hits: List[Dict[str, Any]] = resp.get("hits", [])
            docs: List[Dict[str, Any]] = [hit["document"] for hit in hits]
            if not docs:
                break

            # Convert timestamps to ISO format
            for doc in docs:
                if isinstance(doc.get("timestamp"), int):
                    doc["timestamp"] = iso_from_int(doc["timestamp"])  # type: ignore

            all_docs.extend(docs)
            if len(docs) < base_search["per_page"]:
                break
            page += 1

        return all_docs

    def recent_anomalies(self, duration: Optional[int]) -> List[Dict[str, Any]]:
        """
        Return anomalies in the past `duration` seconds, sorted by most recent first.
        """
        filter_by = "is_anomaly:true"
        sort_by = "timestamp:desc"
        return self._search_anomalies(
            filter_by=filter_by, sort_by=sort_by, duration=duration
        )

    def recent_unprocessed_anomalies(self) -> List[Dict[str, Any]]:
        """
        Return all unprocessed anomalies, sorted by oldest first.
        """
        filter_by = "is_anomaly:true && processed:false"
        sort_by = "timestamp:asc"
        return self._search_anomalies(filter_by=filter_by, sort_by=sort_by)


class AnomalySummary:
    def __init__(self) -> None:
        self.collection_name: str = "anomaly_summary"
        self.ts: typesense.Client = ts_client

    def create_collection(self) -> Any:
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

    def get_collection(self) -> Union[bool, Any]:
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
    ) -> Any:
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
    ) -> List[Dict[str, Any]]:
        """
        Return the `limit` most recent summary docs, sorted by window_start_ms descending.
        If `limit` is None, defaults to 10.
        """
        limit = limit or 10

        per_page: int = min(limit, 250)

        base_search: Dict[str, Any] = {
            "q": "*",
            "query_by": "summary",
            "sort_by": "window_start_ms:desc",
            "per_page": per_page,
        }

        collected: List[Dict[str, Any]] = []
        page: int = 1

        while len(collected) < limit:
            try:
                resp: Dict[str, Any] = self.ts.collections[
                    self.collection_name
                ].documents.search(
                    {**base_search, "page": page}  # type: ignore
                )
            except (Exception,):
                return []

            hits: List[Dict[str, Any]] = resp.get("hits", [])
            docs: List[Dict[str, Any]] = [h["document"] for h in hits]
            if not docs:
                break

            for d in docs:
                if isinstance(d.get("window_start_ms"), int):
                    d["window_start"] = iso_from_int(d.pop("window_start_ms"))  # type: ignore
                if isinstance(d.get("window_end_ms"), int):
                    d["window_end"] = iso_from_int(d.pop("window_end_ms"))  # type: ignore

                collected.append(d)
                if len(collected) >= limit:
                    break

            if len(docs) < per_page:
                break

            page += 1

        return collected[:limit]
