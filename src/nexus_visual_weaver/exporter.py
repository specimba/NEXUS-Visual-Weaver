"""Governed export packet writer for hackathon evidence."""

from __future__ import annotations

import json
import os
import re
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


SENSITIVE_KEY_RE = re.compile(r"(token|secret|api[_-]?key|authorization|payload_excerpt|raw|base64|bytes)", re.IGNORECASE)
SECRET_VALUE_RE = re.compile(r"(hf_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9._-]+|sk-[A-Za-z0-9_-]{20,})")
CREDENTIAL_NAME_RE = re.compile(r"\b[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET)[A-Z0-9_]*\b")
WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s\"']+")


def _sanitize_text(value: str) -> str:
    text = SECRET_VALUE_RE.sub("[redacted_secret]", value)
    text = CREDENTIAL_NAME_RE.sub("[redacted_credential_name]", text)
    text = WINDOWS_PATH_RE.sub(lambda match: f"[local_path]/{Path(match.group(0)).name}", text)
    repo_text = str(REPO_ROOT)
    if repo_text in text:
        text = text.replace(repo_text, "[repo]")
    if "/data/" in text:
        text = text.replace("/data/", "[data]/")
    if len(text) > 1000:
        text = text[:997] + "..."
    return text


def _safe_dict(value: Any, *, allow_size_bytes: bool = False) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if SENSITIVE_KEY_RE.search(key_str) and not (allow_size_bytes and key_str == "size_bytes"):
                continue
            clean[key_str] = _safe_dict(item, allow_size_bytes=allow_size_bytes)
        return clean
    if isinstance(value, list):
        return [_safe_dict(item, allow_size_bytes=allow_size_bytes) for item in value[:40]]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": scan.get("status"),
        "scanner": scan.get("scanner"),
        "export_gate": scan.get("export_gate"),
        "extension": scan.get("extension"),
        "magic": scan.get("magic"),
        "findings": _safe_dict(scan.get("findings") or []),
        "purification_actions": _safe_dict(scan.get("purification_actions") or []),
    }


def _safe_provider(provider: dict[str, Any] | None) -> dict[str, Any]:
    provider = provider or {}
    evidence = provider.get("evidence") if isinstance(provider.get("evidence"), dict) else {}
    return {
        "status": provider.get("status"),
        "provider_state": provider.get("provider_state"),
        "provider": provider.get("provider"),
        "repo_id": provider.get("repo_id"),
        "model": provider.get("model"),
        "message": _safe_dict(provider.get("message", "")),
        "evidence": _safe_dict(evidence),
        "latency_seconds": provider.get("latency_seconds"),
    }


def _safe_reference_metadata(records: Any) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for record in records[:20]:
        if not isinstance(record, dict):
            continue
        cleaned.append(
            {
                "source": record.get("source"),
                "status": record.get("status"),
                "basename": _artifact_name(record.get("basename")) if record.get("basename") else None,
                "sha256": record.get("sha256"),
                "size_bytes": record.get("size_bytes"),
                "st3gg_status": record.get("st3gg_status"),
                "export_gate": record.get("export_gate"),
                "magic": record.get("magic"),
                "extension": record.get("extension"),
                "domain": record.get("domain"),
                "url_hash": record.get("url_hash"),
                "message": _safe_dict(record.get("message", "")),
            }
        )
    return cleaned


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
    generation = _safe_dict(generation)
    creator_controls = _safe_dict(operator_state.get("creator_controls") or getattr(getattr(run, "request", None), "creator_controls", {}) or {})
    reference_metadata = _safe_reference_metadata(operator_state.get("reference_metadata") or getattr(getattr(run, "request", None), "reference_metadata", []) or [])
    st3gg_scan = _safe_scan(scan)
    minicpm_judge = _safe_provider(operator_state.get("minicpm_judge") or {})
    nemotron_evidence = _safe_provider(operator_state.get("nemotron_evidence") or {})
    provider_states = {
        "generation": generation.get("provider_state"),
        "minicpm": minicpm_judge.get("status"),
        "nemotron": nemotron_evidence.get("status"),
        "operator": operator_state.get("provider_state"),
    }
    packet = {
        "schema": "nexus_visual_weaver.export_packet.v1",
        "run_id": run_id,
        "created_at_epoch": int(time.time()),
        "adult_mode": run_adult_mode,
        "prompt": getattr(getattr(run, "request", None), "prompt", ""),
        "refined_prompt": getattr(getattr(run, "refined_prompt", None), "refined", ""),
        "artifact": artifact,
        "image_basename": artifact,
        "creator_controls": creator_controls,
        "reference_metadata": reference_metadata,
        "lora_status": {
            "status": generation.get("lora_status"),
            "repo_id": generation.get("lora_repo_id"),
            "message": generation.get("lora_message"),
        },
        "generation": generation,
        "st3gg_verdict": {
            "status": st3gg_scan.get("status"),
            "export_gate": st3gg_scan.get("export_gate"),
        },
        "st3gg_scan": st3gg_scan,
        "minicpm_judge": minicpm_judge,
        "nemotron_evidence": nemotron_evidence,
        "checkpoint": {
            "status": operator_state.get("checkpoint"),
            "message": operator_state.get("message"),
            "recommendation": getattr(getattr(run, "checkpoint", None), "recommendation", None),
            "trust_score": getattr(getattr(run, "checkpoint", None), "trust_score", None),
            "required_actions": getattr(getattr(run, "checkpoint", None), "required_actions", []),
        },
        "provider_state": operator_state.get("provider_state"),
        "provider_states": provider_states,
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
            "openbmb_lane": minicpm_judge.get("status") == "success",
            "nvidia_nemotron_lane": nemotron_evidence.get("status") == "success",
            "st3gg_export_gate": st3gg_scan.get("export_gate"),
        },
    }
    target = export_root() / f"{run_id}.json"
    target.write_text(json.dumps(packet, indent=2, ensure_ascii=True), encoding="utf-8")
    return {"path": str(target), "packet": packet}
