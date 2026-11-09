"""Validated API and workflow contracts shared by routing and execution."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AgentName = Literal["data", "research", "action"]
WorkflowStatus = Literal["completed", "partial", "unsupported", "failed"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message must contain non-whitespace characters")
        return value.strip()


class AgentTask(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    agent: AgentName
    request: str = Field(min_length=1, max_length=2000)
    depends_on: list[AgentName] = Field(default_factory=list, max_length=2)


class RoutingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["deterministic", "model", "clarification"]
    tasks: list[AgentTask] = Field(default_factory=list, max_length=3)
    explanation: str
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dependencies(self):
        seen: set[AgentName] = set()
        for task in self.tasks:
            if task.agent in seen or not set(task.depends_on) <= seen:
                raise ValueError("Agents must be unique with dependencies preceding them")
            seen.add(task.agent)
        return self


class AgentResult(BaseModel):
    agent: AgentName
    status: Literal["completed", "unavailable", "blocked", "failed"]
    answer: str = ""
    error_code: str | None = None


class WorkflowEvent(BaseModel):
    sequence: int
    node: Literal["route", "execute", "finalize"]
    status: str
    agent: AgentName | None = None
    detail: str


class SupervisorResponse(BaseModel):
    workflow_id: UUID
    status: WorkflowStatus
    answer: str
    routing: RoutingPlan
    results: list[AgentResult]
    events: list[WorkflowEvent]
