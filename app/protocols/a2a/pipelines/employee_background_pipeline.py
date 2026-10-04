# app/protocols/a2a/pipelines/employee_background_pipeline.py

# Imports -------------------------------------------
import json
import re

from langgraph.graph import END, StateGraph
from pathlib import Path
from providers.openai_client import (
    get_openai_client,
    LLM_MODEL,
)
from pydantic import BaseModel, Field
from typing import NotRequired, TypedDict


# Constants / Variables -------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[4]
APPLICANT_JSON = PROJECT_ROOT / "data" / "applicants.json"


# Classes -------------------------------------------
class ProcessorOutput(BaseModel):
    """Structured screening decision returned by the processing model."""

    result: str = Field(
        description=(
            "Tell the user whether the applicant passed, failed, or requires "
            "review based on the supplied background-check and drug-test data."
        )
    )


class AgentState(TypedDict):
    """Data passed between nodes in the background-screening workflow."""

    user_query: str
    applicant_id: NotRequired[str | None]
    applicant_name: NotRequired[str]
    background_check_data: NotRequired[dict]
    drug_test_data: NotRequired[dict]
    result: NotRequired[str]


# Helpers -------------------------------------------
def extract_applicant_id(state: AgentState):
    """Find an ``APP-`` identifier in the screening request."""
    match = re.search(r"\bAPP-\d+\b", state["user_query"], re.IGNORECASE)

    if not match:
        return {
            "applicant_id": None
        }

    return {
        "applicant_id": match.group(0).upper()
    }


def get_applicant(state: AgentState):
    """Load the requested applicant's stored screening records."""
    applicant_id = state.get("applicant_id")

    if not applicant_id:
        return {}

    with open(APPLICANT_JSON, "r", encoding="utf-8") as file:
        data = json.load(file)

    for applicant in data["applicants"]:
        if applicant["applicant_id"] == applicant_id:
            return {
                "applicant_name": applicant["name"],
                "background_check_data": applicant["screening"]["background_check"],
                "drug_test_data": applicant["screening"]["drug_test"],
            }

    return {}


def processor(state: AgentState):
    """Turn supplied screening records into a concise PASS, FAIL, or REVIEW result."""
    prompt = """
    You are a pre-employment background-check processor.

    Based only on the supplied screening data, tell the user whether
    the applicant passed, failed, or requires review.

    Consider both:
    - background check data
    - drug test data

    Do not invent information.
    """

    input_text = f"""
    Applicant ID: {state.get("applicant_id")}
    Applicant Name: {state.get("applicant_name")}

    Background Check Data:
    {state.get("background_check_data")}

    Drug Test Data:
    {state.get("drug_test_data")}
    """

    client = get_openai_client()

    response = client.responses.parse(
        model=LLM_MODEL,
        instructions=prompt,
        input=input_text,
        text_format=ProcessorOutput,
    )

    result = response.output_parsed

    return {
        "result": result.result
    }

builder = StateGraph(AgentState)

builder.add_node("extract_applicant_id", extract_applicant_id)
builder.add_node("get_applicant", get_applicant)
builder.add_node("processor", processor)

builder.set_entry_point("extract_applicant_id")

builder.add_edge("extract_applicant_id", "get_applicant")
builder.add_edge("get_applicant", "processor")
builder.add_edge("processor", END)

graph = builder.compile()


def invoke_graph(initial_state: AgentState):
    """Run the background-screening workflow with a user request."""
    return graph.invoke(initial_state)
