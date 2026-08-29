from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class TripPreferences(BaseModel):
    destination: str = Field(..., description="Target destination city")
    origin: Optional[str] = Field("New York", description="Origin city")
    budget: float = Field(2000.0, description="Total budget limit")
    currency: str = Field("USD", description="Currency symbol/code")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    interests: List[str] = Field(default_factory=lambda: ["sightseeing", "food"], description="Interests")
    travel_style: str = Field("balanced", description="Budget, balanced, or luxury")

class FlightOption(BaseModel):
    airline: str
    origin: str
    destination: str
    price: Optional[float] = None
    duration: str
    is_direct: Optional[bool] = None

class HotelOption(BaseModel):
    name: str
    location: str
    price_per_night: float
    rating: float
    amenities: List[str] = []

class Activity(BaseModel):
    title: str
    description: str
    time_of_day: str
    estimated_cost: float = 0.0

class ItineraryDay(BaseModel):
    day: int
    title: str
    activities: List[Activity] = []

class WeatherInfo(BaseModel):
    temperature_celsius: Optional[float] = None
    conditions: str
    recommendation: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_at: Optional[str] = None

class ResearchedActivity(Activity):
    price_source: Optional[str] = None
    is_estimate: bool = True
    duration_minutes: Optional[int] = None
    opening_hours: Optional[str] = None
    source_url: Optional[str] = None

class TravelResearch(BaseModel):
    weather: Optional[WeatherInfo] = None
    activities: List[ResearchedActivity] = []
    hotels: List[HotelOption] = []
    sources: List[str] = []

class TripPlan(BaseModel):
    id: str
    destination: str
    origin: str
    budget: float
    currency: str
    start_date: str
    end_date: str
    duration_days: int
    summary: str
    flights: List[FlightOption] = []
    hotels: List[HotelOption] = []
    itinerary: List[ItineraryDay] = []
    packing_tips: List[str] = []
    safety_tips: List[str] = []
    rag_context: Optional[str] = None
    weather: Optional[Dict[str, Any]] = None
    mcp_data: Dict[str, Any] = Field(default_factory=dict)
    research_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Finalization schemas ──────────────────────────────────────────────────────

class FinalizeRequest(BaseModel):
    """Sent by the frontend when the user clicks 'Finalize Plan'."""
    trip_plan: TripPlan
    selected_flight_index: int
    selected_hotel_index: int
    # keys are day indices (0-based), values are lists of activity indices
    selected_activity_indices: Dict[str, List[int]] = Field(default_factory=dict)

class FinalizedPlan(BaseModel):
    """Returned by the LLM after finalizing the user's selections."""
    narrative_summary: str = Field(..., description="A polished 2-3 paragraph narrative of the entire trip")
    day_by_day: str = Field(..., description="Day-by-day prose description of selected activities")
    suggestions: List[str] = Field(default_factory=list, description="Smart travel tips and suggestions")
    packing_list: List[str] = Field(default_factory=list, description="Destination/activity-aware packing list")
    total_spent: float = Field(..., description="Total estimated cost of the chosen selections")
    budget_remaining: float = Field(..., description="Budget left after selections")
