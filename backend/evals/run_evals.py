"""
run_evals.py
------------
Run LangSmith evaluations for the Tripster trip planner.

HOW TO USE:
  1. Make sure LANGCHAIN_API_KEY is set in .env and LANGCHAIN_TRACING_V2=true
  2. From the backend/ folder, run:
       python evals/run_evals.py

What this script does:
  - Loads our 3 test cases from eval_dataset.py
  - Pushes them as a Dataset to LangSmith (creates it if not there)
  - Runs the real trip_graph pipeline on each test case
  - Runs 5 evaluators on each result
  - Pushes scores to LangSmith so you can view them on the dashboard
"""

import json
import os
import sys

# Make sure Python can find our app modules when run from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load env vars from the root .env file (one level above backend/)
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Enable LangSmith tracing (must be done before importing LangChain)
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")

from langsmith import Client
from langsmith.evaluation import evaluate

from app.agent.graph import run_trip_planner
from app.schemas.trip import TripPreferences
from evals.eval_dataset import DATASET
from evals.evaluators import ALL_EVALUATORS

# LangSmith dataset name
DATASET_NAME = "Tripster - Trip Planner Eval"


def push_dataset(client: Client) -> str:
    """Upload our test cases to LangSmith and return the dataset ID."""
    if client.has_dataset(dataset_name=DATASET_NAME):
        existing = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Dataset '{DATASET_NAME}' already exists -- reusing it.")
        return str(existing.id)

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Automated test cases for the Tripster AI trip planner.",
    )

    for case in DATASET:
        client.create_example(
            inputs=case["inputs"],
            outputs=case["expected"],
            dataset_id=dataset.id,
        )

    print(f"Created dataset '{DATASET_NAME}' with {len(DATASET)} examples.")
    return str(dataset.id)


def pipeline_wrapper(inputs: dict) -> dict:
    """
    This is the function LangSmith calls for each test case.
    It must accept a dict of inputs and return a dict of outputs.
    """
    preferences = TripPreferences(**inputs)
    plan = run_trip_planner(preferences)
    return {"final_plan": plan.model_dump()}


def main():
    api_key = os.environ.get("LANGCHAIN_API_KEY", "")
    if not api_key:
        print("ERROR: LANGCHAIN_API_KEY is not set in your .env file.")
        print("Get your key at https://smith.langchain.com and add it to .env")
        sys.exit(1)

    print("Connecting to LangSmith...")
    client = Client()

    # Step 1: Upload test cases
    push_dataset(client)

    # Step 2: Run evals
    print(f"\nRunning evaluations on {len(DATASET)} test cases...")
    print("This calls the real LLM pipeline -- may take a few minutes.\n")

    results = evaluate(
        pipeline_wrapper,
        data=DATASET_NAME,
        evaluators=ALL_EVALUATORS,
        experiment_prefix="tripster-eval",
        metadata={"model": "gemini-2.5-flash", "version": "v1"},
    )

    # Step 3: Print a simple summary to the console
    print("\n" + "=" * 50)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 50)

    total_scores = {}
    count = 0

    for result in results:
        count += 1
        dest = result.get("example", {}).get("inputs", {}).get("destination", "?")
        print(f"\nTest case: {dest}")
        for eval_result in result.get("evaluation_results", {}).get("results", []):
            key = eval_result.key
            score = eval_result.score
            comment = getattr(eval_result, "comment", "")
            status = "PASS" if score == 1 else "FAIL"
            print(f"  [{status}] {key}: {comment}")
            total_scores[key] = total_scores.get(key, 0) + (score or 0)

    print("\n" + "-" * 50)
    print("OVERALL PASS RATE PER METRIC:")
    for key, total in total_scores.items():
        rate = (total / count) * 100 if count else 0
        print(f"  {key}: {rate:.0f}% ({total}/{count})")

    print("\nFull results visible at: https://smith.langchain.com")
    print("=" * 50)


if __name__ == "__main__":
    main()