# manager_client/protocols/client_rest.py

# Imports -------------------------------------------
import httpx


# Constants/Variables -------------------------------------------
REST_URL = "http://127.0.0.1:8000/api"


# Helpers -------------------------------------------
async def extend_offer(
    applicant_id: str,
    salary: float,
) -> dict:
    """Send a final applicant ID and annual salary to the REST offer endpoint."""

    payload = {
        "applicant_id": applicant_id,
        "salary": salary,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{REST_URL}/offers",
            json=payload,
        )

        response.raise_for_status()

        return response.json()
