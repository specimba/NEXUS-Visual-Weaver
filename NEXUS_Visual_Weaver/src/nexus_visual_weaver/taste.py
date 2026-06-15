"""Taste profile loading and deterministic scoring."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .schema import TasteProfile, TasteRefinedPrompt

DEFAULT_TASTE_PATH = Path(__file__).resolve().parents[2] / "assets" / "taste_profile.json"

FEATURE_ALIASES: dict[str, tuple[str, ...]] = {
    "patent_leather": ("patent leather", "gloss leather", "black leather", "latex-tech"),
    "faux_fur": ("faux fur", "fur trim", "black fur", "fur collar"),
    "chantilly_lace": ("chantilly lace", "lace", "lace mesh", "lace threads"),
    "crimson_hardware": ("crimson hardware", "red metal", "red buckles", "crimson buckles", "red choker"),
    "platform_boots": ("platform boots", "platform boot", "heavy boots", "tall boots"),
    "slavic_model": ("slavic", "high cheekbones", "pale matte skin", "intense focused eyes"),
    "nexus_sigils": ("nexus sigil", "nexus sigils", "orchestrator glyph", "node glyph"),
    "rain_slicked_surfaces": ("rain", "rain-slicked", "wet pavement", "neon rain"),
    "floating_code_data_streams": ("floating code", "data streams", "code streams"),
}


def load_taste_profile(path: Path | str = DEFAULT_TASTE_PATH) -> TasteProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rules = data.get("enforcement_rules", {})
    return TasteProfile(
        version=data.get("version", "unknown"),
        locked_features=data.get("locked_features", {}),
        must_include=rules.get("must_include", []),
        should_include=rules.get("should_include", []),
        forbidden=rules.get("forbidden", []),
    )


def _has_alias(text: str, aliases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(alias)}\b", lowered) for alias in aliases)


def score_prompt(prompt: str) -> tuple[float, list[str], list[str]]:
    found: list[str] = []
    missing: list[str] = []
    for feature, aliases in FEATURE_ALIASES.items():
        if _has_alias(prompt, aliases):
            found.append(feature)
        else:
            missing.append(feature)

    must = ["patent_leather", "crimson_hardware", "platform_boots", "slavic_model"]
    must_hits = sum(1 for feature in must if feature in found)
    optional_hits = len(found) - must_hits
    score = min(0.98, 0.38 + must_hits * 0.11 + optional_hits * 0.045)
    return round(score, 2), missing, found


def refine_prompt(prompt: str, adult_mode: bool = False) -> TasteRefinedPrompt:
    additions: list[str] = []
    score, missing, _ = score_prompt(prompt)
    supplement_map = {
        "patent_leather": "rich black patent leather with visible grain and wet reflections",
        "faux_fur": "dense black faux fur trim at collar and cuffs",
        "chantilly_lace": "delicate Chantilly lace mesh at neckline and sleeves",
        "crimson_hardware": "glowing crimson hardware on buckles, choker, and closures",
        "platform_boots": "structured platform boots with polished black soles",
        "slavic_model": "Slavic model features with high cheekbones and intense focused eyes",
        "nexus_sigils": "subtle NEXUS sigils and orchestrator node glyphs woven into holographic streams",
        "rain_slicked_surfaces": "rain-slicked cinematic surfaces under cyan and magenta neon",
        "floating_code_data_streams": "floating code and iridescent data streams in the background",
    }
    for feature in missing:
        if feature in supplement_map and len(additions) < 6:
            additions.append(supplement_map[feature])

    mode_clause = "adult catalog remains opt-in and partitioned" if adult_mode else "public-safe presentation"
    refined = " ".join(
        part.strip()
        for part in [prompt.strip(), ", ".join(additions), mode_clause, "ultra-photorealistic FLUX.2 texture detail"]
        if part.strip()
    )
    final_score, final_missing, _ = score_prompt(refined)
    return TasteRefinedPrompt(
        original=prompt,
        refined=refined,
        additions=additions,
        score=final_score,
        missing_features=final_missing,
    )

