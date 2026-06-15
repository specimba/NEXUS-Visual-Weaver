"""Small deterministic workflow state model for the dashboard graph."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkflowNode:
    id: str
    title: str
    lane: str
    status: str = "pending"
    score: float | None = None


@dataclass
class WorkflowState:
    nodes: list[WorkflowNode] = field(default_factory=list)
    paused_at: str = "human_checkpoint"

    @classmethod
    def default(cls) -> "WorkflowState":
        return cls(
            nodes=[
                WorkflowNode("seed", "Seed Prompt", "Creative", "complete"),
                WorkflowNode("refine", "Refine", "Creative", "complete", 0.86),
                WorkflowNode("judge", "Judge", "Model", "complete", 0.84),
                WorkflowNode("locate", "Locate", "Grounding", "complete", 0.88),
                WorkflowNode("generate", "Generate", "Model", "ready"),
                WorkflowNode("video", "Video Path", "Output", "ready"),
                WorkflowNode("checkpoint", "Human Checkpoint", "Guardrail", "paused"),
            ]
        )

