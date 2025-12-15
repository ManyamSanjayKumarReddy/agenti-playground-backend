from dotenv import load_dotenv
# from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langchain.agents import create_agent
from langgraph.constants import END
from states import File, Plan, TaskPlan, CoderState
from prompts import planner_prompt, architect_prompt, coder_system_prompt
from tools import *
import os

os.environ["LANGSMITH_TRACING"] = "true"
_ = load_dotenv()

# llm = ChatGroq(model='openai/gpt-oss-120b')
llm = ChatOpenAI(
    model="gpt-4o-mini-2024-07-18",
    temperature=0.6
)

def planner_agent(state :dict) -> dict:
    """Converts user prompt into a structured plan."""
    user_prompt = state['user_prompt']
    resp = llm.with_structured_output(Plan).invoke(
        planner_prompt(user_prompt)
    )

    if resp is None:
        raise ValueError("Planner did not return a valid response")

    return {"plan": resp}

def architect_agent(state: dict) -> dict:
    """Creates TasksPlan from Plan"""
    plan: Plan = state['plan']
    resp = llm.with_structured_output(TaskPlan).invoke(architect_prompt(plan))

    if resp is None:
        raise ValueError("Planner did not return a valid response.")

    # resp.plan = plan
    return {"task_plan": resp}

def coder_agent(state: dict) -> dict:
    """Langgraph tool-using coder agent_v0"""
    coder_state : CoderState = state.get("coder_state")

    if coder_state is None:
        coder_state = CoderState(task_plan=state['task_plan'], current_step_idx=0)

    steps = coder_state.task_plan.implementation_steps
    if coder_state.current_step_idx >= len(steps):
        return {"coder_state": coder_state, "status": "DONE"}

    current_task = steps[coder_state.current_step_idx]
    existing_content = read_file.run(current_task.filepath)

    system_prompt = coder_system_prompt()
    user_prompt = (
        f"Task: {current_task.task_description}\n"
        f"File: {current_task.filepath}\n"
        f"Existing Content: \n{existing_content}\n"
        "Use write_file(path, content) to save your changes."
    )

    coder_tools = [read_file, write_file, list_files, get_current_directory]
    coding_agent = create_agent(
        model=llm,
        tools=coder_tools,
        system_prompt=system_prompt
    )

    coding_agent.invoke(
        {"messages": [{"role": "user", "content": user_prompt}]}
    )
    coder_state.current_step_idx += 1
    return {"coder_state": coder_state}

graph = StateGraph(dict)

graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coder_agent)

graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")
graph.add_conditional_edges(
    "coder",
    lambda s: "END" if s.get('status') == "DONE" else "coder",
    {"END": END, "coder": "coder"}
)

graph.set_entry_point("planner")
agent = graph.compile()


if __name__ == "__main__":
    result = agent.invoke({"user_prompt": "landing page design for a startup company which focus on web dev , ai agent_v0 and more services and its is based on chennai india with proper and clean ui in html css and js"})
    print("Final State: ", result)