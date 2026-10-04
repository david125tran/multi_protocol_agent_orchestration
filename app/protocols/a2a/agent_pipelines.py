# app/protocols/a2a/agent_pipelines.py

# Imports -------------------------------------------
import csv
import json

from pathlib import Path

from pydantic import BaseModel, Field

from providers.openai_client import (
    get_openai_client,
    LLM_MODEL,
)

from app.protocols.a2a.pipelines.employee_background_pipeline import (
    invoke_graph,
)

from app.protocols.a2a.pipelines.interview_pipeline import (
    invoke_interview_graph,
)


# Constants / Variables -------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]

SALARY_CSV = (
    PROJECT_ROOT
    / "data"
    / "company_salaries.csv"
)


# Structured Outputs -------------------------------------------
class CompensationLookup(BaseModel):
    """
    Normalized compensation taxonomy selected from the approved company data.

    The model is only responsible for interpreting the caller's natural-language
    job title. The actual salary lookup is performed deterministically in Python.
    """

    position: str | None = Field(
        default=None,
        description=(
            "Approved company position selected from the supplied valid "
            "positions, or null when no reasonable mapping exists."
        ),
    )

    level: str | None = Field(
        default=None,
        description=(
            "Approved company level selected from the supplied valid levels, "
            "or null when no reasonable mapping exists."
        ),
    )


# Agent Pipelines -------------------------------------------
async def hr_pipeline(message: str) -> str:
    """
    Ask the HR Agent to review hiring readiness and recommend an appropriate
    offer using supplied candidate evidence and approved compensation data.
    """
    client = get_openai_client()

    response = client.responses.create(
        instructions="""
        You are the Human Resources Agent for David Airlines.

        Your role is to advise hiring managers on:

        - candidate hiring readiness
        - potential hiring concerns or risks
        - whether the available evidence supports proceeding with an offer
        - appropriate salary positioning within an approved compensation range

        You are an ADVISOR.

        You do not make the final hiring decision.

        The Hiring Manager remains responsible for deciding whether to hire
        a candidate and whether to extend an offer.


        HIRING REVIEW

        When candidate information is provided, review the available evidence
        and identify meaningful concerns.

        Consider information such as:

        - relevant experience
        - interview results
        - demonstrated job fit
        - seniority and level alignment
        - required screening results
        - whether important hiring information is still missing

        Do not invent candidate information.

        If there is not enough evidence to reasonably support an offer,
        clearly say what information is still needed.

        If required pre-employment screening has failed, advise against
        proceeding with the hire.

        A strong resume or interview does not override failed required
        screening.


        COMPENSATION

        You do NOT have access to David Airlines salary data.

        You are NEVER allowed to invent, estimate, guess, or use general
        market knowledge to determine the company's salary ranges.

        Before recommending a specific salary, the caller MUST provide
        approved compensation data.

        Valid compensation data should contain:

        - position
        - level
        - minimum salary
        - midpoint salary
        - maximum salary

        If compensation data has NOT been provided, do NOT recommend a
        specific salary.

        Instead respond:

        COMPENSATION_DATA_REQUIRED

        Please obtain the approved internal salary range from the appropriate
        company compensation source and return that information to me.

        Once valid compensation data is supplied, consider the candidate's
        qualifications, experience, interview evidence, and hiring readiness
        when recommending where within the approved range the offer should fall.

        Never recommend an offer outside the supplied salary range.

        Avoid automatically recommending the maximum salary merely because
        a candidate is qualified.

        The recommendation should be supported by the supplied evidence.


        RESPONSE STYLE

        Give a concise advisory response that includes, when relevant:

        Hiring Readiness: READY / NOT READY / NEEDS MORE INFORMATION

        Concerns:
        <important concerns or "None identified">

        Recommended Action:
        <what the hiring manager should do next>

        Recommended Offer:
        <specific salary only when valid compensation data was supplied>

        Brief Rationale:
        <short explanation based only on the supplied evidence>
        """,
        input=message,
        model=LLM_MODEL,
    )

    return response.output_text


async def employee_background_pipeline(message: str) -> str:
    """Run the deterministic background-screening graph for an A2A message."""
    initial_state = {
        "user_query": message,
    }

    graph_output = invoke_graph(
        initial_state
    )

    return format_screening_result(graph_output)


def format_screening_result(graph_output: dict) -> str:
    """Combine the screening summary with the complete stored screening record."""
    screening_record = {
        "applicant_id": graph_output.get("applicant_id"),
        "applicant_name": graph_output.get("applicant_name"),
        "background_check": graph_output.get("background_check_data"),
        "drug_test": graph_output.get("drug_test_data"),
    }

    return (
        f"{graph_output['result']}\n\n"
        "Full screening record:\n"
        f"{json.dumps(screening_record, indent=2)}"
    )


