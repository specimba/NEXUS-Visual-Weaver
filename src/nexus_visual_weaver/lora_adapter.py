"""Guarded LoRA adapter loading for HF runtime execution."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .schema import AdapterRecipe


def _status(status: str, recipe: AdapterRecipe | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "repo_id": recipe.repo_id if recipe else None,
        "adapter_for": recipe.adapter_for if recipe else None,
        "weight": recipe.weight if recipe else None,
    }
    payload.update(extra)
    return payload


def _short_error(exc: BaseException) -> str:
    text = str(exc).replace("\n", " ").strip()
    if len(text) > 240:
        text = text[:237] + "..."
    return f"{exc.__class__.__name__}: {text}"


def adapter_to_dict(recipe: AdapterRecipe) -> dict[str, Any]:
    return asdict(recipe)


def is_compatible(pipe: Any, recipe: AdapterRecipe, target_repo_id: str, *, adult_mode: bool = False) -> bool:
    if not recipe.runtime_enabled:
        return False
    if recipe.adult_only and not adult_mode:
        return False
    if recipe.requires_image:
        return False
    if not hasattr(pipe, "load_lora_weights"):
        return False

    compatible_ids = {recipe.adapter_for, *recipe.compatible_repo_ids}
    if compatible_ids and target_repo_id not in compatible_ids:
        return False
    return True


def load_and_apply(
    pipe: Any,
    recipe: AdapterRecipe | None,
    target_repo_id: str,
    *,
    adult_mode: bool = False,
    adapter_name: str = "nexus_style",
) -> dict[str, Any]:
    if recipe is None:
        return _status("disabled", message="No LoRA adapter selected for this run.")
    if recipe.adult_only and not adult_mode:
        return _status("skipped_incompatible", recipe, message="Adult-only adapter is not available while Adult Mode is off.")
    if recipe.requires_image:
        return _status("skipped_incompatible", recipe, message="Adapter requires image-conditioning support that is deferred in P0.")
    if not hasattr(pipe, "load_lora_weights"):
        return _status("unsupported_pipeline", recipe, message="Pipeline does not expose load_lora_weights.")
    if not is_compatible(pipe, recipe, target_repo_id, adult_mode=adult_mode):
        return _status("skipped_incompatible", recipe, message=f"Adapter is not declared compatible with {target_repo_id}.")

    try:
        kwargs: dict[str, Any] = {"adapter_name": adapter_name}
        if recipe.weight_name:
            kwargs["weight_name"] = recipe.weight_name
        pipe.load_lora_weights(recipe.repo_id, **kwargs)
        if hasattr(pipe, "set_adapters"):
            pipe.set_adapters([adapter_name], adapter_weights=[recipe.weight])
        return _status("loaded", recipe, message="Adapter loaded and applied for this generation.", adapter_name=adapter_name)
    except Exception as exc:
        return _status("failed", recipe, message=_short_error(exc), adapter_name=adapter_name)


def unload_all(pipe: Any) -> None:
    try:
        if hasattr(pipe, "unload_lora_weights"):
            pipe.unload_lora_weights()
    except Exception:
        return
