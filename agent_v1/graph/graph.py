"""
Generation graph: planner -> architect -> coder (looped until done).

This module only wires the graph together. LLM setup lives in
agent_v1.graph.llm, node logic in agent_v1.graph.nodes, state shapes in
agent_v1.graph.states.
"""

import logging
import os

from dotenv import load_dotenv
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent_v1.graph.nodes import architect_agent, coder_agent, planner_agent
from agent_v1.graph.states import GraphState

logger = logging.getLogger("agentbay.graph")


def init_environment() -> None:
    """
    Initialize environment variables once. Safe to call multiple times.
    """
    os.environ.setdefault("LANGSMITH_TRACING", "false")
    load_dotenv()


def _coder_next_step(state: GraphState) -> str:
    return "END" if state.get("status") == "DONE" else "coder"


def build_graph() -> CompiledStateGraph:
    """
    Builds and compiles the generation graph. Safe to reuse across API
    calls - it holds no per-run state itself.
    """
    graph = StateGraph(GraphState)

    graph.add_node("planner", planner_agent)
    graph.add_node("architect", architect_agent)
    graph.add_node("coder", coder_agent)

    graph.add_edge("planner", "architect")
    graph.add_edge("architect", "coder")

    graph.add_conditional_edges(
        "coder",
        _coder_next_step,
        {"END": END, "coder": "coder"},
    )

    graph.set_entry_point("planner")

    return graph.compile()


def run_agent(user_prompt: str) -> GraphState:
    """
    Public callable entry point. This is what the API calls.
    """
    init_environment()
    logger.info("run_agent: starting generation")

    agent = build_graph()
    result = agent.invoke({"user_prompt": user_prompt})

    logger.info("run_agent: finished with status=%s", result.get("status"))
    return result


# Local CLI Test
if __name__ == "__main__":
    final_state = run_agent("build an 404 error page using internal css and html")

    print("Final State:")
    print(final_state)
