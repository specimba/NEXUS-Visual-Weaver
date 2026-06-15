"""HF-native model execution for the Space runtime."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .catalog import ADAPTER_CATALOG
from .lora_adapter import load_and_apply, unload_all
from .schema import AdapterRecipe


FLUX_REPO_ID = "black-forest-labs/FLUX.2-klein-9B"
TINY_TITAN_FLUX_REPO_ID = "black-forest-labs/FLUX.2-klein-4B"
PRIVATE_RESEARCH_FLUX_REPO_ID = FLUX_REPO_ID
_PIPELINE_CACHE: dict[str, Any] = {}
_PIPELINE_CACHE_LOCK = threading.Lock()


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
    lora_status: str = "disabled"
    lora_repo_id: str | None = None
    lora_message: str = "No LoRA adapter selected for this run."
    fallback_used: bool = False
    primary_error: str | None = None

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


def _repo_candidates(repo_id: str) -> list[str]:
    candidates = [repo_id]
    if repo_id != TINY_TITAN_FLUX_REPO_ID and os.environ.get("NEXUS_DISABLE_TINY_TITAN_FALLBACK") != "1":
        candidates.append(TINY_TITAN_FLUX_REPO_ID)
    return candidates


def _get_flux_pipe(repo_id: str, torch_module: Any, pipeline_cls: Any, token: str | None) -> Any:
    with _PIPELINE_CACHE_LOCK:
        cached = _PIPELINE_CACHE.get(repo_id)
        if cached is not None:
            return cached
        pipe = pipeline_cls.from_pretrained(repo_id, torch_dtype=torch_module.bfloat16, token=token)
        pipe.enable_model_cpu_offload()
        _PIPELINE_CACHE[repo_id] = pipe
        return pipe


def _adapter_recipe(repo_id: str | None) -> AdapterRecipe | None:
    if not repo_id:
        return None
    return next((recipe for recipe in ADAPTER_CATALOG if recipe.repo_id == repo_id), None)


def default_lora_repo_id(target_repo_id: str) -> str | None:
    for recipe in ADAPTER_CATALOG:
        compatible_ids = {recipe.adapter_for, *recipe.compatible_repo_ids}
        if recipe.runtime_enabled and not recipe.adult_only and not recipe.requires_image and target_repo_id in compatible_ids:
            return recipe.repo_id
    return None


def generate_flux_image(
    prompt: str,
    *,
    seed: int = 0,
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    lora_repo_id: str | None = None,
    adult_mode: bool = False,
) -> HFGenerationResult:
    repo_id = active_flux_repo_id()
    selected_lora = lora_repo_id if lora_repo_id is not None else default_lora_repo_id(repo_id)
    recipe = _adapter_recipe(selected_lora)
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
            lora_status="disabled",
            lora_repo_id=recipe.repo_id if recipe else None,
            lora_message="LoRA loading requires the HF Space GPU runtime.",
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
            lora_status="disabled",
            lora_repo_id=recipe.repo_id if recipe else None,
            lora_message="FLUX runtime import failed before LoRA loading.",
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
            lora_status="disabled",
            lora_repo_id=recipe.repo_id if recipe else None,
            lora_message="CUDA unavailable before LoRA loading.",
        )

    token = _hf_token()
    errors: list[str] = []
    for candidate in _repo_candidates(repo_id):
        try:
            pipe = _get_flux_pipe(candidate, torch, Flux2KleinPipeline, token)
            if hasattr(pipe, "set_progress_bar_config"):
                pipe.set_progress_bar_config(disable=True)
            lora_result = load_and_apply(pipe, recipe, candidate, adult_mode=adult_mode)

            try:
                generator = torch.Generator(device="cuda").manual_seed(seed)
                image = pipe(
                    prompt=prompt,
                    height=height,
                    width=width,
                    guidance_scale=1.0,
                    num_inference_steps=steps,
                    generator=generator,
                ).images[0]
            finally:
                unload_all(pipe)
            output_path = _output_dir() / f"nexus_flux_{int(time.time())}_{seed}.png"
            image.save(output_path)
            return HFGenerationResult(
                status="success",
                provider_state="generated",
                repo_id=candidate,
                output_path=str(output_path),
                message=f"{candidate} generated a real Raven Quality artifact on HF Space.",
                latency_seconds=round(time.perf_counter() - started, 2),
                width=width,
                height=height,
                steps=steps,
                hf_token_present=bool(token),
                lora_status=str(lora_result.get("status", "disabled")),
                lora_repo_id=lora_result.get("repo_id"),
                lora_message=str(lora_result.get("message", "")),
                fallback_used=candidate != repo_id,
                primary_error=errors[0] if candidate != repo_id and errors else None,
            )
        except Exception as exc:  # pragma: no cover - exercised on HF Space with gated/runtime conditions.
            errors.append(f"{candidate}: {_short_error(exc)}")
            with _PIPELINE_CACHE_LOCK:
                _PIPELINE_CACHE.pop(candidate, None)
            continue
    return HFGenerationResult(
        status="error",
        provider_state="blocked",
        repo_id=repo_id,
        message=f"FLUX.2 generation failed. Check model license acceptance, HF_TOKEN/Space access, and runtime deps. Attempts: {' | '.join(errors)}",
        latency_seconds=round(time.perf_counter() - started, 2),
        width=width,
        height=height,
        steps=steps,
        hf_token_present=bool(_hf_token()),
        lora_status="disabled" if recipe is None else "failed",
        lora_repo_id=recipe.repo_id if recipe else None,
        lora_message="Generation failed before a usable LoRA evidence state could be produced.",
    )
