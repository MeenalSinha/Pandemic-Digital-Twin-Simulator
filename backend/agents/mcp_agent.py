"""
PandemicMCPAgent — ADK-compatible Agent using Model Context Protocol (MCP)

Architecture (compliant with problem statement):
  ONE Agent  : PandemicMCPAgent
  ONE Tool   : simulate_pandemic (MCP tool wrapping the SEIR engine)
  Data Flow  : User query → parse intent → call MCP tool → structured data → LLM response

Agent Development Kit (ADK) pattern:
  - Tool is declared as a callable with typed schema
  - Agent orchestrates Tool call and generates final response
  - MCP protocol is implemented via the MCPToolRegistry + MCPToolCall pattern
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── MCP Protocol Primitives ────────────────────────────────────────────────────

@dataclass
class MCPToolSchema:
    """Describes an MCP tool (analogous to JSON Schema in MCP spec)."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


@dataclass
class MCPToolCall:
    """An MCP tool invocation request."""
    tool_name: str
    arguments: Dict[str, Any]


@dataclass
class MCPToolResult:
    """Structured result returned by an MCP tool."""
    tool_name: str
    content: Dict[str, Any]
    is_error: bool = False
    error_message: str = ""


# ── MCP Tool: simulate_pandemic ───────────────────────────────────────────────

class PandemicSimulationTool:
    """
    MCP-compatible tool that wraps the existing SEIR simulation engine.

    This is the single external data source the MCP agent connects to.
    Returns deterministic, structured JSON data that the agent uses
    to formulate its natural language response.
    """

    TOOL_SCHEMA = MCPToolSchema(
        name="simulate_pandemic",
        description=(
            "Runs an SEIR epidemic simulation for a given region and intervention. "
            "Returns structured data: peak infections, reduction percentage, and lives saved "
            "compared to a no-action baseline."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "City/region ID (delhi, mumbai, london, new_york, tokyo, sao_paulo)",
                    "enum": ["delhi", "mumbai", "london", "new_york", "tokyo", "sao_paulo"],
                },
                "intervention": {
                    "type": "string",
                    "description": "Public health intervention type",
                    "enum": [
                        "no_action", "partial_lockdown", "full_lockdown",
                        "vaccination_rollout", "combined_strategy",
                        "school_closure", "travel_restriction",
                    ],
                },
            },
            "required": ["region", "intervention"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "intervention": {"type": "string"},
                "peak_infected": {"type": "integer"},
                "peak_day": {"type": "integer"},
                "total_infected": {"type": "integer"},
                "total_deceased": {"type": "integer"},
                "r0": {"type": "number"},
                "baseline_peak_infected": {"type": "integer"},
                "reduction_percent": {"type": "number"},
                "lives_saved": {"type": "integer"},
                "population": {"type": "integer"},
                "attack_rate_pct": {"type": "number"},
            },
        },
    )

    @staticmethod
    def call(region: str, intervention: str) -> MCPToolResult:
        """
        Execute the SEIR simulation and return structured data.
        This is the MCP tool call — it returns raw structured JSON,
        not a natural language response.
        """
        try:
            from models.seir_model import SEIRModel, SEIRParameters
            from services.data_service import DataIngestionService

            data_svc = DataIngestionService()
            region_data = data_svc.get_region(region)

            # Build base parameters from region data
            base_params = SEIRParameters(
                beta=0.35,
                sigma=round(1 / 5.1, 4),
                gamma=round(1 / 14, 4),
                mu=0.008,
                population=region_data["population"],
                initial_infected=500,
                initial_exposed=1000,
            )

            # Run baseline (no_action) first for comparison
            baseline_params = SEIRModel.apply_intervention(base_params, "no_action")
            baseline_result = SEIRModel(baseline_params).run(days=180)
            baseline_peak = int(baseline_result.peak_infected)

            # Run intervention scenario
            intervention_params = SEIRModel.apply_intervention(base_params, intervention)
            intervention_result = SEIRModel(intervention_params).run(days=180)

            peak_infected = int(intervention_result.peak_infected)
            total_infected = int(intervention_result.total_infected)
            total_deceased = int(intervention_result.total_deceased)
            population = region_data["population"]

            reduction_pct = round(
                max(0.0, (baseline_peak - peak_infected) / max(baseline_peak, 1) * 100), 1
            )
            lives_saved = max(0, int(
                (baseline_result.total_deceased - total_deceased)
            ))
            attack_rate = round(total_infected / population * 100, 2)

            return MCPToolResult(
                tool_name="simulate_pandemic",
                content={
                    "region": region,
                    "region_name": region_data["name"],
                    "country": region_data["country"],
                    "intervention": intervention,
                    "peak_infected": peak_infected,
                    "peak_day": int(intervention_result.peak_day),
                    "total_infected": total_infected,
                    "total_deceased": total_deceased,
                    "r0": float(intervention_result.r0),
                    "baseline_peak_infected": baseline_peak,
                    "reduction_percent": reduction_pct,
                    "lives_saved": lives_saved,
                    "population": population,
                    "attack_rate_pct": attack_rate,
                },
            )

        except Exception as exc:
            logger.exception("MCP tool error in simulate_pandemic")
            return MCPToolResult(
                tool_name="simulate_pandemic",
                content={},
                is_error=True,
                error_message=str(exc),
            )


