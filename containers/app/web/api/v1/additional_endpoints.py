from typing import Any, Dict

from fastapi import APIRouter
from processor.anomaly_detector import SystemEventTracker
from processor.database import SystemEventsDBHandler
from pydantic import BaseModel

router: APIRouter = APIRouter()


class SystemEvent(BaseModel):
    timestamp: str
    sensor_id: str
    temperature: float
    pressure: float
    flow: float


processor: SystemEventTracker = SystemEventTracker()
system_event_store: SystemEventsDBHandler = SystemEventsDBHandler()


@router.post("/system_event", summary="Receive system event")
def system_event(event: SystemEvent) -> Any:
    try:
        event_dict: Dict[str, Any] = event.model_dump()
        processed: Dict[str, Any] = processor.process_event(event_dict)
        return system_event_store.add_event({**event_dict, **processed})
    except Exception as exc:
        return {"error": str(exc)}
