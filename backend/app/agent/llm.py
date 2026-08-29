import os
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.schemas.trip import TravelResearch, TripPlan

# Re-export so other modules can import ChatGoogleGenerativeAI from here
__all__ = ["ChatGoogleGenerativeAI", "planner_llm", "research_llm"]


def create_planner() -> Optional[object]:
	api_key = settings.GEMINI_API_KEY
	if not api_key:
		return None

	model = ChatGoogleGenerativeAI(
		model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
		google_api_key=api_key,
		temperature=0.2,
	)
	return model.with_structured_output(TripPlan)

def create_researcher() -> Optional[object]:
	if not settings.GEMINI_API_KEY:
		return None
	model = ChatGoogleGenerativeAI(
		model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
		google_api_key=settings.GEMINI_API_KEY,
		temperature=0.1,
		model_kwargs={"tools": [{"google_search": {}}]},
	)
	return model.with_structured_output(TravelResearch)


research_llm = create_researcher()

planner_llm = create_planner()
