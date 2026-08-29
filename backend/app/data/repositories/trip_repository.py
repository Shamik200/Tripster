import json
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.data.database import read_database, write_database
from app.data.vector_store import vector_store
from app.schemas.trip import TripPlan

def save_trip_plan(trip_plan: TripPlan) -> None:
    serialized_plan = json.loads(trip_plan.model_dump_json())
    data = read_database()
    data["trips"][trip_plan.id] = serialized_plan
    write_database(data)
    vector_store.add_trip_plan(
        trip_plan.id,
        json.dumps(serialized_plan, ensure_ascii=False),
        {"destination": trip_plan.destination, "created_at": trip_plan.created_at},
    )

def get_trip_plan(trip_id: str) -> Optional[TripPlan]:
    data = read_database()
    try:
        trip_dict = data.get("trips", {}).get(trip_id)
        if trip_dict:
            return TripPlan.model_validate(trip_dict)
    except Exception:
        pass
    return None

def list_trip_plans() -> List[Dict[str, Any]]:
    data = read_database()
    try:
        trips = list(data.get("trips", {}).values())
        return sorted(trips, key=lambda item: item.get("created_at", ""), reverse=True)
    except Exception:
        return []
