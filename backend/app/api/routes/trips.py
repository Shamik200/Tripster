from fastapi import APIRouter, HTTPException
from app.schemas.trip import FinalizeRequest, TripPreferences
from app.services import trip_service

# used to export api endpoints to different modules
router = APIRouter(prefix="/api")

@router.post("/plan")
def plan_trip(preferences: TripPreferences):
    try:
        trip_plan = trip_service.create_trip(preferences)
        return {"success": True, "trip_plan": trip_plan.model_dump()}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

@router.post("/finalize")
def finalize_trip(request: FinalizeRequest):
    try:
        result = trip_service.finalize_trip(request)
        return {"success": True, "finalized_plan": result.model_dump()}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

@router.get("/trips")
def list_trips():
    return {"trips": trip_service.list_trips()}

@router.get("/trips/{trip_id}")
def get_trip(trip_id: str):
    plan = trip_service.get_trip(trip_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Trip not found")
    return plan.model_dump()
