"""Typed data surfaces for the NEXUS Visual Weaver dashboard."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class CreativeRequest:
    prompt: str
    output_goal: str = "image_to_video"
    adult_mode: bool = False
    references: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class TasteProfile:
    version: str
    locked_features: dict[str, Any]
    must_include: list[str]
    should_include: list[str]
    forbidden: list[str]


@dataclass(frozen=True)
class TasteRefinedPrompt:
    original: str
    refined: str
    additions: list[str]
    score: float
    missing_features: list[str]


@dataclass(frozen=True)
class WardrobeSlot:
    name: str
    description: str
    material: str
    palette: str
    lora_hint: str
    locked: bool = False
    adult_only: bool = False
    locate_region: str = "pending"
    edit_priority: int = 3


@dataclass(frozen=True)
class OutfitGraph:
    slots: list[WardrobeSlot]
    score: float

    @property
    def locked_count(self) -> int:
        return sum(1 for slot in self.slots if slot.locked)


@dataclass(frozen=True)
class ModelCandidate:
    repo_id: str
    role: str
    task: str
    params_b: float
    runtime: str
    license: str
    gated: bool = False
    adult_only: bool = False
    public_demo: bool = True
    source_url: str = ""


@dataclass(frozen=True)
class AdapterRecipe:
    repo_id: str
    adapter_for: str
    task: str
    weight: float = 0.75
    license: str = "unknown"
    adult_only: bool = False
    compatibility: str = "compatible"


@dataclass(frozen=True)
class GroundingTarget:
    slot_name: str
    query: str
    expected_region: str
    confidence: float


@dataclass(frozen=True)
class InspectionReport:
    status: str
    targets: list[GroundingTarget]
    drift_flags: list[str]
    locate_model: str = "nvidia/LocateAnything-3B"


@dataclass(frozen=True)
class LoreBeatSet:
    beats: list[dict[str, str]]
    tone: str


@dataclass(frozen=True)
class VideoPlan:
    preset: str
    source: str
    camera_move: str
    duration_seconds: float
    fps: int
    continuity_locks: list[str]
    checkpoint_required: bool = True


@dataclass(frozen=True)
class HumanCheckpoint:
    checkpoint_id: str
    recommendation: str
    trust_score: float
    required_actions: list[str]


@dataclass(frozen=True)
class GenerationRun:
    request: CreativeRequest
    refined_prompt: TasteRefinedPrompt
    outfit: OutfitGraph
    model_stack: list[ModelCandidate]
    adapters: list[AdapterRecipe]
    inspection: InspectionReport
    lore: LoreBeatSet
    video: VideoPlan
    checkpoint: HumanCheckpoint
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WisdomRecord:
    run_id: str
    approved: bool
    dataset_target: str
    lessons: list[str]
    created_at: str = field(default_factory=utc_now)
