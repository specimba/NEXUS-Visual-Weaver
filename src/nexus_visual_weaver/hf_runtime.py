"""HF-native model execution for the Space runtime."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


FLUX_REPO_ID = "black-forest-labs/FLUX.2-klein-9B"
TINY_TITAN_FLUX_REPO_ID = "black-forest-labs/FLUX.2-klein-4B"
PRIVATE_RESEARCH_FLUX_REPO_ID = FLUX_REPO_ID


@dataclass(frozen=True)
class HFGenerationResult:
    status: str
    provider_state: str
    repo_id: str
    output_path: str | None = None
    message: str = ""
    latency_seconds: float | None = None
    width: int = 1024
    height: int = 1024
    steps: int = 4
    hf_token_present: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def hf_runtime_enabled() -> bool:
    if os.environ.get("NEXUS_DISABLE_REAL_HF") == "1":
        return False
    if os.environ.get("NEXUS_ENABLE_REAL_HF") == "1":
        return True
    return bool(os.environ.get("SPACE_ID") or os.environ.get("HF_SPACE_ID"))


def _output_dir() -> Path:
    path_str = os.environ.get("NEXUS_OUTPUT_DIR")
    if not path_str:
        if Path("/data").exists():
            try:
                root = Path("/data/nexus_visual_weaver")
                root.mkdir(parents=True, exist_ok=True)
                return root
            except PermissionError:
                pass
        path_str = "outputs/runtime"
    root = Path(path_str)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _short_error(exc: BaseException) -> str:
    text = str(exc).replace("\n", " ").strip()
    if len(text) > 420:
        text = text[:417] + "..."
    return f"{exc.__class__.__name__}: {text}"


def _hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")


def active_flux_repo_id() -> str:
    configured = os.environ.get("NEXUS_FLUX_REPO_ID")
    if configured:
        return configured
    if os.environ.get("NEXUS_TINY_TITAN_MODE") == "1":
        return TINY_TITAN_FLUX_REPO_ID
    return FLUX_REPO_ID


def generate_flux_image(prompt: str, *, seed: int = 0, width: int = 1024, height: int = 1024, steps: int = 4) -> HFGenerationResult:
    repo_id = active_flux_repo_id()
    if not hf_runtime_enabled():
        return HFGenerationResult(
            status="disabled",
            provider_state="dry-run",
            repo_id=repo_id,
            message="Real HF generation disabled outside Space. Raven Quality Stack uses FLUX.2 Klein 9B by default; set NEXUS_TINY_TITAN_MODE=1 for the 4B sidecar.",
            width=width,
            height=height,
            steps=steps,
            hf_token_present=bool(_hf_token()),
        )

    started = time.perf_counter()
    try:
        import torch
        from diffusers import Flux2KleinPipeline
    except Exception as exc:  # pragma: no cover - depends on Space runtime packages.
        return HFGenerationResult(
            status="missing_runtime",
            provider_state="blocked",
            repo_id=repo_id,
            message=f"FLUX runtime import failed. Install diffusers main + torch. {_short_error(exc)}",
            width=width,
            height=height,
            steps=steps,
            hf_token_present=bool(_hf_token()),
        )

    if not torch.cuda.is_available():
        return HFGenerationResult(
            status="no_cuda",
            provider_state="blocked",
            repo_id=repo_id,
            message="CUDA is not available to the Space callback; FLUX.2 generation requires GPU execution.",
            width=width,
            height=height,
            steps=steps,
            hf_token_present=bool(_hf_token()),
        )

    token = _hf_token()
    repo_candidates = [repo_id]
    if repo_id != TINY_TITAN_FLUX_REPO_ID and os.environ.get("NEXUS_DISABLE_TINY_TITAN_FALLBACK") != "1":
        repo_candidates.append(TINY_TITAN_FLUX_REPO_ID)
    errors: list[str] = []
    for candidate in repo_candidates:
        try:
            dtype = torch.bfloat16
            pipe = Flux2KleinPipeline.from_pretrained(candidate, torch_dtype=dtype, token=token)
            pipe.enable_model_cpu_offload()
            generator = torch.Generator(device="cuda").manual_seed(seed)
            image = pipe(
                prompt=prompt,
                height=height,
                width=width,
                guidance_scale=1.0,
                num_inference_steps=steps,
                generator=generator,
            ).images[0]
            output_path = _output_dir() / f"nexus_flux_{int(time.time())}_{seed}.png"
            image.save(output_path)
            fallback = candidate != repo_id
            message = (
                f"{candidate} generated a Tiny Titan sidecar artifact after the 9B lane was unavailable."
                if fallback
                else f"{candidate} generated a real Raven Quality artifact on HF Space."
            )
            return HFGenerationResult(
                status="success",
                provider_state="generated",
                repo_id=candidate,
                output_path=str(output_path),
                message=message,
                latency_seconds=round(time.perf_counter() - started, 2),
                width=width,
                height=height,
                steps=steps,
                hf_token_present=bool(token),
            )
        except Exception as exc:  # pragma: no cover - exercised on HF Space with gated/runtime conditions.
            errors.append(f"{candidate}: {_short_error(exc)}")
    return HFGenerationResult(
        status="error",
        provider_state="blocked",
        repo_id=repo_id,
        message=f"FLUX.2 generation failed. Check model license acceptance, HF_TOKEN/Space access, and runtime deps. Attempts: {' | '.join(errors)}",
        latency_seconds=round(time.perf_counter() - started, 2),
        width=width,
        height=height,
        steps=steps,
        hf_token_present=bool(token),
    )
