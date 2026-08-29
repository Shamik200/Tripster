"""
evaluators.py
-------------
Simple evaluator functions for LangSmith.

LangSmith calls each evaluator with:
  - run:    the Run object (has .inputs and .outputs from your pipeline)
  - example: the Example object (has .inputs and .outputs = our "expected" dict)

Each evaluator returns a dict like: {"key": "score_name", "score": 0 or 1}
  score=1  means PASS
  score=0  means FAIL
"""


def check_itinerary_days(run, example):
    """The plan must have at least the right number of itinerary days."""
    expected_min = example.outputs.get("min_days", 1)
    plan = run.outputs.get("final_plan", {})
    itinerary = plan.get("itinerary", [])
    actual_days = len(itinerary)
    passed = actual_days >= expected_min
    return {
        "key": "correct_itinerary_days",
        "score": 1 if passed else 0,
        "comment": f"Expected >= {expected_min} days, got {actual_days}",
    }


def check_budget_not_exceeded(run, example):
    """The total hotel cost must not wildly exceed the budget."""
    max_budget = example.outputs.get("max_budget", float("inf"))
    plan = run.outputs.get("final_plan", {})
    hotels = plan.get("hotels", [])

    if not hotels:
        return {
            "key": "budget_not_exceeded",
            "score": 1,
            "comment": "No hotels in plan; skipping budget check.",
        }

    duration = plan.get("duration_days", 1)
    total_hotel_cost = sum(h.get("price_per_night", 0) * duration for h in hotels)
    passed = total_hotel_cost <= max_budget
    return {
        "key": "budget_not_exceeded",
        "score": 1 if passed else 0,
        "comment": f"Hotel cost: {total_hotel_cost:.0f}, budget: {max_budget}",
    }


def check_currency_matches(run, example):
    """The plan must use the requested currency."""
    expected_currency = example.outputs.get("currency", "USD")
    plan = run.outputs.get("final_plan", {})
    actual_currency = plan.get("currency", "")
    passed = actual_currency == expected_currency
    return {
        "key": "currency_matches",
        "score": 1 if passed else 0,
        "comment": f"Expected {expected_currency}, got {actual_currency}",
    }


def check_destination_matches(run, example):
    """The plan must be for the right destination."""
    expected_destination = example.outputs.get("destination", "")
    plan = run.outputs.get("final_plan", {})
    actual_destination = plan.get("destination", "")
    passed = expected_destination.lower() in actual_destination.lower()
    return {
        "key": "destination_matches",
        "score": 1 if passed else 0,
        "comment": f"Expected '{expected_destination}', got '{actual_destination}'",
    }


def check_has_summary(run, example):
    """The plan must have a non-empty summary."""
    plan = run.outputs.get("final_plan", {})
    summary = plan.get("summary", "")
    passed = bool(summary and len(summary) > 20)
    return {
        "key": "has_summary",
        "score": 1 if passed else 0,
        "comment": f"Summary length: {len(summary)}",
    }


# All evaluators to run -- easy to add more later
ALL_EVALUATORS = [
    check_itinerary_days,
    check_budget_not_exceeded,
    check_currency_matches,
    check_destination_matches,
    check_has_summary,
]