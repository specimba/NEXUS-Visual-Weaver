"""NEXUS Visual Weaver command-center package."""

from .catalog import DEFAULT_ACTIVE_STACK, catalog_summary, filter_catalog, parameter_budget
from .model_relay import ContextPacket, LaneDecision, ModelRecord, WeaverModelRelay
from .planner import build_command_center_run
from .schema import (
    AdapterRecipe,
    CreativeRequest,
    GenerationRun,
    GroundingTarget,
    HumanCheckpoint,
    InspectionReport,
    LoreBeatSet,
    ModelCandidate,
    OutfitGraph,
    TasteProfile,
    TasteRefinedPrompt,
    VideoPlan,
    WardrobeSlot,
    WisdomRecord,
)

__all__ = [
    "AdapterRecipe",
    "CreativeRequest",
    "GenerationRun",
    "GroundingTarget",
    "HumanCheckpoint",
    "InspectionReport",
    "LoreBeatSet",
    "ModelCandidate",
    "OutfitGraph",
    "TasteProfile",
    "TasteRefinedPrompt",
    "VideoPlan",
    "WardrobeSlot",
    "WisdomRecord",
    "ContextPacket",
    "DEFAULT_ACTIVE_STACK",
    "LaneDecision",
    "ModelRecord",
    "WeaverModelRelay",
    "build_command_center_run",
    "catalog_summary",
    "filter_catalog",
    "parameter_budget",
]