async def staff_accountant_pipeline(message: str) -> str:
    """
    Resolve a natural-language role into the approved compensation taxonomy,
    then perform an exact deterministic lookup against the salary CSV.
    """
    client = get_openai_client()

    salary_rows = load_salary_rows()

    valid_positions = sorted(
        {
            row["position"].strip()
            for row in salary_rows
            if row.get("position")
        }
    )

    valid_levels = sorted(
        {
            row["level"].strip()
            for row in salary_rows
            if row.get("level")
        }
    )

    response = client.responses.parse(
        model=LLM_MODEL,
        instructions=f"""
        You are the Staff Accountant for David Airlines.

        You help resolve natural-language job titles into the company's
        approved compensation taxonomy.

        IMPORTANT:

        You are NOT responsible for choosing or inventing salary values.

        Your only job in this step is to interpret the caller's requested role
        and map it to one approved company POSITION and one approved LEVEL.

        The actual compensation lookup will be performed deterministically
        after your response.


        VALID POSITIONS

        {valid_positions}


        VALID LEVELS

        {valid_levels}


        NORMALIZATION RULES

        - Use ONLY values from VALID POSITIONS and VALID LEVELS.
        - Do not invent a new position.
        - Do not invent a new level.
        - Interpret seniority words such as Junior, Staff, Senior, Manager,
          Principal, or similar terms as a level when they correspond to a
          supplied approved level.
        - Do not assume that every word in the caller's job title belongs in
          the position name.
        - Prefer separating seniority from the underlying position when the
          approved taxonomy clearly does so.

        Example:

        Caller request:
        "Senior Software Engineer"

        Valid normalized interpretation:

        Position: Software Engineer
        Level: Senior


        AMBIGUITY

        Only return a position and level when the requested role can be
        reasonably mapped to the approved taxonomy.

        If the request is genuinely ambiguous or no reasonable mapping exists:

        - return null for position
        - return null for level

        Do not select an unrelated "closest" position merely so that a match
        can be produced.

        The caller may then clarify the request.
        """,
        input=message,
        text_format=CompensationLookup,
    )

    lookup = response.output_parsed

    if (
        lookup is None
        or not lookup.position
        or not lookup.level
    ):
        return (
            "COMPENSATION_DATA_NOT_FOUND\n\n"
            "The requested role could not be mapped confidently to an approved "
            "position and level. Please clarify the intended role or level."
        )

    salary_row = find_salary_row(
        rows=salary_rows,
        position=lookup.position,
        level=lookup.level,
    )

    if not salary_row:
        return (
            "COMPENSATION_DATA_NOT_FOUND\n\n"
            f"Resolved Position: {lookup.position}\n"
            f"Resolved Level: {lookup.level}\n\n"
            "No exact approved compensation row exists for that combination."
        )

    minimum_salary = salary_row.get(
        "minimum_salary",
        "",
    )

    midpoint_salary = salary_row.get(
        "midpoint_salary",
        "",
    )

    maximum_salary = salary_row.get(
        "maximum_salary",
        "",
    )

    return (
        "COMPENSATION_DATA\n\n"
        f"Requested Role: {message.strip()}\n"
        f"Resolved Position: {salary_row['position']}\n"
        f"Resolved Level: {salary_row['level']}\n\n"
        "The requested role maps to this approved compensation classification.\n\n"
        f"Minimum Salary: {minimum_salary}\n"
        f"Midpoint Salary: {midpoint_salary}\n"
        f"Maximum Salary: {maximum_salary}"
    )


async def interview_pipeline(message: str) -> str:
    """Run the interview graph that simulates an applicant's answers."""
    initial_state = {
        "user_query": message,
    }

    graph_output = invoke_interview_graph(
        initial_state
    )

    return graph_output["result"]


# Compensation Data Helpers -------------------------------------------
def load_salary_rows() -> list[dict]:
    """
    Load and return all approved compensation rows from the company salary CSV.
    """
    with open(
        SALARY_CSV,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        return [
            {
                key: (
                    value.strip()
                    if isinstance(value, str)
                    else value
                )
                for key, value in row.items()
            }
            for row in reader
        ]


def find_salary_row(
    rows: list[dict],
    position: str,
    level: str,
) -> dict | None:
    """
    Return the exact approved compensation row for a position and level.

    Matching is case-insensitive but otherwise deterministic.
    """
    normalized_position = position.strip().casefold()
    normalized_level = level.strip().casefold()

    for row in rows:

        row_position = (
            row.get(
                "position",
                "",
            )
            .strip()
            .casefold()
        )

        row_level = (
            row.get(
                "level",
                "",
            )
            .strip()
            .casefold()
        )

        if (
            row_position == normalized_position
            and row_level == normalized_level
        ):
            return row

    return None
