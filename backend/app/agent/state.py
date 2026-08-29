from typing import Any, Dict, Optional, TypedDict

class TripState(TypedDict):
    preferences: Dict[str, Any]
    rag_context: Optional[str]
    previous_trip_context: Optional[str]
    mcp_data: Optional[Dict[str, Any]]
    research_data: Optional[Dict[str, Any]]
    final_plan: Optional[Dict[str, Any]]
