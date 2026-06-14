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
        """
        Convert this result instance to a plain dictionary.
        
        Returns:
        	dict[str, Any]: A dictionary representation of this result.
        """
        return asdict(self)


def _short_error(exc: BaseException) -> str:
    """
    Convert an exception to a single-line, truncated error message.
    
    Returns:
    	str: Error message in the format "ClassName: message", truncated to 360 characters.
    """
    text = str(exc).replace("\n", " ").strip()
    if len(text) > 360:
        text = text[:357] + "..."
    return f"{exc.__class__.__name__}: {text}"


def _image_data_url(path: str | None) -> str | None:
    """
    Convert an image file to a base64-encoded data URL.
    
    Parameters:
    	path (str | None): The file path to the image.
    
    Returns:
    	str | None: A data URL string with base64-encoded image data and appropriate MIME type (image/png, image/jpeg, or image/webp), or None if the file is invalid or does not exist.
    """
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
    """
    Send a JSON POST request with Bearer token authorization.
    
    Returns:
        dict[str, Any]: The parsed JSON response.
    """
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
        return json.loads(response.read().decode("utf-8"))


def _extract_content(response: dict[str, Any]) -> str:
    """
    Extract the message content from a chat-completions API response.
    
    If the content is a string, returns it as-is. If the content is non-string data,
    JSON-encodes it. Returns an empty string if no choices are available.
    
    Parameters:
        response (dict): A chat-completions API response containing a "choices" list
                         with message objects.
    
    Returns:
        str: The extracted message content, or its JSON-encoded representation if the
             content is not a string. Returns an empty string if no choices are available.
    """
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=True)


def _safe_json_from_text(text: str) -> dict[str, Any]:
    """
    Extract and parse a JSON object from text, with fallback handling for unparseable content.
    
    Attempts to isolate a JSON object from the input text by finding the first opening brace and last closing brace. If JSON parsing fails or the parsed result is not a dictionary, returns a fallback structure containing the input text (truncated to 1200 characters) under the "raw_summary" key. An empty input returns an empty dictionary.
    
    Parameters:
        text (str): The text from which to extract and parse JSON.
    
    Returns:
        dict[str, Any]: The parsed JSON object as a dictionary, or a fallback dictionary with "raw_summary" key containing the original text if parsing fails.
    """
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
    """
    Evaluate a generated image against a fashion brief using the OpenBMB MiniCPM-V model.
    
    API credentials are read from environment variables: MINICPM_BASE_URL, MINICPM_API_KEY (or OPENBMB_API_KEY), and optionally MINICPM_MODEL.
    
    Parameters:
        scan: Dictionary containing scan metadata; the 'export_gate' key is extracted for result evidence.
    
    Returns:
        ProviderJudgeResult with status 'missing_secret' if credentials are unconfigured, 'no_artifact' if the image is unavailable, 'success' on successful judgment, or 'failed' on API errors. Includes parsed JSON evidence from the model's response (or a fallback summary if parsing fails) and measured call latency.
    """
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
    """
    Requests structured evidence from NVIDIA Nemotron about a visual creation run.
    
    Reads configuration from NEMOTRON_BASE_URL and NEMOTRON_API_KEY (or NVIDIA_API_KEY) environment variables. If configuration is incomplete, returns a "missing_secret" result. Posts a chat completions request with the prompt, run packet (JSON-truncated), and optional MiniCPM result; parses the response into structured evidence and records call latency. Returns a "failed" result on network, timeout, or parsing errors.
    
    Parameters:
    	prompt (str): Description or context of the visual creation to be evaluated.
    	run_packet (dict[str, Any]): Metadata and details about the current run.
    	minicpm_result (dict[str, Any] | None, optional): Prior MiniCPM judgment result for context. Defaults to None.
    	timeout (float, optional): HTTP request timeout in seconds. Defaults to 45.0.
    
    Returns:
    	ProviderJudgeResult: Result containing status ("missing_secret", "success", or "failed"), evidence (parsed JSON or raw summary), latency_seconds, and configuration details.
    """
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
