from .base import AgentContext, AgentOutput, BaseAgent
from .greeting_agent import GreetingAgent
from .identity_agent import IdentityAgent
from .memory_agent import MemoryAgent
from .project_agent import ProjectAgent
from .recovery_agent import RecoveryAgent
from .research_agent import ResearchAgent


RAW_AGENTS = {
    "identity_agent": IdentityAgent(),
    "project_agent": ProjectAgent(),
    "greeting_agent": GreetingAgent(),
    "memory_agent": MemoryAgent(),
    "research_agent": ResearchAgent(),
    "recovery_agent": RecoveryAgent(),
}


def _registration_context() -> AgentContext:
    return AgentContext(
        query="registry admission check",
        intent="knowledge_lookup",
        route={"intent": "knowledge_lookup", "agent": "research_agent"},
        results=[],
        execution_plan={"goal": "admission", "steps": ["validate"]},
        conversation_state={"is_follow_up": False, "plan_shifted": False},
        active_goal=None,
    )


def _validate_agent(name: str, agent: BaseAgent) -> list[str]:
    errors: list[str] = []

    if not isinstance(agent, BaseAgent):
        errors.append("must inherit from BaseAgent")

    execute_fn = getattr(type(agent), "execute", None)
    if execute_fn is None or execute_fn is BaseAgent.execute:
        errors.append("must implement execute()")

    capabilities = getattr(agent, "capabilities", None)
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("must define non-empty capabilities list")

    if not hasattr(agent, "name") or getattr(agent, "name", "") != name:
        errors.append("agent.name must match registry key")

    # Admission runtime contract check: execute() must return AgentOutput.
    try:
        output = agent.execute(_registration_context())
        if not isinstance(output, AgentOutput):
            errors.append("execute() must return AgentOutput")
    except Exception as exc:
        errors.append(f"execute() failed during admission check: {exc}")

    return errors


def _admit_agents(raw_agents: dict[str, BaseAgent]) -> dict[str, BaseAgent]:
    admitted: dict[str, BaseAgent] = {}
    rejected: dict[str, list[str]] = {}

    for name, agent in raw_agents.items():
        errors = _validate_agent(name, agent)
        if errors:
            rejected[name] = errors
            continue
        admitted[name] = agent

    if rejected:
        parts = []
        for name, errors in rejected.items():
            parts.append(f"{name}: {', '.join(errors)}")
        raise TypeError("Registry admission policy rejected agent(s): " + " | ".join(parts))

    return admitted


AGENTS = _admit_agents(RAW_AGENTS)


def _describe(agent: BaseAgent) -> dict:
    return {
        "description": f"Executes {agent.name} tasks.",
        "primary_sources": getattr(agent, "primary_sources", []),
        "capabilities": getattr(agent, "capabilities", []),
    }


AGENT_CAPABILITIES = {name: _describe(agent) for name, agent in AGENTS.items()}
