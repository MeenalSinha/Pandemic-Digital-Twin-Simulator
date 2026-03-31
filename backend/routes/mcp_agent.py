"""
MCP Agent Route — POST /mcp-agent

Exposes the PandemicMCPAgent via a simple REST endpoint.

Request:  { "query": "What happens with a lockdown in Delhi?" }
Response: { "data": {...}, "response": "natural language explanation" }
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)


class MCPAgentRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Natural language question about a pandemic intervention",
        examples=["What is the impact of a lockdown in Delhi?"],
    )


class MCPAgentResponse(BaseModel):
    agent: str
    query: str
    intent: dict
    mcp_tool_call: dict
    data: dict | None
    response: str
    error: str | None = None


@router.post("", response_model=MCPAgentResponse)
async def run_mcp_agent(request: MCPAgentRequest):
    """
    Run the PandemicMCPAgent pipeline:
    1. Parse natural language query for region + intervention
    2. Call simulate_pandemic MCP tool
    3. Return structured data + natural language response
    """
    try:
        from agents.mcp_agent import get_mcp_agent

        agent = get_mcp_agent()
        result = agent.run(request.query)
        return result

    except Exception as exc:
        logger.exception("MCP agent endpoint error")
        raise HTTPException(
            status_code=500,
            detail=f"MCP agent error: {str(exc)}"
        )


@router.get("/schema")
async def get_mcp_schema():
    """Return the MCP tool schema — shows which tools the agent has access to."""
    try:
        from agents.mcp_agent import get_mcp_agent
        agent = get_mcp_agent()

        tools = []
        for tool in agent._registry.list_tools():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "output_schema": tool.output_schema,
            })

        return {
            "agent": agent.CONFIG.name,
            "description": agent.CONFIG.description,
            "model": agent.CONFIG.model,
            "mcp_tools": tools,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
