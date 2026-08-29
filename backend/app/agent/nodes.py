import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.data.database import read_mcp_cache, write_mcp_cache
from app.agent.llm import planner_llm, research_llm
from app.agent.state import TripState
from mcp_servers.travel_server import search_flights_tool
from app.rag.retriever import retrieve_destination_context, retrieve_previous_trip_context
from app.schemas.trip import Activity, FlightOption, HotelOption, ItineraryDay, TravelResearch, TripPlan

def _get_duration(preferences: Dict[str, Any]) -> int:
    start_date_str = preferences.get("start_date")
    end_date_str = preferences.get("end_date")
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            return max(1, (end_date - start_date).days + 1)
        except ValueError:
            pass
    return int(preferences.get("duration_days", 5))

def retrieve_rag_node(state: TripState) -> Dict[str, Any]:
    preferences = state["preferences"]
    destination = preferences.get("destination", "Tokyo")
    query = json.dumps(preferences, sort_keys=True)
    return {
        "rag_context": retrieve_destination_context(destination),
        "previous_trip_context": retrieve_previous_trip_context(query),
    }

def execute_mcp_tools_node(state: TripState) -> Dict[str, Any]:
    preferences = state["preferences"]
    destination = preferences.get("destination", "Tokyo")
    origin = preferences.get("origin", "New York")
    budget = float(preferences.get("budget", 2000.0))
    duration = _get_duration(preferences)
    interests = ", ".join(preferences.get("interests", ["culture"]))
    cache_key = json.dumps({"destination": destination, "origin": origin,
                            "budget": budget, "duration": duration,
                            "interests": interests}, sort_keys=True)
    cache = read_mcp_cache()
    cached_entry = cache.get(cache_key)
    if cached_entry and time.time() - cached_entry.get("created_at", 0) < settings.MCP_CACHE_TTL_SECONDS:
        return {"mcp_data": cached_entry["data"]}

    mcp_data = {
        "flights": search_flights_tool(origin, destination, budget),
    }
    cache[cache_key] = {"created_at": time.time(), "data": mcp_data}
    write_mcp_cache(cache)
    return {"mcp_data": mcp_data}

def research_trip_node(state: TripState) -> Dict[str, Any]:
    if not research_llm:
        return {"research_data": {}}

    preferences = state["preferences"]
    destination = preferences.get("destination", "Tokyo")
    budget = float(preferences.get("budget", 2000.0))
    currency = preferences.get("currency", "USD")
    duration = _get_duration(preferences)

    research_prompt = ChatPromptTemplate.from_template("""
Research current travel information for this request:
Destination: {destination}
Trip Duration: {duration} days
Total Budget: {budget} {currency}
User Preferences JSON:
{preferences_json}

INSTRUCTIONS:
1. Find realistic activities and hotels that fit {destination}, user interests, budget ({budget} {currency}), and trip duration ({duration} days).
2. Find current weather information.
3. CURRENCY INSTRUCTION: All hotel prices (price_per_night) and activity estimated costs MUST be expressed in {currency}.
   - If {currency} is INR (Indian Rupee), realistic hotel prices in Europe/USA are typically 6,000 to 25,000 INR per night. Do NOT give Euro/USD numbers (like 80 or 150) labeled as INR!
   - If {currency} is USD, hotel prices are typically $80 to $350 USD per night.
   - If {currency} is EUR, hotel prices are typically 70 to 300 EUR per night.
   - If {currency} is JPY, hotel prices are typically 10,000 to 35,000 JPY per night.
4. Mark prices as estimates. Return data strictly matching the TravelResearch schema.
""")

    formatted_prompt = research_prompt.format(
        destination=destination,
        duration=duration,
        budget=budget,
        currency=currency,
        preferences_json=json.dumps(preferences, indent=2)
    )

    research = research_llm.invoke(formatted_prompt)
    return {"research_data": research.model_dump()}

