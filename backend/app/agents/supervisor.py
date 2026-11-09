"""Bounded LangGraph Supervisor with explicit plans and capability availability."""

import logging
from collections.abc import Callable, Mapping
from typing import Literal, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.data_agent_service import ask_data_agent
from app.agents.routing import HELP, plan_request
from app.schemas import (
    AgentName,
    AgentResult,
    AgentTask,
    ChatRequest,
    RoutingPlan,
    SupervisorResponse,
    WorkflowEvent,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)
MAX_AGENT_STEPS = 3
GRAPH_RECURSION_LIMIT = 8  # route + at most three tasks + finalize, with headroom
UNAVAILABLE = {
    "research": (
        "Document retrieval is not implemented; "
        "no policy evidence or eligibility decision is available."
    ),
    "action": (
        "Action drafting and approvals are not implemented; "
        "no email, refund, or business change was prepared or executed."
    ),
}


class AgentState(TypedDict, total=False):
    message: str
    workflow_id: str
    plan: RoutingPlan
    next_task: int
    results: list[AgentResult]
    events: list[WorkflowEvent]
    status: WorkflowStatus
    answer: str


# A handler receives a task and completed evidence. Register future capabilities
# through this interface only when they really work.
AgentHandler = Callable[[AgentTask, tuple[AgentResult, ...]], str]


def _data_handler(task: AgentTask, evidence: tuple[AgentResult, ...]) -> str:
    return ask_data_agent(task.request)


def _event(
    events: list[WorkflowEvent],
    node: Literal["route", "execute", "finalize"],
    status: str,
    detail: str,
    agent: AgentName | None = None,
) -> WorkflowEvent:
    return WorkflowEvent(
        sequence=len(events) + 1, node=node, status=status, detail=detail, agent=agent
    )


def build_supervisor(
    handlers: Mapping[AgentName, AgentHandler] | None = None,
    planner: Callable[[str], RoutingPlan] = plan_request,
):
    registry = dict(handlers) if handlers is not None else {"data": _data_handler}

    def route(state: AgentState) -> AgentState:
        # Also validate direct graph.invoke users, not only HTTP requests.
        message = ChatRequest(message=state["message"]).message
        workflow_id = str(uuid4())
        try:
            plan = RoutingPlan.model_validate(planner(message))
            status = "completed"
        except Exception:
            # Never log raw prompts, credentials, SDK errors, or database URLs.
            logger.warning("supervisor_routing_failed workflow_id=%s", workflow_id)
            plan = RoutingPlan(
                method="clarification", explanation="Routing failed. Please retry the request.",
                limitations=["The routing service is unavailable; no agents were invoked."],
            )
            status = "failed"
        return {
            "message": message, "workflow_id": workflow_id, "plan": plan,
            "next_task": 0, "results": [],
            "events": [_event([], "route", status, plan.explanation)],
            "status": "failed" if status == "failed" else "unsupported", "answer": "",
        }

    def next_node(state: AgentState) -> Literal["execute", "finalize"]:
        if state["next_task"] < min(len(state["plan"].tasks), MAX_AGENT_STEPS):
            return "execute"
        return "finalize"

    def execute(state: AgentState) -> AgentState:
        task = state["plan"].tasks[state["next_task"]]
        completed = tuple(r for r in state["results"] if r.status == "completed")
        handler = registry.get(task.agent)
        if handler is None:
            result = AgentResult(
                agent=task.agent, status="unavailable", error_code="capability_unavailable",
                answer=UNAVAILABLE.get(task.agent, "This agent is unavailable."),
            )
        elif not set(task.depends_on) <= {r.agent for r in completed}:
            result = AgentResult(
                agent=task.agent, status="blocked", error_code="dependency_unavailable",
                answer="Required evidence is unavailable; this step was not executed.",
            )
        else:
            try:
                answer = handler(task, completed)
                if not isinstance(answer, str) or not answer.strip():
                    raise RuntimeError("Empty agent answer")
                result = AgentResult(agent=task.agent, status="completed", answer=answer)
            except Exception:
                logger.warning(
                    "supervisor_agent_failed workflow_id=%s agent=%s",
                    state["workflow_id"], task.agent,
                )
                result = AgentResult(
                    agent=task.agent, status="failed", error_code="agent_failed",
                    answer=f"The {task.agent} agent could not complete this step. Please retry.",
                )
        event = _event(
            state["events"], "execute", result.status,
            f"{task.agent} step {result.status}.", task.agent,
        )
        return {
            "next_task": state["next_task"] + 1,
            "results": [*state["results"], result],
            "events": [*state["events"], event],
        }

    def finalize(state: AgentState) -> AgentState:
        results = state["results"]
        completed = [r for r in results if r.status == "completed"]
        if state["status"] == "failed":
            status = "failed"
        elif completed:
            status = (
                "completed" if len(completed) == len(results) and not state["plan"].limitations
                else "partial"
            )
        elif any(r.status == "failed" for r in results):
            status = "failed"
        else:
            status = "unsupported"
        # Preserve results without a model call inventing policy conclusions.
        sections = [f"{r.agent.capitalize()} agent: {r.answer}" for r in results]
        sections.extend(state["plan"].limitations)
        if not sections:
            sections.append(HELP)
        event = _event(state["events"], "finalize", status, f"Workflow {status}.")
        logger.info("supervisor_finished workflow_id=%s status=%s", state["workflow_id"], status)
        return {
            "answer": "\n\n".join(sections), "status": status,
            "events": [*state["events"], event],
        }

    workflow = StateGraph(AgentState)
    workflow.add_node("route", route)
    workflow.add_node("execute", execute)
    workflow.add_node("finalize", finalize)
    workflow.add_edge(START, "route")
    destinations = {"execute": "execute", "finalize": "finalize"}
    workflow.add_conditional_edges("route", next_node, destinations)
    workflow.add_conditional_edges("execute", next_node, destinations)
    workflow.add_edge("finalize", END)
    return workflow.compile().with_config({"recursion_limit": GRAPH_RECURSION_LIMIT})


# Preserve supervisor.invoke({"message": ...}) compatibility.
supervisor = build_supervisor()


def run_supervisor(message: str) -> SupervisorResponse:
    state = supervisor.invoke({"message": message})
    return SupervisorResponse(
        workflow_id=state["workflow_id"], status=state["status"], answer=state["answer"],
        routing=state["plan"], results=state["results"], events=state["events"],
    )
