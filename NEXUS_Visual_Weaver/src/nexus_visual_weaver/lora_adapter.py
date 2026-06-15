"""Guarded LoRA adapter loading for HF runtime execution."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .schema import AdapterRecipe


def _status(status: str, recipe: AdapterRecipe | None = None, **extra: Any) -> dict[str, Any]:
    """
    Build a status dictionary with adapter metadata and additional fields.
    
    Returns:
        dict[str, Any]: A dictionary containing the status and optional recipe fields (repo_id, adapter_for, weight), merged with any extra keyword arguments.
    """
    payload: dict[str, Any] = {
        "status": status,
        "repo_id": recipe.repo_id if recipe else None,
        "adapter_for": recipe.adapter_for if recipe else None,
        "weight": recipe.weight if recipe else None,
    }
    payload.update(extra)
    return payload


def _short_error(exc: BaseException) -> str:
    """
    Format an exception message with truncation for compact display.
    
    Returns the exception class name and message as "{ClassName}: {message}",
    truncated to 240 characters.
    
    Parameters:
        exc (BaseException): The exception to format.
    
    Returns:
        str: The formatted exception message.
    """
    text = str(exc).replace("\n", " ").strip()
    if len(text) > 240:
        text = text[:237] + "..."
    return f"{exc.__class__.__name__}: {text}"


def adapter_to_dict(recipe: AdapterRecipe) -> dict[str, Any]:
    """
    Convert an AdapterRecipe instance to a dictionary.
    
    Returns:
    	dict[str, Any]: Dictionary representation of the recipe's fields.
    """
    return asdict(recipe)


def is_compatible(pipe: Any, recipe: AdapterRecipe, target_repo_id: str, *, adult_mode: bool = False) -> bool:
    """
    Determines whether a LoRA adapter is compatible with a pipeline and target model.
    
    Returns:
        `true` if the recipe is runtime-enabled, not blocked by adult-mode restrictions,
        does not require image input, the pipeline has LoRA support, and the target model
        is compatible; `false` otherwise.
    """
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
    """
    Load and apply a LoRA adapter to a pipeline when permitted, returning structured operation status.
    
    Parameters:
        recipe: Adapter configuration. If None, the function returns a disabled status without attempting to load.
        target_repo_id: The model repository ID to verify adapter compatibility against.
    
    Returns:
        A dictionary with keys: status (disabled, skipped_incompatible, unsupported_pipeline, loaded, or failed), repo_id, adapter_for, weight, adapter_name, and message.
    """
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
        unload_all(pipe)
        return _status("failed", recipe, message=_short_error(exc), adapter_name=adapter_name)


def unload_all(pipe: Any) -> None:
    """
    Unload all LoRA adapter weights from the pipeline if supported.
    """
    try:
        if hasattr(pipe, "unload_lora_weights"):
            pipe.unload_lora_weights()
    except Exception:
        return
