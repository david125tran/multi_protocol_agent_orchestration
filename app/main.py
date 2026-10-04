# app/main.py

# Imports -------------------------------------------
import contextlib

from fastapi import FastAPI
from a2a.server.routes import add_a2a_routes_to_fastapi
from app.protocols.a2a.router_a2a import (
    jsonrpc_routes,
    agent_card_routes,
    agent_cards,
)
from app.protocols.mcp.router_mcp import (
    mcp,
    mcp_app,
)
from app.protocols.rest.router_rest import (
    router as rest_router,
)


# Application Lifespan -------------------------------------------
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Keep the MCP session manager running for the lifetime of the FastAPI app.

    The MCP server is mounted inside this FastAPI application, so its session
    manager needs to be started when the app starts and stopped when the app
    shuts down.
    """
    """Run the MCP session manager while the FastAPI application is alive."""
    async with mcp.session_manager.run():
        yield


# FastAPI Application -------------------------------------------
# Create the main FastAPI app and attach the shared startup/shutdown lifecycle.
app = FastAPI(
    lifespan=lifespan
)


# A2A Agent Directory -------------------------------------------
@app.get("/a2a/agents")
def list_agents():
    """
    Return a simple directory of the A2A agents available in this application.

    This gives external clients a lightweight way to discover agent IDs,
    display names, descriptions, and versions before requesting full Agent Cards.

    I'm purposely not showing the agent's description here so that it doesn't 
    understand what the staff_accountant does and goes through progressive
    disclosure. 
    """
    return {
        name: {
            "agent_id": name,
            "name": card.name,
            "version": card.version,
        }
        for name, card in agent_cards.items()
    }


# REST Routes -------------------------------------------
# Register the standard REST API endpoints with the main FastAPI app.
app.include_router(rest_router)


# A2A Routes -------------------------------------------
# Register the A2A Agent Card and JSON-RPC endpoints for all configured agents.
add_a2a_routes_to_fastapi(
    app,
    agent_card_routes=agent_card_routes,
    jsonrpc_routes=jsonrpc_routes,
)


# MCP Routes -------------------------------------------
# Mount the MCP ASGI application under the /mcp URL prefix.
app.mount(
    "/mcp",
    mcp_app,
)
