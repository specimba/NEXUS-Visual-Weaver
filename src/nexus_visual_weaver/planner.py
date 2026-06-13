"""High-level command-center orchestration."""

from __future__ import annotations

from uuid import uuid4

from .catalog import ADAPTER_CATALOG, active_stack
from .grounding import inspect_outfit
from .lore import build_lore_beats, build_video_plan
from .schema import CreativeRequest, GenerationRun, HumanCheckpoint
from .taste import refine_prompt
from .wardrobe import build_outfit_graph


def build_command_center_run(
    prompt: str,
    mode: str = "Strict",
    video_preset: str = "Wan2.2 I2V",
    adult_mode: bool = False,
) -> GenerationRun:
    request = CreativeRequest(prompt=prompt, adult_mode=adult_mode)
    refined = refine_prompt(prompt, adult_mode=adult_mode)
    outfit = build_outfit_graph(refined.refined, adult_mode=adult_mode)
    inspection = inspect_outfit(outfit)
    lore = build_lore_beats(refined.refined)
    video = build_video_plan(video_preset)
    stack = active_stack(adult_mode)
    adapters = [adapter for adapter in ADAPTER_CATALOG if adult_mode or not adapter.adult_only][:4]
    trust_score = round((refined.score + outfit.score + (0.86 if inspection.status == "pass" else 0.72)) / 3, 2)
    required_actions = []
    if adult_mode:
        required_actions.append("Confirm 18+ session scope and keep exports partitioned")
    if inspection.drift_flags:
        required_actions.extend(inspection.drift_flags)
    if mode.lower().startswith("frontier"):
        required_actions.append("Frontier mode requires human checkpoint before video render")

    checkpoint = HumanCheckpoint(
        checkpoint_id=f"nw-{uuid4().hex[:8]}",
        recommendation="approve_candidate" if trust_score >= 0.78 else "revise_before_generation",
        trust_score=trust_score,
        required_actions=required_actions or ["Review candidate thumbnails before promotion"],
    )
    return GenerationRun(
        request=request,
        refined_prompt=refined,
        outfit=outfit,
        model_stack=stack,
        adapters=adapters,
        inspection=inspection,
        lore=lore,
        video=video,
        checkpoint=checkpoint,
    )

