from fastapi import APIRouter
from processor.database import SystemEventsDBHandler
from web.utils import SystemEventTracker

router = APIRouter()


processor = SystemEventTracker()
system_event_store = SystemEventsDBHandler()


@router.post("/system_event", summary="Receive system event")
def system_event(event: dict):
    try:
        return system_event_store.add_event({**event, **processor.process_event(event)})
    except (Exception,) as exc:
        return {"error": str(exc)}
