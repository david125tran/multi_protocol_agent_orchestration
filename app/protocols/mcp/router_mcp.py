# app/protocols/mcp/router_mcp.py

# Imports -------------------------------------------
import json
from mcp.server.fastmcp import FastMCP
from pathlib import Path


# Constants / Variables -------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# Mock applicant data used by the MCP resume tool.
APPLICANT_JSON = PROJECT_ROOT / "data" / "applicants.json"


# MCP Server -------------------------------------------
# Create the MCP server that exposes applicant-related tools.
mcp = FastMCP("Applicant Data Tools")


# Helpers -------------------------------------------
def load_applicants():
    """Load the mock applicant records from the root-level data directory."""
    with open(APPLICANT_JSON, "r", encoding="utf-8") as file:
        return json.load(file)["applicants"]


def find_applicant(applicant_id: str):
    """Return the applicant matching an ID, or ``None`` when no match exists."""
    for applicant in load_applicants():
        if applicant["applicant_id"] == applicant_id:
            return applicant

    return None


# MCP Tools -------------------------------------------
@mcp.tool()
def get_applicant_resume(applicant_id: str):
    """
    Return the MCP-safe resume fields for one applicant.

    ``applicant_id`` is the identifier shown in the demo data. Screening data
    is intentionally excluded because this tool represents resume retrieval.
    """
    applicant = find_applicant(applicant_id)

    if not applicant:
        return {
            "error": "APPLICANT_NOT_FOUND"
        }

    return {
        "applicant_id": applicant["applicant_id"],
        "name": applicant["name"],
        "target_role": applicant["target_role"],
        "years_experience": applicant["years_experience"],
        "technical_background": applicant["technical_background"],
        "employment_history": applicant["employment_history"],
    }


mcp_app = mcp.streamable_http_app()
