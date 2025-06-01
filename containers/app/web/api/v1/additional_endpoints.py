from fastapi import APIRouter
from processor.anomaly_detector import SystemEventTracker
from processor.database import SystemEventsDBHandler
from pydantic import BaseModel

router = APIRouter()


class SystemEvent(BaseModel):
    timestamp: str
    sensor_id: str
    temperature: float
    pressure: float
    flow: float


processor = SystemEventTracker()
system_event_store = SystemEventsDBHandler()


@router.post("/system_event", summary="Receive system event")
def system_event(event: SystemEvent):
    try:
        event_dict = event.model_dump()
        processed = processor.process_event(event_dict)
        return system_event_store.add_event({**event_dict, **processed})
    except Exception as exc:
        return {"error": str(exc)}
