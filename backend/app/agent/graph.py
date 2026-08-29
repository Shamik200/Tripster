from langgraph.graph import END, START, StateGraph
from app.agent.nodes import execute_mcp_tools_node, generate_plan_node, research_trip_node, retrieve_rag_node, validate_plan_node
from app.agent.state import TripState
from app.schemas.trip import TripPlan, TripPreferences

workflow = StateGraph(TripState)
workflow.add_node("rag_retrieval", retrieve_rag_node)
workflow.add_node("mcp_tools", execute_mcp_tools_node)
workflow.add_node("web_research", research_trip_node)
workflow.add_node("generate_plan", generate_plan_node)
workflow.add_node("validate_plan", validate_plan_node)
workflow.add_edge(START, "rag_retrieval")
workflow.add_edge("rag_retrieval", "mcp_tools")
workflow.add_edge("mcp_tools", "web_research")
workflow.add_edge("web_research", "generate_plan")
workflow.add_edge("generate_plan", "validate_plan")
workflow.add_edge("validate_plan", END)
trip_graph = workflow.compile()

def run_trip_planner(preferences: TripPreferences) -> TripPlan:
    initial_state: TripState = {
        "preferences": preferences.model_dump(),
        "rag_context": None,
            "previous_trip_context": None,
        "mcp_data": None,
        "research_data": None,
        "final_plan": None,
    }
    result = trip_graph.invoke(initial_state)
    return TripPlan.model_validate(result["final_plan"])