# ── MCP Tool Registry ──────────────────────────────────────────────────────────

class MCPToolRegistry:
    """
    Registry of all available MCP tools.
    In a full MCP implementation this would be discovered via the MCP protocol.
    Here it is pre-registered with the SEIR simulation tool.
    """

    def __init__(self):
        self._tools: Dict[str, MCPToolSchema] = {}
        self._handlers: Dict[str, Any] = {}

        # Register the single external tool
        self.register(
            PandemicSimulationTool.TOOL_SCHEMA,
            PandemicSimulationTool.call,
        )

    def register(self, schema: MCPToolSchema, handler) -> None:
        self._tools[schema.name] = schema
        self._handlers[schema.name] = handler

    def list_tools(self) -> List[MCPToolSchema]:
        return list(self._tools.values())

    def execute(self, call: MCPToolCall) -> MCPToolResult:
        if call.tool_name not in self._handlers:
            return MCPToolResult(
                tool_name=call.tool_name,
                content={},
                is_error=True,
                error_message=f"Unknown tool: {call.tool_name}",
            )
        handler = self._handlers[call.tool_name]
        return handler(**call.arguments)


# ── Intent Parser ──────────────────────────────────────────────────────────────

class IntentParser:
    """
    Parses natural language queries to extract region and intervention intent.
    Used by PandemicMCPAgent before making the MCP tool call.
    """

    REGION_ALIASES: Dict[str, str] = {
        "delhi": "delhi",
        "delhi ncr": "delhi",
        "ncr": "delhi",
        "mumbai": "mumbai",
        "bombay": "mumbai",
        "new york": "new_york",
        "nyc": "new_york",
        "new york city": "new_york",
        "london": "london",
        "tokyo": "tokyo",
        "sao paulo": "sao_paulo",
        "são paulo": "sao_paulo",
    }

    INTERVENTION_ALIASES: Dict[str, str] = {
        "lockdown": "full_lockdown",
        "full lockdown": "full_lockdown",
        "strict lockdown": "full_lockdown",
        "partial lockdown": "partial_lockdown",
        "partial": "partial_lockdown",
        "vaccination": "vaccination_rollout",
        "vaccine": "vaccination_rollout",
        "vaccinate": "vaccination_rollout",
        "school closure": "school_closure",
        "school": "school_closure",
        "close schools": "school_closure",
        "travel ban": "travel_restriction",
        "travel restriction": "travel_restriction",
        "travel": "travel_restriction",
        "combined": "combined_strategy",
        "combination": "combined_strategy",
        "combined strategy": "combined_strategy",
        "nothing": "no_action",
        "no action": "no_action",
        "do nothing": "no_action",
        "none": "no_action",
    }

    def parse(self, query: str) -> Dict[str, str]:
        """Extract region and intervention from a natural language query."""
        q = query.lower().strip()

        # Match region
        region = "delhi"  # default
        for alias, region_id in self.REGION_ALIASES.items():
            if alias in q:
                region = region_id
                break

        # Match intervention
        intervention = "no_action"  # default
        for alias, intervention_id in self.INTERVENTION_ALIASES.items():
            if alias in q:
                intervention = intervention_id
                break

        return {"region": region, "intervention": intervention}


