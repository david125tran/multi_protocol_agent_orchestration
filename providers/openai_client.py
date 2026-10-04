# providers/openai_client.py

"""Create the shared OpenAI client after loading local environment settings."""

# Imports -------------------------------------------
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Constants / Variables -------------------------------------------
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL")


# Helpers -------------------------------------------
def get_openai_client() -> OpenAI:
    """Return an OpenAI client configured with the local API key."""
    return OpenAI(api_key=OPENAI_API_KEY)
