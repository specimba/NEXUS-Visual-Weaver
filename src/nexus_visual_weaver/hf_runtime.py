"""HF-native model execution for the Space runtime."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


FLUX_REPO_ID = "black-forest-labs/FLUX.2-klein-9B"


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
    root = Path(os.environ.get("NEXUS_OUTPUT_DIR") or ("/data/nexus_visual_weaver" if Path("/data").exists() else "outputs/runtime"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _short_error(exc: BaseException) -> str:
    text = str(exc).replace("\n", " ").strip()
    if len(text) > 420:
        text = text[:417] + "..."
    return f"{exc.__class__.__name__}: {text}"


def _hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")


def generate_flux_image(prompt: str, *, seed: int = 0, width: int = 1024, height: int = 1024, steps: int = 4) -> HFGenerationResult:
    if not hf_runtime_enabled():
        return HFGenerationResult(
            status="disabled",
            provider_state="dry-run",
            repo_id=FLUX_REPO_ID,
            message="Real HF generation disabled outside Space. Set NEXUS_ENABLE_REAL_HF=1 to force local execution.",
            width=width,
            height=height,
            steps=steps,
            hf_token_present=bool(_hf_token()),
        )

    started = time.perf_counter()
    try:
        import torch
        from diffusers import FluxPipeline
    except Exception as exc:  # pragma: no cover - depends on Space runtime packages.
        return HFGenerationResult(
            status="missing_runtime",
            provider_state="blocked",
            repo_id=FLUX_REPO_ID,
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
            repo_id=FLUX_REPO_ID,
            message="CUDA is not available to the Space callback; FLUX.2 9B requires GPU execution.",
            width=width,
            height=height,
            steps=steps,
            hf_token_present=bool(_hf_token()),
        )

    try:
        dtype = torch.bfloat16
        token = _hf_token()
        pipe = Flux2KleinPipeline.from_pretrained(FLUX_REPO_ID, torch_dtype=dtype, token=token)
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
        return HFGenerationResult(
            status="success",
            provider_state="generated",
            repo_id=FLUX_REPO_ID,
            output_path=str(output_path),
            message="FLUX.2 Klein generated a real image artifact on HF Space.",
            latency_seconds=round(time.perf_counter() - started, 2),
            width=width,
            height=height,
            steps=steps,
            hf_token_present=bool(token),
        )
    except Exception as exc:  # pragma: no cover - exercised on HF Space with gated/runtime conditions.
        return HFGenerationResult(
            status="error",
            provider_state="blocked",
            repo_id=FLUX_REPO_ID,
            message=f"FLUX.2 generation failed. Check model license acceptance, HF_TOKEN/Space access, and runtime deps. {_short_error(exc)}",
            latency_seconds=round(time.perf_counter() - started, 2),
            width=width,
            height=height,
            steps=steps,
            hf_token_present=bool(_hf_token()),
        )
