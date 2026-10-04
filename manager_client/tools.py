# manager_client/tools.py

# Imports -------------------------------------------
from manager_client.protocols.client_a2a import (
    send_a2a_message,
    extract_a2a_text,
)
from manager_client.protocols.client_mcp import (
    get_applicant_resume,
)
from manager_client.protocols.client_rest import (
    extend_offer,
)


# Helpers -------------------------------------------
async def tool_get_resume(applicant_id: str):
    """Retrieve one applicant's resume through the MCP client."""
    return await get_applicant_resume(applicant_id)


async def tool_interview_candidate(
    applicant_id: str,
    job_description: str,
    questions: str,
):
    """Ask the Interview A2A agent to simulate answers for a candidate."""
    message = f"""
    Applicant ID:
    {applicant_id}

    Job Description:
    {job_description}

    Interview Questions:
    {questions}
    """

    response = await send_a2a_message(
        "interview",
        message,
    )

    return extract_a2a_text(response)


async def tool_background_check(applicant_id: str):
    """Ask the background A2A agent for one applicant's screening result."""
    response = await send_a2a_message(
        "employee_background",
        f"Check the background screening and drug test for {applicant_id}.",
    )

    return extract_a2a_text(response)


async def tool_get_compensation(role: str):
    """Ask the accountant A2A agent for an approved role salary range."""
    response = await send_a2a_message(
        "staff_accountant",
        f"What is the approved salary range for {role}?",
    )

    return extract_a2a_text(response)


async def tool_ask_hr(message: str):
    """Send hiring context to the HR A2A agent and return its response text."""
    response = await send_a2a_message(
        "hr",
        message,
    )

    return extract_a2a_text(response)


async def tool_extend_offer(
    applicant_id: str,
    salary: float,
):
    """Extend a mock offer through the deterministic REST client."""
    return await extend_offer(
        applicant_id=applicant_id,
        salary=salary,
    )
