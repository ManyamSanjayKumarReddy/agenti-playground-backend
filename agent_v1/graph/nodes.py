"""
Agent nodes for the generation graph: planner -> architect -> coder.
"""

import logging

from agent_v1.graph.llm import get_llm, invoke_structured_with_retry
from agent_v1.graph.states import CoderState, FileContent, GraphState, Plan, TaskPlan
from agent_v1.prompts.prompts import architect_prompt, coder_system_prompt, planner_prompt
from agent_v1.tools.filesystem import read_file, set_project_root, write_file
from agent_v1.tools.project_root import create_project_root

logger = logging.getLogger("agentbay.graph")


def planner_agent(state: GraphState) -> GraphState:
    """
    Converts the user's prompt into a structured Plan.
    """
    user_prompt = state["user_prompt"]
    logger.info("planner: starting")

    plan = invoke_structured_with_retry(get_llm(), Plan, planner_prompt(user_prompt))
    if not plan:
        raise ValueError("Planner agent returned empty output")

    logger.info("planner: done, name=%s, files=%d", plan.name, len(plan.files))
    return {"plan": plan}


def architect_agent(state: GraphState) -> GraphState:
    """
    Converts the Plan into an ordered TaskPlan.
    """
    plan = state["plan"]
    logger.info("architect: starting for plan=%s", plan.name)

    task_plan = invoke_structured_with_retry(get_llm(), TaskPlan, architect_prompt(plan))
    if not task_plan:
        raise ValueError("Architect agent returned empty output")

    logger.info(
        "architect: done, %d implementation steps",
        len(task_plan.implementation_steps),
    )
    return {"plan": plan, "task_plan": task_plan}


def coder_agent(state: GraphState) -> GraphState:
    """
    Single-action-per-step coding agent.

    Deliberately does NOT use tool-calling / bound tools: some
    OpenAI-compatible gateways (self-hosted vLLM serving gpt-oss, in
    particular) don't reliably support multi-turn function-calling yet.
    Structured output (used here, same as planner/architect) doesn't hit
    that code path and has been more reliable in practice, so this step
    reads the existing file itself, asks the model only for the new
    content, and writes it itself - the model never needs to invoke
    anything.
    """
    coder_state = state.get("coder_state")

    if coder_state is None:
        project_dir = create_project_root(state["plan"].name)
        coder_state = CoderState(
            task_plan=state["task_plan"],
            project_root=str(project_dir),
            current_step_idx=0,
        )
        logger.info("coder: created project root %s", coder_state.project_root)

    set_project_root(coder_state.project_root)

    steps = coder_state.task_plan.implementation_steps

    if coder_state.current_step_idx >= len(steps):
        logger.info("coder: all %d steps complete", len(steps))
        return {"coder_state": coder_state, "status": "DONE"}

    current_task = steps[coder_state.current_step_idx]
    step_num = coder_state.current_step_idx + 1
    logger.info(
        "coder: step %d/%d, file=%s",
        step_num,
        len(steps),
        current_task.filepath,
    )

    existing_content = read_file.run(current_task.filepath)

    user_prompt = (
        f"Task: {current_task.task_description}\n"
        f"File: {current_task.filepath}\n\n"
        f"Existing Content:\n{existing_content}\n\n"
        "Respond with the complete file content."
    )

    result = invoke_structured_with_retry(
        get_llm(),
        FileContent,
        [
            {"role": "system", "content": coder_system_prompt()},
            {"role": "user", "content": user_prompt},
        ],
    )
    if not result:
        raise ValueError("Coder agent returned empty output")

    write_file.run({"path": current_task.filepath, "content": result.content})
    logger.info("coder: step %d/%d wrote %s", step_num, len(steps), current_task.filepath)

    coder_state.current_step_idx += 1
    return {"coder_state": coder_state}