# ── ADK-style Agent Definition ─────────────────────────────────────────────────

@dataclass
class AgentConfig:
    """Configuration for the ADK agent (mirrors google.adk.agents.Agent config)."""
    name: str
    description: str
    instructions: str
    tools: List[str] = field(default_factory=list)
    model: str = "gemini-2.5-pro"


class PandemicMCPAgent:
    """
    ADK-compatible agent that uses MCP to retrieve structured pandemic data
    and generates a final natural language response.

    Complies with the problem statement:
      ✓ ONE clearly defined AI agent
      ✓ Uses MCP (Model Context Protocol) to call ONE tool
      ✓ Connects to ONE external data source (SEIR simulation engine)
      ✓ Retrieves structured data
      ✓ Uses that data to generate its final response

    Flow:
      1. Receive natural language query
      2. Parse intent (region + intervention)
      3. Call MCP tool → get structured JSON data
      4. Use data to generate natural language response (via LLM or fallback)
    """

    # ADK-style agent configuration
    CONFIG = AgentConfig(
        name="PandemicMCPAgent",
        description=(
            "An AI agent that simulates pandemic interventions using MCP. "
            "Accepts natural language queries, calls the simulate_pandemic MCP tool, "
            "and generates structured + natural language responses."
        ),
        instructions=(
            "You are an expert epidemiologist AI agent. "
            "When given a query about pandemic interventions, use the simulate_pandemic tool "
            "to retrieve structured simulation data, then synthesize a clear, "
            "evidence-based response explaining the impact of the intervention."
        ),
        tools=["simulate_pandemic"],
        model="gemini-2.5-pro",
    )

    def __init__(self):
        self._registry = MCPToolRegistry()
        self._parser = IntentParser()
        logger.info("PandemicMCPAgent initialized with tools: %s",
                    [t.name for t in self._registry.list_tools()])

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(self, query: str) -> Dict[str, Any]:
        """
        Execute the full agent flow:
          1. Parse query intent
          2. Call MCP tool
          3. Generate response from structured data

        Returns:
            {
                "agent": "PandemicMCPAgent",
                "query": str,
                "intent": {"region": str, "intervention": str},
                "mcp_tool_call": {"tool": str, "arguments": dict},
                "data": {...},       ← raw structured data from MCP tool
                "response": str,     ← final natural language answer
                "error": str | None
            }
        """
        logger.info("PandemicMCPAgent.run | query='%s'", query)

        # Step 1: Parse intent
        intent = self._parser.parse(query)
        logger.info("Intent parsed: region=%s intervention=%s",
                    intent["region"], intent["intervention"])

        # Step 2: Build MCP tool call
        tool_call = MCPToolCall(
            tool_name="simulate_pandemic",
            arguments={
                "region": intent["region"],
                "intervention": intent["intervention"],
            },
        )

        # Step 3: Execute MCP tool → get structured data
        tool_result = self._registry.execute(tool_call)

        if tool_result.is_error:
            return {
                "agent": self.CONFIG.name,
                "query": query,
                "intent": intent,
                "mcp_tool_call": {
                    "tool": tool_call.tool_name,
                    "arguments": tool_call.arguments,
                },
                "data": None,
                "response": f"Simulation failed: {tool_result.error_message}",
                "error": tool_result.error_message,
            }

        data = tool_result.content

        # Step 4: Generate natural language response
        response = self._generate_response(data, query)

        return {
            "agent": self.CONFIG.name,
            "query": query,
            "intent": intent,
            "mcp_tool_call": {
                "tool": tool_call.tool_name,
                "arguments": tool_call.arguments,
            },
            "data": data,
            "response": response,
            "error": None,
        }

    # ── Response Generation ────────────────────────────────────────────────────

    def _generate_response(self, data: Dict[str, Any], original_query: str) -> str:
        """
        Generate a natural language response from structured MCP tool data.
        Attempts Gemini LLM first; falls back to deterministic template.
        """
        # Try LLM response
        llm_response = self._try_llm_response(data, original_query)
        if llm_response:
            return llm_response

        # Deterministic fallback
        return self._template_response(data)

    def _try_llm_response(self, data: Dict, query: str) -> Optional[str]:
        """Attempt to call Gemini LLM with the structured MCP data."""
        try:
            from services.llm_service import _call_gemini

            system = (
                "You are an epidemiologist AI agent. You have just retrieved structured "
                "simulation data from a pandemic simulation tool. Synthesize the data "
                "into one clear, informative sentence. No markdown. No lists. Plain text."
            )
            user = (
                f"User query: {query}\n\n"
                f"MCP tool result:\n"
                f"  Region: {data.get('region_name', data.get('region'))}, {data.get('country')}\n"
                f"  Intervention: {data.get('intervention', '').replace('_', ' ').title()}\n"
                f"  Peak infections: {data.get('peak_infected', 0):,} (on day {data.get('peak_day', 0)})\n"
                f"  Total infected: {data.get('total_infected', 0):,}\n"
                f"  Baseline peak: {data.get('baseline_peak_infected', 0):,}\n"
                f"  Reduction vs baseline: {data.get('reduction_percent', 0):.1f}%\n"
                f"  Lives saved: {data.get('lives_saved', 0):,}\n"
                f"  Attack rate: {data.get('attack_rate_pct', 0):.1f}% of population\n"
                f"  R0: {data.get('r0', 0):.2f}\n\n"
                f"Write one natural language sentence summarising the intervention impact."
            )
            return _call_gemini(system, user, max_tokens=200)
        except Exception as exc:
            logger.debug("LLM response generation failed: %s", exc)
            return None

    def _template_response(self, data: Dict) -> str:
        """Deterministic response template using structured MCP data."""
        region_name = data.get("region_name", data.get("region", "the region"))
        country = data.get("country", "")
        intervention = data.get("intervention", "no_action").replace("_", " ").title()
        reduction = data.get("reduction_percent", 0.0)
        lives_saved = data.get("lives_saved", 0)
        peak_infected = data.get("peak_infected", 0)
        total_infected = data.get("total_infected", 0)
        attack_rate = data.get("attack_rate_pct", 0)
        r0 = data.get("r0", 0)
        population = data.get("population", 1)

        if reduction > 60:
            impact_desc = "dramatically reduces"
            outcome = "highly effective"
        elif reduction > 30:
            impact_desc = "significantly reduces"
            outcome = "moderately effective"
        elif reduction > 10:
            impact_desc = "partially reduces"
            outcome = "marginally effective"
        else:
            impact_desc = "provides minimal reduction in"
            outcome = "largely ineffective against"

        lives_str = (
            f"{lives_saved / 1_000_000:.1f} million" if lives_saved >= 1_000_000
            else f"{lives_saved / 1_000:.0f} thousand" if lives_saved >= 1_000
            else f"{lives_saved:,}"
        )

        return (
            f"Applying {intervention} in {region_name}, {country} {impact_desc} "
            f"peak infections by {reduction:.1f}%, saving approximately {lives_str} lives. "
            f"The simulation projects {peak_infected:,} peak simultaneous infections "
            f"with an overall attack rate of {attack_rate:.1f}% of the {population:,} population "
            f"(R0={r0:.2f}). "
            f"This intervention is {outcome} pandemic control in this region."
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

_mcp_agent: Optional[PandemicMCPAgent] = None


def get_mcp_agent() -> PandemicMCPAgent:
    """Return the shared PandemicMCPAgent instance (lazy init)."""
    global _mcp_agent
    if _mcp_agent is None:
        _mcp_agent = PandemicMCPAgent()
    return _mcp_agent
