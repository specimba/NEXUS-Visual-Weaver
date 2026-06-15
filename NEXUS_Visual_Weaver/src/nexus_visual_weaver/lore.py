"""Lore beat and checkpointed video planning."""

from __future__ import annotations

from .schema import LoreBeatSet, VideoPlan


def build_lore_beats(prompt: str) -> LoreBeatSet:
    seed = prompt.strip()[:90] or "The Archivist enters the neon archive."
    beats = [
        {"id": "01", "title": "The Archivist", "cue": seed},
        {"id": "02", "title": "Neon Gates", "cue": "rain-lit threshold, NEXUS glyphs waking in the glass"},
        {"id": "03", "title": "The Confrontation", "cue": "wardrobe details and crimson hardware become identity anchors"},
        {"id": "04", "title": "Shattered Truth", "cue": "LocateAnything confirms outfit continuity under motion"},
        {"id": "05", "title": "Raven's Choice", "cue": "human checkpoint decides whether to promote the run"},
        {"id": "06", "title": "Into the Rain", "cue": "video path locks the final camera move and frame pacing"},
    ]
    return LoreBeatSet(beats=beats, tone="gothic couture cyberpunk / controlled cinematic tension")


def build_video_plan(preset: str = "Wan2.2 I2V") -> VideoPlan:
    if "LTX" in preset:
        return VideoPlan(
            preset="LTX-2.3",
            source="approved image candidate",
            camera_move="slow parallax push with fabric and rain continuity locks",
            duration_seconds=5.3,
            fps=24,
            continuity_locks=["wardrobe slots", "face/pose", "crimson hardware", "rain direction"],
        )
    return VideoPlan(
        preset="Wan2.2 I2V",
        source="approved image candidate",
        camera_move="controlled dolly-in with coat, lace, boots, and code-stream stabilization",
        duration_seconds=4.8,
        fps=24,
        continuity_locks=["outerwear", "footwear", "jewelry", "NEXUS sigils"],
    )

