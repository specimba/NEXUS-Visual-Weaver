"""Wardrobe slot extraction and validation."""

from __future__ import annotations

from .schema import OutfitGraph, WardrobeSlot

SLOT_BLUEPRINTS: list[tuple[str, str, str, str, str]] = [
    ("hair_headwear", "sleek hair or sculptural headwear", "hair / metal", "obsidian with neon edge", "identity lock"),
    ("upper_body", "structured bodice or fitted top", "chantilly_lace", "black lace and mesh", "lace / mesh adapter"),
    ("outerwear", "long technical coat or jacket", "patent_leather", "jet black", "FLUX.2 material texture"),
    ("hands", "gloves with interface details", "patent_leather", "black with crimson nodes", "detail LoRA"),
    ("lower_body", "tailored lower silhouette", "layered_garments", "dark graphite", "garment consistency"),
    ("footwear", "strong platform boots", "polished_leather", "matte black sole", "boot detail"),
    ("jewelry", "choker, buckles, and hard points", "crimson_hardware", "crimson metal", "hardware glow"),
    ("props", "holographic sigils and data tools", "holographic_glass", "cyan and magenta", "NEXUS glyphs"),
    ("background_context", "rain, code, and location atmosphere", "neon_rain", "obsidian/cyan/crimson", "environmental continuity"),
]


def build_outfit_graph(prompt: str, adult_mode: bool = False, controls: dict | None = None) -> OutfitGraph:
    lowered = prompt.lower()
    controls = controls or {}
    locked_slots = set(controls.get("locked_slots") or [])
    locate_focus = set(controls.get("locate_focus") or [])
    slots: list[WardrobeSlot] = []
    for index, (name, description, material, palette, lora_hint) in enumerate(SLOT_BLUEPRINTS):
        if name == "outerwear" and controls.get("outerwear"):
            description = str(controls["outerwear"])
        if name == "upper_body" and controls.get("upper_body"):
            material = str(controls["upper_body"])
        if name == "footwear" and controls.get("footwear"):
            description = str(controls["footwear"])
        if name == "jewelry" and controls.get("hardware"):
            material = str(controls["hardware"])
        if controls.get("palette"):
            palette = str(controls["palette"])
        locked = any(token in lowered for token in name.split("_")) or material.replace("_", " ") in lowered
        if name == "outerwear" and "coat" in lowered:
            locked = True
        if name == "footwear" and ("boot" in lowered or "platform" in lowered):
            locked = True
        if name == "jewelry" and ("crimson" in lowered or "hardware" in lowered):
            locked = True
        if name in locked_slots:
            locked = True
        slots.append(
            WardrobeSlot(
                name=name,
                description=description,
                material=material,
                palette=palette,
                lora_hint=lora_hint,
                locked=locked,
                adult_only=False if not adult_mode else name in {"upper_body", "lower_body"},
                locate_region="manual-focus" if name in locate_focus else "auto-map",
                edit_priority=max(1, 5 - index // 2),
            )
        )
    locked_count = sum(1 for slot in slots if slot.locked)
    score = round(0.68 + min(0.24, locked_count * 0.035), 2)
    return OutfitGraph(slots=slots, score=score)
