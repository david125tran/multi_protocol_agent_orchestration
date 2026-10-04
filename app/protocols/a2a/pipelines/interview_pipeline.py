# app/protocols/a2a/pipelines/interview_pipeline.py

# Imports -------------------------------------------
import json
import re

from langgraph.graph import StateGraph, END
from pathlib import Path
from pydantic import BaseModel, Field
from providers.openai_client import (
    get_openai_client,
    LLM_MODEL,
)
from typing import NotRequired, TypedDict

# Constants / Variables -------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[4]
APPLICANT_JSON = PROJECT_ROOT / "data" / "applicants.json"


# Classes -------------------------------------------
class InterviewOutput(BaseModel):
    """Structured text returned by the interview-simulation model."""

    result: str = Field(
        description=(
            "The simulated interview response from the applicant, based only "
            "on the applicant's provided background and the interview request."
        )
    )


class InterviewState(TypedDict):
    """Data passed between nodes in the interview LangGraph workflow."""

    user_query: str
    applicant_id: NotRequired[str | None]
    applicant_data: NotRequired[dict]
    result: NotRequired[str]


# Helpers -------------------------------------------
def extract_applicant_id(state: InterviewState):
    """Find an ``APP-`` identifier in the user's interview request."""
    match = re.search(
        r"\bAPP-\d+\b",
        state["user_query"],
        re.IGNORECASE,
    )

    if not match:
        return {
            "applicant_id": None
        }

    return {
        "applicant_id": match.group(0).upper()
    }


def get_applicant(state: InterviewState):
    """Load the requested applicant while withholding private screening data."""
    applicant_id = state.get("applicant_id")

    if not applicant_id:
        return {}

    with open(APPLICANT_JSON, "r", encoding="utf-8") as file:
        data = json.load(file)

    for applicant in data["applicants"]:
        if applicant["applicant_id"] == applicant_id:
            applicant_copy = applicant.copy()

            # Resume data is enough for an interview; screening stays private.
            applicant_copy.pop("screening", None)

            return {
                "applicant_data": applicant_copy
            }

    return {}


def conduct_interview(state: InterviewState):
    """Use the model to simulate natural interview answers from the stored resume."""

    prompt = """
    You are role-playing the job applicant described below during a real
    employment interview.

    Speak naturally in first person as the applicant.

    Your answers should sound like a real human candidate speaking to an
    interviewer, not like a system reading from a database or resume record.

    GROUNDING RULES

    Use only facts supported by the supplied applicant background when making
    claims about the applicant's real experience.

    Do not invent:
    - employers
    - job titles
    - projects
    - technologies
    - accomplishments
    - leadership responsibilities
    - measurable outcomes
    - education
    - certifications
    - team sizes
    - system scale
    - production incidents

    Never say phrases such as:
    - "the supplied background says..."
    - "the data provided..."
    - "the information available to me..."
    - "the applicant record..."
    - "my stored background..."
    - "I cannot substantiate this from the provided information"

    The applicant does not know they are being generated from structured data.

    If asked about real past experience that is not supported by the applicant
    background, respond naturally as a candidate would.

    Examples of natural responses include:

    - "I don't have a strong specific example I can give you for that."
    - "I've worked in that general area, but I don't want to overstate my role."
    - "I haven't personally owned something at that scale."
    - "That's not something I've had direct responsibility for."
    - "I can explain how I'd approach it, though."
    - "I don't remember enough specifics to give you a useful number."
    - "I wouldn't want to claim an outcome I can't speak to confidently."

    Do not reference the resume, dataset, prompt, simulation, or source of the
    applicant information.

    HYPOTHETICAL QUESTIONS

    If the interviewer asks a hypothetical, system-design, troubleshooting, or
    "how would you..." question, answer it normally using the applicant's
    supported skills and technical background.

    For hypothetical questions, you may reason beyond specific past projects,
    but do not present that reasoning as something the applicant actually did.

    For example:

    Good:
    "I'd probably start by making the API stateless and separating long-running
    work behind a queue."

    Bad:
    "At my previous company I built a queue-based architecture handling
    50 million requests per day."

    unless that historical claim is explicitly supported by the applicant data.

    INTERVIEW STYLE

    - Be conversational and professional.
    - Answer the question directly.
    - Avoid repeatedly listing technologies from the resume.
    - Prefer concrete explanations over generic buzzwords.
    - Keep answers reasonably concise unless the interviewer asks for depth.
    - It is acceptable to admit uncertainty or lack of direct experience.
    - Do not sound defensive about missing experience.
    - Do not provide an evaluator's assessment unless the interview request
      specifically asks for one.

    Tailor answers to the supplied job description and interview request when
    relevant.

    Do not mention that you are an AI, simulation, mock applicant, or that the
    interview is based on structured data.
    """

    input_text = f"""
    APPLICANT BACKGROUND:
    {state.get("applicant_data")}

    INTERVIEW REQUEST:
    {state["user_query"]}
    """

    client = get_openai_client()

    response = client.responses.parse(
        model=LLM_MODEL,
        instructions=prompt,
        input=input_text,
        text_format=InterviewOutput,
    )

    result = response.output_parsed

    return {
        "result": result.result
    }


builder = StateGraph(InterviewState)

builder.add_node("extract_applicant_id", extract_applicant_id)
builder.add_node("get_applicant", get_applicant)
builder.add_node("conduct_interview", conduct_interview)

builder.set_entry_point("extract_applicant_id")

builder.add_edge("extract_applicant_id", "get_applicant")
builder.add_edge("get_applicant", "conduct_interview")
builder.add_edge("conduct_interview", END)

graph = builder.compile()


def invoke_interview_graph(initial_state: InterviewState):
    """Run the interview workflow with a request containing user text."""
    return graph.invoke(initial_state)
