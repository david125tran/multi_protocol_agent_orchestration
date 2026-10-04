# manager_client/protocols/client_a2a.py

# Imports -------------------------------------------
import uuid
import httpx


# Constants/Variables -------------------------------------------
BASE_URL = "http://127.0.0.1:8000"


# Helpers -------------------------------------------
async def list_agents():
    """Fetch the backend's current A2A agent directory."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/a2a/agents"
        )

        response.raise_for_status()

        return response.json()


async def get_agent_card(agent_name: str):
    """Fetch one agent's card, or a helpful error for an unknown agent ID."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/a2a/{agent_name}/.well-known/agent-card.json"
        )

        if response.status_code == 404:
            return {
                "error": "AGENT_NOT_FOUND",
                "message": (
                    f"No agent exists with agent_id '{agent_name}'. "
                    "Use the exact agent_id returned by list_agents."
                ),
            }

        response.raise_for_status()

        return response.json()


async def send_a2a_message(
    agent_name: str,
    message: str,
):
    """Send a message to an A2A agent and return its JSON-RPC response."""

    url = f"{BASE_URL}/a2a/{agent_name}/jsonrpc"

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "ROLE_USER",
                "parts": [
                    {
                        "text": message
                    }
                ],
            }
        },
    }

    headers = {
        "Content-Type": "application/json",
        "A2A-Version": "1.0",
    }

    timeout = httpx.Timeout(
        120.0,
        connect=10.0,
    )

    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:

        response = await client.post(
            url,
            json=payload,
            headers=headers,
        )

        response.raise_for_status()

        return response.json()

def extract_a2a_text(response: dict) -> str:
    """Return the first text artifact from an A2A response or a readable error."""
    if "error" in response:
        error = response["error"]

        return (
            f"A2A Error: "
            f"{error.get('message', 'Unknown error')}"
        )

    # The A2A SDK can wrap a completed task inside the JSON-RPC result.
    result = response.get("result", response)
    task = result.get("task") if isinstance(result, dict) else None

    if task is None:
        task = response.get("task")

    payload = task or result
    artifacts = payload.get("artifacts", [])

    for artifact in artifacts:
        for part in artifact.get("parts", []):
            text = part.get("text")

            if text:
                return text

    return str(payload)
