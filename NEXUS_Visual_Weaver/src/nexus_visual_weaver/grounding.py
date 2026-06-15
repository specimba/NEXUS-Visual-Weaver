"""LocateAnything-style grounding simulation for planning and UI state."""

from __future__ import annotations

from .schema import GroundingTarget, InspectionReport, OutfitGraph


def inspect_outfit(outfit: OutfitGraph) -> InspectionReport:
    targets: list[GroundingTarget] = []
    for slot in outfit.slots:
        if slot.name in {"outerwear", "upper_body", "footwear", "jewelry", "background_context"}:
            confidence = 0.92 if slot.locked else 0.78
            targets.append(
                GroundingTarget(
                    slot_name=slot.name,
                    query=f"locate {slot.description}",
                    expected_region=slot.locate_region,
                    confidence=confidence,
                )
            )

    drift_flags: list[str] = []
    if not any(slot.name == "footwear" and slot.locked for slot in outfit.slots):
        drift_flags.append("footwear requires stronger prompt lock")
    if outfit.score < 0.78:
        drift_flags.append("material contrast needs refinement before render")

    return InspectionReport(
        status="pass" if not drift_flags else "review",
        targets=targets,
        drift_flags=drift_flags,
    )

