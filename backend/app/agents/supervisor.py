from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.agents.data_agent_service import ask_data_agent


# Information shared between agents
class AgentState(TypedDict):
    message: str
    answer: str


# Our existing Data Agent
def data_agent_node(state: AgentState):
    answer = ask_data_agent(state["message"])
    return {"answer": answer}


# Build the workflow
workflow = StateGraph(AgentState)

workflow.add_node("data_agent", data_agent_node)

workflow.add_edge(START, "data_agent")
workflow.add_edge("data_agent", END)

supervisor = workflow.compile()