import json
import os
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.graph import run_trip_planner
from app.agent.llm import planner_llm
from app.core.config import settings
from app.data.repositories import trip_repository
from app.schemas.trip import FinalizeRequest, FinalizedPlan, TripPlan, TripPreferences

def create_trip(preferences: TripPreferences) -> TripPlan:
    plan = run_trip_planner(preferences)
    trip_repository.save_trip_plan(plan)
    return plan

def list_trips() -> List[Dict[str, Any]]:
    return trip_repository.list_trip_plans()

def get_trip(trip_id: str) -> Optional[TripPlan]:
    return trip_repository.get_trip_plan(trip_id)

def finalize_trip(request: FinalizeRequest) -> FinalizedPlan:
    """Send user selections to LLM and receive a polished final plan."""
    plan = request.trip_plan
    currency = plan.currency
    duration_days = plan.duration_days

    # Extract chosen items
    chosen_flight = plan.flights[request.selected_flight_index] if plan.flights else None
    chosen_hotel = plan.hotels[request.selected_hotel_index] if plan.hotels else None

    # Build selected activities list
    selected_days = []
    for day_idx, act_indices in request.selected_activity_indices.items():
        day = plan.itinerary[int(day_idx)]
        acts = [day.activities[i] for i in act_indices if i < len(day.activities)]
        if acts:
            selected_days.append({"day": day.day, "title": day.title, "activities": [a.model_dump() for a in acts]})

    # Calculate totals
    flight_cost = chosen_flight.price or 0.0
    hotel_cost = (chosen_hotel.price_per_night or 0.0) * duration_days
    activity_cost = sum(
        act["estimated_cost"]
        for day in selected_days
        for act in day["activities"]
    )
    total_spent = flight_cost + hotel_cost + activity_cost
    budget_remaining = plan.budget - total_spent

    # Build a compact selection summary for the LLM
    selection_summary = {
        "destination": plan.destination,
        "origin": plan.origin,
        "travel_dates": f"{plan.start_date} to {plan.end_date}",
        "duration_days": duration_days,
        "budget": plan.budget,
        "currency": currency,
        "chosen_flight": chosen_flight.model_dump() if chosen_flight else None,
        "chosen_hotel": chosen_hotel.model_dump() if chosen_hotel else None,
        "selected_itinerary": selected_days,
        "total_spent": round(total_spent, 2),
        "budget_remaining": round(budget_remaining, 2),
    }

    if planner_llm:
        plain_llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.5,
        )
        finalize_llm = plain_llm.with_structured_output(FinalizedPlan)

        finalize_prompt = ChatPromptTemplate.from_template("""
The traveler has finalized their trip selections for {destination}. Based on their chosen flight, hotel, and activities, produce the following:

Trip selection summary:
{summary_json}

Your output must include:
1. narrative_summary: A warm, engaging 2-3 paragraph summary of the entire trip (highlight destination, vibe, key experiences).
2. day_by_day: A flowing day-by-day prose description of what the traveler will do each day based on their selected activities.
3. suggestions: 5-7 smart, specific travel tips for this exact trip to {destination} (e.g. advance bookings, transport, safety, local food).
4. packing_list: A practical packing list of 10-15 items tailored to {destination}, dates, weather, and chosen activities.
5. total_spent: {total_spent} (use this exact value)
6. budget_remaining: {budget_remaining} (use this exact value)

IMPORTANT RULES:
- Be specific to {destination}. Do not give generic advice.
- DO NOT use markdown formatting (like **bold** or *italic*) anywhere in your output. Just use plain text.
""")

        formatted_prompt = finalize_prompt.format(
            destination=plan.destination,
            summary_json=json.dumps(selection_summary, indent=2),
            total_spent=round(total_spent, 2),
            budget_remaining=round(budget_remaining, 2)
        )

        result = finalize_llm.invoke(formatted_prompt)
        result.total_spent = round(total_spent, 2)
        result.budget_remaining = round(budget_remaining, 2)
        return result

    # Fallback if no LLM configured
    return FinalizedPlan(
        narrative_summary=f"Your {duration_days}-day trip to {plan.destination} has been finalized!",
        day_by_day="\n".join(
            f"Day {d['day']} ({d['title']}): " + ", ".join(a["title"] for a in d["activities"])
            for d in selected_days
        ),
        suggestions=plan.safety_tips + ["Check local weather before packing.", "Book popular attractions in advance."],
        packing_list=plan.packing_tips + ["Travel documents", "Travel insurance", "Local currency cash"],
        total_spent=round(total_spent, 2),
        budget_remaining=round(budget_remaining, 2),
    )
