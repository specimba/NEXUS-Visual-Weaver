"""Optional sponsor/provider judging adapters for the command center."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


OPENBMB_REPO_ID = "openbmb/MiniCPM-V-4.6"
NEMOTRON_PARSE_REPO_ID = "nvidia/NVIDIA-Nemotron-Parse-v1.2"
NEMOTRON_NANO_REPO_ID = "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF"


@dataclass(frozen=True)
class ProviderJudgeResult:
    status: str
    provider_state: str
    provider: str
    repo_id: str
    model: str
    message: str
    evidence: dict[str, Any]
    latency_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _short_error(exc: BaseException) -> str:
    text = str(exc).replace("\n", " ").strip()
    if len(text) > 360:
        text = text[:357] + "..."
    return f"{exc.__class__.__name__}: {text}"


def _image_data_url(path: str | None) -> str | None:
    if not path:
        return None
    target = Path(path)
    if not target.exists() or not target.is_file():
        return None
    suffix = target.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/webp"
    data = base64.b64encode(target.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _post_json(url: str, token: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL comes from Space secret/config.
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _extract_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=True)


def _safe_json_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {}
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        stripped = stripped[start : end + 1]
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return {"raw_summary": text[:1200]}
    return parsed if isinstance(parsed, dict) else {"raw_summary": parsed}


def judge_with_minicpm(
    *,
    prompt: str,
    image_path: str | None,
    scan: dict[str, Any],
    wardrobe_summary: str,
    timeout: float = 45.0,
) -> ProviderJudgeResult:
    base_url = os.environ.get("MINICPM_BASE_URL", "").rstrip("/")
    token = os.environ.get("MINICPM_API_KEY") or os.environ.get("OPENBMB_API_KEY")
    model = os.environ.get("MINICPM_MODEL", "MiniCPM-V-4.6")
    if not base_url or not token:
        return ProviderJudgeResult(
            status="missing_secret",
            provider_state="missing secret",
            provider="OpenBMB",
            repo_id=OPENBMB_REPO_ID,
            model=model,
            message="MiniCPM-V judge is not configured. Add MINICPM_BASE_URL and MINICPM_API_KEY as Space secrets.",
            evidence={"configured": False, "scan_gate": scan.get("export_gate", "pending")},
        )

    image_url = _image_data_url(image_path)
    if not image_url:
        return ProviderJudgeResult(
            status="no_artifact",
            provider_state="blocked",
            provider="OpenBMB",
            repo_id=OPENBMB_REPO_ID,
            model=model,
            message="MiniCPM-V judge skipped because no generated image artifact is available.",
            evidence={"configured": True, "scan_gate": scan.get("export_gate", "pending")},
        )

    instruction = (
        "Return strict JSON only with keys: wardrobe_compliance, footwear_check, "
        "material_drift, gothic_couture_match, lore_continuity, export_safety_notes, "
        "overall_status. Be concise and judge the visible generated image against the brief."
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{instruction}\nBrief: {prompt}\nWardrobe: {wardrobe_summary}"},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        "temperature": 0.1,
    }
    started = time.perf_counter()
    try:
        response = _post_json(f"{base_url}/v1/chat/completions", token, payload, timeout)
        content = _extract_content(response)
        evidence = _safe_json_from_text(content)
        return ProviderJudgeResult(
            status="success",
            provider_state="configured",
            provider="OpenBMB",
            repo_id=OPENBMB_REPO_ID,
            model=model,
            message="MiniCPM-V returned visual judge evidence.",
            evidence=evidence or {"raw_summary": content[:1200]},
            latency_seconds=round(time.perf_counter() - started, 2),
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return ProviderJudgeResult(
            status="failed",
            provider_state="failed",
            provider="OpenBMB",
            repo_id=OPENBMB_REPO_ID,
            model=model,
            message=f"MiniCPM-V judge call failed. {_short_error(exc)}",
            evidence={"configured": True, "error": _short_error(exc)},
            latency_seconds=round(time.perf_counter() - started, 2),
        )


def judge_with_nemotron(
    *,
    prompt: str,
    run_packet: dict[str, Any],
    minicpm_result: dict[str, Any] | None = None,
    timeout: float = 45.0,
) -> ProviderJudgeResult:
    base_url = os.environ.get("NEMOTRON_BASE_URL", "").rstrip("/")
    token = os.environ.get("NEMOTRON_API_KEY") or os.environ.get("NVIDIA_API_KEY")
    model = os.environ.get("NEMOTRON_MODEL", "nvidia/NVIDIA-Nemotron-Parse-v1.2")
    repo_id = NEMOTRON_PARSE_REPO_ID if "Parse" in model or "parse" in model else NEMOTRON_NANO_REPO_ID
    if not base_url or not token:
        return ProviderJudgeResult(
            status="missing_secret",
            provider_state="missing secret",
            provider="NVIDIA",
            repo_id=repo_id,
            model=model,
            message="Nemotron evidence lane is not configured. Add NEMOTRON_BASE_URL and NEMOTRON_API_KEY/NVIDIA_API_KEY.",
            evidence={"configured": False, "repo_id": repo_id},
        )

    instruction = (
        "Return strict JSON only with keys: sponsor_model_used, structured_parse, "
        "risk_notes, parameter_budget_notes, final_claim_status. Parse this visual creation run."
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": f"{instruction}\nPrompt: {prompt}\nRun: {json.dumps(run_packet, ensure_ascii=True)[:6000]}\nMiniCPM: {json.dumps(minicpm_result or {}, ensure_ascii=True)[:2500]}",
            }
        ],
        "temperature": 0.1,
    }
    started = time.perf_counter()
    try:
        response = _post_json(f"{base_url}/v1/chat/completions", token, payload, timeout)
        content = _extract_content(response)
        evidence = _safe_json_from_text(content)
        return ProviderJudgeResult(
            status="success",
            provider_state="configured",
            provider="NVIDIA",
            repo_id=repo_id,
            model=model,
            message="Nemotron returned structured sponsor evidence.",
            evidence=evidence or {"raw_summary": content[:1200]},
            latency_seconds=round(time.perf_counter() - started, 2),
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return ProviderJudgeResult(
            status="failed",
            provider_state="failed",
            provider="NVIDIA",
            repo_id=repo_id,
            model=model,
            message=f"Nemotron evidence call failed. {_short_error(exc)}",
            evidence={"configured": True, "error": _short_error(exc)},
            latency_seconds=round(time.perf_counter() - started, 2),
        )