def generate_plan_node(state: TripState) -> Dict[str, Any]:
    preferences = state["preferences"]
    rag = state.get("rag_context", "")
    previous_trip_context = state.get("previous_trip_context", "")
    mcp_data = state.get("mcp_data") or {}
    research_data = state.get("research_data") or {}
    destination = preferences.get("destination", "Tokyo")
    origin = preferences.get("origin", "New York")
    budget = float(preferences.get("budget", 2000.0))
    currency = preferences.get("currency", "USD")
    start_date = preferences.get("start_date", datetime.utcnow().strftime("%Y-%m-%d"))
    end_date = preferences.get("end_date", datetime.utcnow().strftime("%Y-%m-%d"))
    duration = _get_duration(preferences)

    if planner_llm:
        planner_prompt = ChatPromptTemplate.from_template("""
Create one complete travel plan using the supplied data.

User preferences:
{preferences_json}

Destination knowledge from RAG:
{rag}

Relevant previous trip plans:
{previous_trip_context}

Retrieved MCP flight options:
{mcp_data_json}

Web-researched activities, hotels, and weather:
{research_data_json}

CRITICAL REQUIREMENTS:
1. CURRENCY ACCURACY & REALISM:
   - Currency requested is {currency}. All prices (hotel price_per_night, activity estimated_cost) MUST be in {currency}.
   - Do NOT mix up currencies. If currency is INR, hotels should be 5,000-25,000 INR per night (NOT 80 INR!).

2. ACTIVITY QUALITY:
   - Activities must be real, selectable experiences only (museums, restaurants, cultural tours, shopping).
   - Do NOT include logistical steps: hotel check-in, check-out, airport transfers, arrive at destination, departure.

3. BUDGET SCALING:
   - Budget: {budget} {currency}. Scale recommendations to match the travel style ({travel_style}).
   - "budget" style: affordable accommodations and local dining.
   - "balanced" style: 3-4 star hotels and popular attractions.
   - "luxury" style: 4-5 star hotels and premium experiences.

4. ITINERARY STRUCTURE:
   - Create exactly {duration} itinerary days.
   - Each day must have 3 to 5 selectable activities.

5. FORMATTING:
   - Absolutely NO markdown formatting (like **bold** or *italic*) anywhere in strings. Use clean plain text.

Return a complete TripPlan object.
""")

        formatted_prompt = planner_prompt.format(
            preferences_json=json.dumps(preferences, indent=2),
            rag=rag,
            previous_trip_context=previous_trip_context,
            mcp_data_json=json.dumps(mcp_data, indent=2),
            research_data_json=json.dumps(research_data, indent=2),
            currency=currency,
            budget=budget,
            travel_style=preferences.get("travel_style", "balanced"),
            duration=duration
        )

        generated_plan = planner_llm.invoke(formatted_prompt)
        generated_plan.start_date = start_date
        generated_plan.end_date = end_date
        generated_plan.duration_days = duration
        generated_plan.flights = [FlightOption.model_validate(flight) for flight in mcp_data.get("flights", [])]
        generated_plan.hotels = [HotelOption.model_validate(hotel) for hotel in research_data.get("hotels", [])]
        generated_plan.weather = research_data.get("weather")
        generated_plan.mcp_data = mcp_data
        generated_plan.research_data = research_data
        return {"final_plan": generated_plan.model_dump()}

    activities = [Activity.model_validate(activity) for activity in research_data.get("activities", [])]
    itinerary_days = [ItineraryDay(day=day, title=f"Day {day}: Exploring {destination}", activities=activities)
                      for day in range(1, duration + 1)]
    trip_plan = TripPlan(
        id=str(uuid.uuid4()), destination=destination, origin=origin, budget=budget,
        currency=currency, start_date=start_date, end_date=end_date, duration_days=duration,
        summary=f"A complete {duration}-day trip to {destination} covering top sights and local experiences.",
        flights=[FlightOption.model_validate(flight) for flight in mcp_data.get("flights", [])],
        hotels=[HotelOption.model_validate(hotel) for hotel in research_data.get("hotels", [])],
        itinerary=itinerary_days,
        packing_tips=["Comfortable walking shoes", "Universal travel adapter", "Weather-appropriate layers"],
        safety_tips=["Keep digital copies of passport", "Use standard licensed transport"],
        rag_context=rag,
        weather=research_data.get("weather"),
        mcp_data=mcp_data,
        research_data=research_data,
    )
    return {"final_plan": json.loads(trip_plan.model_dump_json())}

def validate_plan_node(state: TripState) -> Dict[str, Any]:
    plan = TripPlan.model_validate(state["final_plan"])
    expected_days = _get_duration(state["preferences"])
    if len(plan.itinerary) != expected_days:
        raise ValueError(f"Planner returned {len(plan.itinerary)} days; expected {expected_days}")
    return {"final_plan": plan.model_dump()}
