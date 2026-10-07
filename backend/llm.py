"""Shared LLM + MCP wiring for every Campus Customs agent.

Rule 9 (output/harness.md): every agent uses gpt-6-luna, reached through the
Portkey gateway, authenticated with the PORTKEY_API_KEY environment variable.
This is the only place a model is configured -- agents import build_model()
so no agent can drift onto a different model.
"""

import json
import os
import sys
from pathlib import Path

from openai import AsyncOpenAI
from fastmcp import Client
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_CONFIG = PROJECT_ROOT / ".mcp.json"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
SERVER_PREFIX = "campus-customs_"

# Token budget for one ticket. The Boss and every specialist it delegates to
# share one usage counter, so this caps the whole team's work on a ticket.
TEAM_LIMITS = UsageLimits(request_limit=30, total_tokens_limit=200_000)


def build_model() -> OpenAIResponsesModel:
    """gpt-6-luna via Portkey's OpenAI-compatible Responses API.

    Uses /v1/responses rather than /v1/chat/completions: the provider rejects
    function tools on chat completions for gpt-6-luna.
    """
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set")
    client = AsyncOpenAI(
        base_url=PORTKEY_BASE_URL,
        api_key=api_key,
        default_headers={
            "x-portkey-api-key": api_key,
            # Never serve a cached reply: the shop's state changes between runs, and
            # cached Responses items carry ids the API rejects when sent back.
            "x-portkey-cache-force-refresh": "true",
        },
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def load_prompt(role: str) -> str:
    """Read an agent's system prompt from backend/prompts/<role>.md."""
    return (PROMPTS_DIR / f"{role}.md").read_text(encoding="utf-8")


def mcp_config() -> dict:
    """.mcp.json with machine-specific bits filled in, so the repo stays portable.

    "python" becomes the interpreter running this code (the project's venv),
    and relative script paths are resolved against the project root -- so it
    works whether the backend is started from backend/ or the project root.
    """
    cfg = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    for server in cfg["mcpServers"].values():
        if server.get("command") in ("python", "python3"):
            server["command"] = sys.executable
        server["args"] = [
            str(PROJECT_ROOT / a) if a.endswith(".py") and not Path(a).is_absolute() else a
            for a in server.get("args", [])
        ]
    return cfg


def campus_tools(*tool_names: str):
    """The campus-customs MCP server (from .mcp.json), limited to tool_names.

    Agents get facts and take actions ONLY through these MCP tools -- there is
    no other path to the database. No agent is given approve_board_item: cash
    moves only through the backend's human-approval route.

    Tools are prefixed with the server name, e.g.
    "campus-customs_check_inventory"; we match on the unprefixed name.
    """
    toolset = MCPToolset(Client(mcp_config())).prefixed(SERVER_PREFIX.rstrip("_"))
    allowed = {f"{SERVER_PREFIX}{n}" for n in tool_names}
    return toolset.filtered(lambda ctx, tool_def: tool_def.name in allowed)
