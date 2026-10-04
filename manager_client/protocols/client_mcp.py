# manager_client/protocols/client_mcp.py

import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import (
    streamable_http_client,
)


# Constants/Variables -------------------------------------------
MCP_URL = "http://127.0.0.1:8000/mcp/mcp"


# Helpers -------------------------------------------
async def get_applicant_resume(applicant_id: str):
    """Call the applicant-resume MCP tool and normalize its returned content."""

    async with streamable_http_client(MCP_URL) as (
        read_stream,
        write_stream,
        _,
    ):

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            result = await session.call_tool(
                "get_applicant_resume",
                {
                    "applicant_id": applicant_id,
                },
            )

            # MCP servers may return either structured data or text content.
            if result.structuredContent is not None:
                return result.structuredContent

            for content in result.content:

                if hasattr(content, "text"):

                    try:
                        return json.loads(content.text)

                    except json.JSONDecodeError:
                        return content.text

            return None


async def get_all_applicant_resumes(applicant_ids: list[str]) -> dict:
    """Retrieve several resumes concurrently and keep errors tied to each ID.

    ``applicant_ids`` contains the applicants in the current hiring task. Each
    MCP call uses its own session, so the initial screen does not wait for one
    request to finish before starting the next one.
    """
    results = await asyncio.gather(
        *(get_applicant_resume(applicant_id) for applicant_id in applicant_ids),
        return_exceptions=True,
    )

    return {
        applicant_id: (
            {
                "error": type(result).__name__,
                "message": str(result),
            }
            if isinstance(result, Exception)
            else result
        )
        for applicant_id, result in zip(applicant_ids, results)
    }
