"""Governed export packet writer for hackathon evidence."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .catalog import active_stack, parameter_budget

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_LOCAL_EXPORT_ROOTS = (
    REPO_ROOT / "outputs",
    REPO_ROOT / ".pi",
    REPO_ROOT / ".codex",
)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_export_candidate(candidate: Path) -> Path | None:
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    resolved = candidate.resolve(strict=False)
    src_root = (REPO_ROOT / "src").resolve(strict=False)
    if resolved == src_root or _is_within(resolved, src_root):
        return None

    allowed_roots = [root.resolve(strict=False) for root in ALLOWED_LOCAL_EXPORT_ROOTS]
    if Path("/data").exists():
        allowed_roots.append(Path("/data/nexus_visual_weaver").resolve(strict=False))
    if any(resolved == root or _is_within(resolved, root) for root in allowed_roots):
        return resolved
    return None


def _artifact_name(output_path: Any) -> str | None:
    if not output_path:
        return None
    return Path(str(output_path)).name


def export_root() -> Path:
    requested = os.environ.get("NEXUS_EXPORT_DIR")
    candidates = [Path(requested)] if requested else []
    if Path("/data").exists():
        candidates.append(Path("/data/nexus_visual_weaver/exports"))
    candidates.append(Path("outputs/exports"))
    for candidate in candidates:
        safe_candidate = _safe_export_candidate(candidate)
        if safe_candidate is None:
            continue
        try:
            safe_candidate.mkdir(parents=True, exist_ok=True)
            return safe_candidate
        except OSError:
            continue
    fallback = (REPO_ROOT / "outputs/exports").resolve(strict=False)
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def write_export_packet(
    *,
    run: Any,
    scan: dict[str, Any],
    operator_state: dict[str, Any],
    adult_mode: bool,
) -> dict[str, Any]:
    run_id = getattr(getattr(run, "checkpoint", None), "checkpoint_id", f"nw-{int(time.time())}")
    run_adult_mode = bool(getattr(getattr(run, "request", None), "adult_mode", adult_mode))
    stack = list(getattr(run, "model_stack", None) or active_stack(run_adult_mode))
    budget = parameter_budget(stack)
    generation = dict(operator_state.get("generation") or {})
    generation.pop("hf_token_present", None)
    artifact = _artifact_name(generation.get("output_path"))
    if "output_path" in generation:
        generation["output_path"] = artifact
    modal_job = operator_state.get("modal_video_repair") or {
        "status": "deferred",
        "repo_id": "netflix/void-model",
        "provider": "modal",
    }
    audio_lore = operator_state.get("audio_lore_tts") or {
        "status": "optional",
        "repo_id": "hexgrad/Kokoro-82M",
    }
    offellia = operator_state.get("offellia_judge") or {
        "status": "deferred_local",
        "repo_id": "Brunobkr/OFFELLIA_Q4_0_gemma-4-12B-it.gguf",
    }
    tiny_titan = operator_state.get("tiny_titan_sidecar") or {
        "status": "available",
        "repo_id": "black-forest-labs/FLUX.2-klein-4B",
    }
    locate_grounding = operator_state.get("locateanything_grounding") or {}
    packet = {
        "schema": "nexus_visual_weaver.export_packet.v1",
        "run_id": run_id,
        "created_at_epoch": int(time.time()),
        "active_preset": operator_state.get("active_preset", "Raven Quality Stack"),
        "adult_mode": run_adult_mode,
        "prompt": getattr(getattr(run, "request", None), "prompt", ""),
        "refined_prompt": getattr(getattr(run, "refined_prompt", None), "refined", ""),
        "artifact": artifact,
        "generation": generation,
        "st3gg_scan": scan,
        "locateanything_grounding": locate_grounding,
        "offellia_judge": offellia,
        "minicpm_judge": operator_state.get("minicpm_judge") or {},
        "nemotron_evidence": operator_state.get("nemotron_evidence") or {},
        "modal_video_repair": modal_job,
        "audio_lore_tts": audio_lore,
        "tiny_titan_sidecar": tiny_titan,
        "checkpoint": {
            "status": operator_state.get("checkpoint"),
            "message": operator_state.get("message"),
        },
        "provider_state": operator_state.get("provider_state"),
        "model_stack": [
            {
                "repo_id": model.repo_id,
                "role": model.role,
                "params_b": model.params_b,
                "license": model.license,
                "gated": model.gated,
            }
            for model in stack
        ],
        "parameter_budget": budget,
        "hackathon_claims": {
            "build_small_32b": budget["status"] == "pass",
            "gradio_space": True,
            "off_brand_custom_ui": True,
            "openbmb_lane": (operator_state.get("minicpm_judge") or {}).get("status") == "success",
            "nvidia_nemotron_lane": (operator_state.get("nemotron_evidence") or {}).get("status") == "success",
            "offellia_quality_lane": offellia.get("status") in {"success", "completed"},
            "modal_void_lane": modal_job.get("status") in {"success", "completed", "documented"},
            "tiny_titan_sidecar": tiny_titan.get("status") in {"success", "available", "sidecar"},
            "raven_quality_stack": True,
            "locateanything_grounding": bool(locate_grounding.get("targets") or locate_grounding.get("repo_id")),
            "st3gg_export_gate": scan.get("export_gate"),
        },
    }
    target = export_root() / f"{run_id}.json"
    target.write_text(json.dumps(packet, indent=2, ensure_ascii=True), encoding="utf-8")
    return {"path": str(target), "packet": packet}
