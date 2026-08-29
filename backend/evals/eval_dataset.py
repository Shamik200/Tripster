"""
eval_dataset.py
---------------
A small, hardcoded set of test cases for the Tripster trip planner.
Each entry has:
  - inputs:  the TripPreferences the user sends
  - expected: what we roughly expect in the result (used by evaluators)
"""

DATASET = [
    {
        "inputs": {
            "destination": "Paris",
            "origin": "New York",
            "budget": 3000.0,
            "currency": "USD",
            "start_date": "2025-10-01",
            "end_date": "2025-10-07",
            "interests": ["art", "food", "culture"],
            "travel_style": "balanced",
        },
        "expected": {
            "min_days": 6,
            "max_budget": 3000.0,
            "currency": "USD",
            "destination": "Paris",
        },
    },
    {
        "inputs": {
            "destination": "Tokyo",
            "origin": "London",
            "budget": 150000.0,
            "currency": "INR",
            "start_date": "2025-11-05",
            "end_date": "2025-11-10",
            "interests": ["technology", "anime", "food"],
            "travel_style": "budget",
        },
        "expected": {
            "min_days": 5,
            "max_budget": 150000.0,
            "currency": "INR",
            "destination": "Tokyo",
        },
    },
    {
        "inputs": {
            "destination": "Bali",
            "origin": "Sydney",
            "budget": 5000.0,
            "currency": "USD",
            "start_date": "2025-12-20",
            "end_date": "2025-12-27",
            "interests": ["beach", "wellness", "adventure"],
            "travel_style": "luxury",
        },
        "expected": {
            "min_days": 7,
            "max_budget": 5000.0,
            "currency": "USD",
            "destination": "Bali",
        },
    },
]