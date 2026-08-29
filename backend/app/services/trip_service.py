import json
import os
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.graph import run_trip_planner
from app.agent.llm import planner_llm
from app.core.config import settings
from app.data.repositories import trip_repository
from app.schemas.trip import FinalizeLLMOutput, FinalizeRequest, FinalizedPlan, TripPlan, TripPreferences

def create_trip(preferences: TripPreferences) -> TripPlan:
    plan = run_trip_planner(preferences)
    trip_repository.save_trip_plan(plan)
    return plan

def list_trips() -> List[Dict[str, Any]]:
    return trip_repository.list_trip_plans()

def get_trip(trip_id: str) -> Optional[TripPlan]:
    return trip_repository.get_trip_plan(trip_id)

def _compact_flight(flight) -> Optional[Dict[str, Any]]:
    if not flight:
        return None
    return {
        "airline": flight.airline,
        "origin": flight.origin,
        "destination": flight.destination,
        "price": flight.price,
        "duration": flight.duration,
        "is_direct": flight.is_direct,
    }


def _compact_hotel(hotel) -> Optional[Dict[str, Any]]:
    if not hotel:
        return None
    return {
        "name": hotel.name,
        "location": hotel.location,
        "price_per_night": hotel.price_per_night,
        "rating": hotel.rating,
    }


def _local_finalized_plan(plan: TripPlan, selected_days: List[Dict[str, Any]], total_spent: float, budget_remaining: float) -> FinalizedPlan:
    duration_days = plan.duration_days
    return FinalizedPlan(
        narrative_summary=f"Your {duration_days}-day trip to {plan.destination} has been finalized.",
        day_by_day="\n".join(
            f"Day {d['day']} ({d['title']}): " + ", ".join(a["title"] for a in d["activities"])
            for d in selected_days
        ) or "No activities selected.",
        suggestions=(plan.safety_tips or [])[:5] or [
            "Book popular attractions in advance.",
            "Check local weather before packing.",
            "Keep a digital copy of your documents.",
        ],
        packing_list=(plan.packing_tips or [])[:10] or [
            "Travel documents",
            "Travel insurance",
            "Comfortable walking shoes",
            "Weather-appropriate clothing",
            "Phone charger",
            "Reusable water bottle",
            "Local currency cash",
        ],
        total_spent=round(total_spent, 2),
        budget_remaining=round(budget_remaining, 2),
    )


def _from_llm_output(output: FinalizeLLMOutput, total_spent: float, budget_remaining: float) -> FinalizedPlan:
    return FinalizedPlan(
        narrative_summary=output.narrative_summary.replace("\t", " ").strip(),
        day_by_day="\n".join(s.replace("\t", " ").strip() for s in output.day_summaries if s and s.strip()),
        suggestions=[s.strip() for s in output.suggestions if s and s.strip()],
        packing_list=[s.strip() for s in output.packing_list if s and s.strip()],
        total_spent=round(total_spent, 2),
        budget_remaining=round(budget_remaining, 2),
    )


def finalize_trip(request: FinalizeRequest) -> FinalizedPlan:
    """Send user selections to LLM and receive a polished final plan."""
    plan = request.trip_plan
    currency = plan.currency
    duration_days = plan.duration_days

    chosen_flight = plan.flights[request.selected_flight_index] if plan.flights else None
    chosen_hotel = plan.hotels[request.selected_hotel_index] if plan.hotels else None

    selected_days = []
    for day_idx, act_indices in request.selected_activity_indices.items():
        day = plan.itinerary[int(day_idx)]
        acts = [day.activities[i] for i in act_indices if i < len(day.activities)]
        if acts:
            selected_days.append({
                "day": day.day,
                "title": day.title,
                "activities": [
                    {"title": a.title, "time_of_day": a.time_of_day, "estimated_cost": a.estimated_cost}
                    for a in acts
                ],
            })

    flight_cost = chosen_flight.price or 0.0
    hotel_cost = (chosen_hotel.price_per_night or 0.0) * duration_days
    activity_cost = sum(
        act["estimated_cost"]
        for day in selected_days
        for act in day["activities"]
    )
    total_spent = flight_cost + hotel_cost + activity_cost
    budget_remaining = plan.budget - total_spent

    fallback = _local_finalized_plan(plan, selected_days, total_spent, budget_remaining)

    if not planner_llm:
        return fallback

    selection_summary = {
        "destination": plan.destination,
        "origin": plan.origin,
        "travel_dates": f"{plan.start_date} to {plan.end_date}",
        "duration_days": duration_days,
        "currency": currency,
        "chosen_flight": _compact_flight(chosen_flight),
        "chosen_hotel": _compact_hotel(chosen_hotel),
        "selected_itinerary": selected_days,
    }

    plain_llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.3,
        max_output_tokens=2048,
    )
    try:
        finalize_llm = plain_llm.with_structured_output(FinalizeLLMOutput, method="json_schema")
    except Exception:
        finalize_llm = plain_llm.with_structured_output(FinalizeLLMOutput)

    finalize_prompt = ChatPromptTemplate.from_template("""
Write a short final trip write-up for {destination}. Keep every field brief. Plain text only.

Selections:
{summary_json}

Fill:
- narrative_summary: two short paragraphs, under 250 words
- day_summaries: one sentence per day in the itinerary ({duration_days} items)
- suggestions: 5 specific tips for {destination}
- packing_list: 10 packing items for this trip
""")

    formatted_prompt = finalize_prompt.format(
        destination=plan.destination,
        summary_json=json.dumps(selection_summary),
        duration_days=duration_days,
    )

    try:
        output = finalize_llm.invoke(formatted_prompt)
        return _from_llm_output(output, total_spent, budget_remaining)
    except Exception:
        return fallback
