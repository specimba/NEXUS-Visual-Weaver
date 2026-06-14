"""Governed export packet writer for hackathon evidence."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .catalog import active_stack, parameter_budget


def export_root() -> Path:
    requested = os.environ.get("NEXUS_EXPORT_DIR")
    candidates = [Path(requested)] if requested else []
    if Path("/data").exists():
        candidates.append(Path("/data/nexus_visual_weaver/exports"))
    candidates.append(Path("outputs/exports"))
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except PermissionError:
            continue
    fallback = Path("outputs/exports")
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
    stack = active_stack(adult_mode)
    generation = dict(operator_state.get("generation") or {})
    generation.pop("hf_token_present", None)
    packet = {
        "schema": "nexus_visual_weaver.export_packet.v1",
        "run_id": run_id,
        "created_at_epoch": int(time.time()),
        "adult_mode": bool(adult_mode),
        "prompt": getattr(getattr(run, "request", None), "prompt", ""),
        "refined_prompt": getattr(getattr(run, "refined_prompt", None), "refined", ""),
        "artifact": (operator_state.get("generation") or {}).get("output_path"),
        "generation": generation,
        "st3gg_scan": scan,
        "minicpm_judge": operator_state.get("minicpm_judge") or {},
        "nemotron_evidence": operator_state.get("nemotron_evidence") or {},
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
        "parameter_budget": parameter_budget(stack),
        "hackathon_claims": {
            "build_small_32b": parameter_budget(stack)["status"] == "pass",
            "gradio_space": True,
            "off_brand_custom_ui": True,
            "openbmb_lane": (operator_state.get("minicpm_judge") or {}).get("status") == "success",
            "nvidia_nemotron_lane": (operator_state.get("nemotron_evidence") or {}).get("status") == "success",
            "st3gg_export_gate": scan.get("export_gate"),
        },
    }
    target = export_root() / f"{run_id}.json"
    target.write_text(json.dumps(packet, indent=2, ensure_ascii=True), encoding="utf-8")
    return {"path": str(target), "packet": packet}
