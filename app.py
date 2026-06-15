"""NEXUS Visual Weaver - Build Small Hackathon command center."""

from __future__ import annotations

import os
import sys
import hashlib
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import gradio as gr

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import spaces  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover - local development does not require Spaces.
    spaces = None

from nexus_visual_weaver.catalog import catalog_summary
from nexus_visual_weaver.exporter import write_export_packet
from nexus_visual_weaver.hf_runtime import generate_flux_image
from nexus_visual_weaver.model_relay import WeaverModelRelay
from nexus_visual_weaver.planner import build_command_center_run
from nexus_visual_weaver.provider_runtime import judge_with_minicpm, judge_with_nemotron
from nexus_visual_weaver.render import render_catalog_table, render_command_header, render_dashboard_regions
from nexus_visual_weaver.security import scan_file
from nexus_visual_weaver.styles import APP_CSS

APP_THEME = gr.themes.Base(
    primary_hue="rose",
    secondary_hue="cyan",
    neutral_hue="slate",
    radius_size="sm",
    font=["Inter", "ui-sans-serif", "system-ui"],
)


DEFAULT_PROMPT = (
    "A Slavic archivist in a rain-slick neon city, wearing a structured black patent "
    "leather long coat with faux fur collar, Chantilly lace neckline, glowing crimson "
    "hardware, platform boots, NEXUS sigils and floating code streams behind her."
)

MODEL_RELAY = WeaverModelRelay()

STYLE_MODIFIERS = {
    "Balanced": "balanced editorial lighting, precise garment detail, clean composition",
    "High Fashion": "haute couture editorial styling, premium material finish, runway-grade silhouette",
    "Cinematic": "cinematic rain-lit atmosphere, dramatic lensing, high contrast neon reflections",
}

ASPECT_DIMENSIONS = {
    "Square": (1024, 1024),
    "Portrait": (832, 1216),
}


def _default_operator_state() -> dict[str, Any]:
    return {
        "provider_state": "idle",
        "checkpoint": "pending",
        "export": "pending",
        "message": "No operator action yet.",
    }


def _zero_gpu_entrypoint(fn: Any) -> Any:
    """
    Optionally wrap a function with ZeroGPU acceleration.
    
    If the spaces module is available and provides GPU support, wraps the function with `spaces.GPU(duration=300)`. Otherwise, returns the function unchanged.
    
    Parameters:
        fn: The callback function.
    
    Returns:
        The function, optionally wrapped with ZeroGPU acceleration.
    """
    gpu_decorator = getattr(spaces, "GPU", None) if spaces is not None else None
    if gpu_decorator is None:
        return fn
    return gpu_decorator(duration=300)(fn)


def _relay_snapshot(adult_mode: bool = False) -> dict[str, Any]:
    """
    Retrieves the relay dashboard snapshot based on visibility mode.
    
    Returns:
        dict[str, Any]: Dashboard snapshot containing relay status and model information.
    """
    return MODEL_RELAY.dashboard_snapshot(public_demo=not adult_mode)


def _file_path(uploaded: Any) -> str | None:
    """
    Extract a file path from various upload input formats.
    
    Returns:
        str | None: The file path string, or None if the input is None or lacks a valid path.
    """
    if uploaded is None:
        return None
    if isinstance(uploaded, str):
        return uploaded
    path = getattr(uploaded, "name", None)
    return str(path) if path else None


def _safe_file_hash(path: str | None) -> tuple[str | None, int | None]:
    """
    Compute the SHA-256 hash and size of a file.
    
    Returns:
        tuple[str | None, int | None]: The file's SHA-256 hash as a hex string and size in bytes. Returns (None, None) if the path is falsy or the file cannot be read.
    """
    if not path:
        return None, None
    try:
        target = Path(path)
        sha256 = hashlib.sha256()
        size = 0
        with target.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                sha256.update(chunk)
                size += len(chunk)
    except OSError:
        return None, None
    return sha256.hexdigest(), size


def _safe_reference_url_metadata(reference_url: str | None) -> dict[str, Any] | None:
    """
    Validates a reference URL and extracts its metadata.
    
    Returns:
        A dict with status "metadata_only" containing domain (lowercased) and URL hash if valid;
        a dict with status "invalid_url" if the URL scheme is not HTTP(S) or domain is missing;
        None if reference_url is falsy.
    """
    if not reference_url:
        return None
    parsed = urlparse(reference_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"source": "url", "status": "invalid_url", "message": "Reference URL must be http(s)."}
    url_hash = hashlib.sha256(reference_url.strip().encode("utf-8")).hexdigest()
    return {
        "source": "url",
        "status": "metadata_only",
        "domain": parsed.netloc.lower(),
        "url_hash": url_hash,
        "message": "URL stored as metadata only; Space runtime does not crawl or copy shop images.",
    }


def _reference_metadata(uploaded: Any, reference_url: str | None, scan: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Builds a list of metadata records from an uploaded file and/or reference URL.
    
    For an uploaded file, includes basename, SHA-256 hash, size, and scan results (status,
    export gate, magic, extension). For a reference URL, includes domain, URL hash, and status.
    
    Parameters:
    	uploaded: An uploaded file object, path string, or None.
    	reference_url: Optional reference URL string.
    	scan: Dictionary of ST3GG scan results for the uploaded file.
    
    Returns:
    	List of metadata dictionaries for the file and/or URL. Empty if neither is provided.
    """
    records: list[dict[str, Any]] = []
    path = _file_path(uploaded)
    if path:
        file_hash, size = _safe_file_hash(path)
        records.append(
            {
                "source": "upload",
                "basename": Path(path).name,
                "sha256": file_hash,
                "size_bytes": size,
                "st3gg_status": scan.get("status"),
                "export_gate": scan.get("export_gate"),
                "magic": scan.get("magic"),
                "extension": scan.get("extension"),
            }
        )
    url_record = _safe_reference_url_metadata(reference_url)
    if url_record:
        records.append(url_record)
    return records


def _creator_controls(
    reasoning_mode: str,
    video_preset: str,
    silhouette: str | None = None,
    outerwear: str | None = None,
    upper_body: str | None = None,
    footwear: str | None = None,
    palette: str | None = None,
    hardware: str | None = None,
    locate_focus: list[str] | None = None,
    seed: int | None = None,
    style_strength: str = "High Fashion",
    aspect: str = "Portrait",
) -> dict[str, Any]:
    """
    Create a control object combining wardrobe selections with generation policy and reasoning configuration.
    
    Returns:
        dict: Nested structure containing reasoning mode, video preset, wardrobe selections with locked slots,
              and FLUX generation configuration.
    """
    wardrobe = {
        "silhouette": silhouette or "structured long coat",
        "outerwear": outerwear or "black patent leather long coat",
        "upper_body": upper_body or "Chantilly lace neckline",
        "footwear": footwear or "platform boots",
        "palette": palette or "black, crimson, cyan neon",
        "hardware": hardware or "crimson hardware",
        "locked_slots": ["outerwear", "upper_body", "footwear", "jewelry"],
        "locate_focus": locate_focus or ["outerwear", "footwear", "jewelry"],
    }
    return {
        "reasoning_mode": reasoning_mode,
        "video_preset": video_preset,
        "wardrobe": wardrobe,
        "generation": {
            "flux_primary": "black-forest-labs/FLUX.2-klein-9B",
            "flux_sidecar": "black-forest-labs/FLUX.2-klein-4B",
            "lora_policy": "attempt compatible runtime adapter; report loaded/skipped/failed",
            "seed": seed,
            "style_strength": style_strength,
            "aspect": aspect,
        },
    }


def _resolve_seed(seed_value: Any) -> int:
    """Resolve user seed input. Empty or -1 means randomize."""
    try:
        if seed_value is None or str(seed_value).strip() == "":
            return secrets.randbelow(1_000_000_000)
        seed = int(float(seed_value))
    except (TypeError, ValueError):
        return secrets.randbelow(1_000_000_000)
    return secrets.randbelow(1_000_000_000) if seed < 0 else seed


def _generation_dimensions(aspect: str | None) -> tuple[int, int]:
    return ASPECT_DIMENSIONS.get(str(aspect or "Portrait"), ASPECT_DIMENSIONS["Portrait"])


def _style_modifier(style_strength: str | None) -> str:
    return STYLE_MODIFIERS.get(str(style_strength or "High Fashion"), STYLE_MODIFIERS["High Fashion"])


def _prompt_with_controls(prompt: str, controls: dict[str, Any]) -> str:
    """
    Augments a prompt with wardrobe control parameters.
    
    If any wardrobe fields are specified in the controls, appends them to the
    prompt with a "Wardrobe controls:" prefix. Otherwise returns the prompt unchanged.
    
    Parameters:
    	controls (dict[str, Any]): A controls dictionary containing a "wardrobe" key with fields for silhouette, outerwear, upper_body, footwear, palette, and hardware.
    
    Returns:
    	str: The prompt with wardrobe controls appended, or the original prompt if no wardrobe items are specified.
    """
    wardrobe = controls.get("wardrobe", {})
    additions = [
        wardrobe.get("silhouette"),
        wardrobe.get("outerwear"),
        wardrobe.get("upper_body"),
        wardrobe.get("footwear"),
        wardrobe.get("palette"),
        wardrobe.get("hardware"),
    ]
    suffix = ", ".join(str(item) for item in additions if item)
    generation = controls.get("generation", {})
    if not suffix and not generation:
        return prompt
    style = _style_modifier(str(generation.get("style_strength", "High Fashion")))
    prompt = f"{prompt}\nWardrobe controls: {suffix}" if suffix else prompt
    return f"{prompt}\nStyle direction: {style}"


def _generated_output_path(operator_state: dict[str, Any] | None) -> str | None:
    """
    Extract the generated artifact output path from the operator state.
    
    Returns:
        The output path string if a generated artifact exists, None otherwise.
    """
    generation = (operator_state or {}).get("generation") or {}
    output_path = generation.get("output_path")
    return str(output_path) if output_path else None


def _authoritative_generated_scan(operator_state: dict[str, Any] | None) -> dict[str, Any]:
    """
    Obtain the current scan for a generated artifact.
    
    Returns:
    	dict[str, Any]: A scan record sourced from the generated output file, stored state, or a default scan.
    """
    output_path = _generated_output_path(operator_state)
    if output_path:
        return scan_file(output_path)
    stored_scan = (operator_state or {}).get("generated_scan")
    return stored_scan if isinstance(stored_scan, dict) else scan_file(None)


def _checkpoint_seed(checkpoint_id: str) -> int:
    """
    Derives a numeric seed from a checkpoint ID.
    
    Parameters:
        checkpoint_id (str): A checkpoint identifier string.
    
    Returns:
        int: An integer seed bounded to less than 1,000,000, or 0 if no valid seed data can be extracted from the checkpoint ID.
    """
    suffix = "".join(char for char in checkpoint_id[-8:] if char in "0123456789abcdefABCDEF")
    if not suffix:
        return 0
    try:
        return int(suffix, 16) % 1_000_000
    except ValueError:
        return 0


def _wardrobe_summary(run: Any) -> str:
    """
    Formats outfit wardrobe slots into a semicolon-separated summary string.
    
    Returns:
        A semicolon-separated string listing each outfit slot's name, description, material, palette, and locked status.
    """
    slots = getattr(getattr(run, "outfit", None), "slots", []) or []
    return "; ".join(
        f"{slot.name}: {slot.description}, material={slot.material}, palette={slot.palette}, locked={slot.locked}"
        for slot in slots
    )


SECTIONS = ["Forge", "Wardrobe", "Lore", "Models", "Security", "Runs"]


def _button_updates(run: Any | None, operator_state: dict[str, Any] | None) -> tuple[Any, Any, Any]:
    state = operator_state or {}
    generated = bool(_generated_output_path(state)) and (state.get("generation") or {}).get("status") == "success"
    checkpoint_approved = state.get("checkpoint") == "approved"
    exported = state.get("provider_state") == "exported"
    return (
        gr.update(interactive=generated and not checkpoint_approved and not exported),
        gr.update(interactive=generated and checkpoint_approved and not exported),
        gr.update(interactive=False),
    )


def _dashboard_regions(
    run: Any | None = None,
    adult_mode: bool = False,
    scan: dict[str, Any] | None = None,
    active_section: str = "Forge",
    operator_state: dict[str, Any] | None = None,
) -> dict[str, str]:
    return render_dashboard_regions(
        run=run,
        adult_mode=adult_mode,
        scan=scan,
        relay_status=_relay_snapshot(adult_mode),
        active_section=active_section,
        operator_state=operator_state,
    )


@_zero_gpu_entrypoint
def run_weave(
    prompt: str,
    reasoning_mode: str,
    video_preset: str,
    adult_mode: bool,
    upload: Any,
    active_section: str,
    silhouette: str | None = None,
    outerwear: str | None = None,
    upper_body: str | None = None,
    footwear: str | None = None,
    palette: str | None = None,
    hardware: str | None = None,
    reference_url: str | None = None,
    seed_value: Any = -1,
    style_strength: str = "High Fashion",
    aspect: str = "Portrait",
) -> tuple[Any, ...]:
    """
    Execute the complete weaving workflow from prompt through image generation and evaluation.
    
    Assembles wardrobe controls, generates an image via FLUX, scans and judges the output through ST3GG scanning and dual judges (Minicpm and Nemotron), and compiles operator state reflecting generation status, checkpoint readiness, and export gating.
    
    Returns:
        Tuple containing dashboard region HTML fragments (topbar, command_rail, workflow, operations, inspector, drawer, status, artifacts, providers), catalog HTML, run data, catalog summary, scan results, operator state with generation details and judge evidence, and button state updates.
    """
    prompt = prompt.strip() or DEFAULT_PROMPT
    resolved_seed = _resolve_seed(seed_value)
    width, height = _generation_dimensions(aspect)
    controls = _creator_controls(
        reasoning_mode=reasoning_mode,
        video_preset=video_preset,
        silhouette=silhouette,
        outerwear=outerwear,
        upper_body=upper_body,
        footwear=footwear,
        palette=palette,
        hardware=hardware,
        seed=resolved_seed,
        style_strength=style_strength,
        aspect=aspect,
    )
    controlled_prompt = _prompt_with_controls(prompt, controls)
    reference_scan = scan_file(_file_path(upload))
    reference_metadata = _reference_metadata(upload, reference_url, reference_scan)
    run = build_command_center_run(
        prompt=controlled_prompt,
        mode=reasoning_mode,
        video_preset=video_preset,
        adult_mode=adult_mode,
        creator_controls=controls,
        reference_metadata=reference_metadata,
    )
    generation = generate_flux_image(
        run.refined_prompt.refined,
        seed=resolved_seed,
        width=width,
        height=height,
        adult_mode=adult_mode,
    )
    generated_scan = scan_file(generation.output_path) if generation.output_path else scan_file(None)
    minicpm = judge_with_minicpm(
        prompt=run.refined_prompt.refined,
        image_path=generation.output_path,
        scan=generated_scan,
        wardrobe_summary=_wardrobe_summary(run),
    )
    nemotron = judge_with_nemotron(
        prompt=run.refined_prompt.refined,
        run_packet=run.to_dict(),
        minicpm_result=minicpm.to_dict(),
    )
    if generation.status == "success":
        provider_state = "generated"
    elif generation.status in {"disabled", "missing_runtime", "no_cuda", "error"}:
        provider_state = generation.provider_state
    else:
        provider_state = "checkpointed"
    operator_state = {
        "provider_state": provider_state,
        "checkpoint": "pending_review",
        "export": generated_scan.get("export_gate", "pending"),
        "message": generation.message or "Image run complete. Human checkpoint required before export.",
        "generation": generation.to_dict(),
        "creator_controls": controls,
        "reference_metadata": reference_metadata,
        "reference_scan": reference_scan,
        "generated_scan": generated_scan,
        "minicpm_judge": minicpm.to_dict(),
        "nemotron_evidence": nemotron.to_dict(),
    }
    regions = _dashboard_regions(
        run=run,
        adult_mode=adult_mode,
        scan=generated_scan,
        active_section=active_section,
        operator_state=operator_state,
    )
    catalog = render_catalog_table(adult_mode=adult_mode)
    return (
        regions["topbar"],
        regions["command_rail"],
        regions["workflow"],
        regions["operations"],
        regions["inspector"],
        regions["drawer"],
        regions["status"],
        regions["artifacts"],
        regions["providers"],
        catalog,
        run.to_dict(),
        catalog_summary(adult_mode),
        generated_scan,
        run,
        generated_scan,
        operator_state,
        *_button_updates(run, operator_state),
    )


def toggle_adult_visibility(
    adult_mode: bool,
    active_section: str,
    upload: Any,
) -> tuple[Any, ...]:
    """
    Update the dashboard to reflect a change in adult content visibility.
    
    Re-scans any uploaded file and regenerates all dashboard regions to show or hide adult content while maintaining ST3GG, consent, and export gates.
    
    Returns:
    	tuple: Updated UI fragments and state (topbar, command rail, operations, inspector, artifacts, providers, catalog table, catalog summary, scan metadata, operator state).
    """
    scan = scan_file(_file_path(upload))
    operator_state = {
        **_default_operator_state(),
        "message": "Adult catalog visibility changed. ST3GG, consent, and export gates remain active.",
    }
    regions = _dashboard_regions(adult_mode=adult_mode, scan=scan, active_section=active_section, operator_state=operator_state)
    return (
        regions["topbar"],
        regions["command_rail"],
        regions["operations"],
        regions["inspector"],
        regions["artifacts"],
        regions["providers"],
        render_catalog_table(adult_mode=adult_mode),
        catalog_summary(adult_mode),
        scan,
        operator_state,
    )


def refresh_section(
    active_section: str,
    adult_mode: bool,
    run: Any | None,
    scan: dict[str, Any] | None,
    operator_state: dict[str, Any] | None,
) -> tuple[str, str, str, str, str, dict[str, Any]]:
    """
    Render dashboard regions for the currently selected navigation section.
    
    Returns:
        A tuple of (command_rail, operations, inspector, artifacts, providers, scan),
        where the first five elements are HTML strings for dashboard regions and the last
        is the ST3GG scan results dictionary.
    """
    scan = scan or scan_file(None)
    regions = _dashboard_regions(
        run=run,
        adult_mode=adult_mode,
        scan=scan,
        active_section=active_section,
        operator_state=operator_state or _default_operator_state(),
    )
    return regions["command_rail"], regions["operations"], regions["inspector"], regions["artifacts"], regions["providers"], scan


def _render_stateful(
    run: Any | None,
    adult_mode: bool,
    scan: dict[str, Any] | None,
    active_section: str,
    operator_state: dict[str, Any],
) -> tuple[Any, ...]:
    """
    Render the dashboard with current state and return all UI outputs and state objects.
    
    Ensures scan data exists, calls the dashboard region renderer with current state, and assembles
    a comprehensive tuple of HTML fragments, state objects, and button updates for Gradio output.
    
    Parameters:
    	run: The current run object, or None if no run is active.
    	adult_mode: Whether adult-mode visibility is enabled.
    	scan: Scan/ST3GG evidence dict. If None or falsy, defaults to empty scan from scan_file.
    	active_section: The currently active dashboard section identifier.
    	operator_state: Current operator state dict containing provider status, checkpoint, export, and messaging.
    
    Returns:
    	A tuple containing: topbar, command_rail, workflow, operations, inspector, drawer, status,
    	artifacts, providers (all HTML fragments), catalog table HTML, run dict (or empty dict),
    	catalog summary, scan dict, operator_state dict, and a Gradio update object for the stop
    	button (interactive if run exists and provider is neither idle, stopped, nor exported).
    """
    scan = scan or scan_file(None)
    regions = _dashboard_regions(
        run=run,
        adult_mode=adult_mode,
        scan=scan,
        active_section=active_section,
        operator_state=operator_state,
    )
    return (
        regions["topbar"],
        regions["command_rail"],
        regions["workflow"],
        regions["operations"],
        regions["inspector"],
        regions["drawer"],
        regions["status"],
        regions["artifacts"],
        regions["providers"],
        render_catalog_table(adult_mode=adult_mode),
        run.to_dict() if hasattr(run, "to_dict") else {},
        catalog_summary(adult_mode),
        scan,
        operator_state,
        *_button_updates(run, operator_state),
    )


def scan_reference(
    run: Any | None,
    adult_mode: bool,
    upload: Any,
    active_section: str,
    operator_state: dict[str, Any] | None,
    reference_url: str | None = None,
) -> tuple[Any, ...]:
    """
    Scan and evaluate a reference image or URL, updating the operator state with findings.
    
    Parameters:
        reference_url (str | None): Optional URL for reference metadata validation.
            Only domain and URL hash are recorded; no content crawling or copying occurs.
    
    Returns:
        Rendered dashboard outputs and the computed generated scan.
    """
    state = operator_state or _default_operator_state()
    reference_path = _file_path(upload)
    reference_scan = scan_file(reference_path)
    reference_metadata = _reference_metadata(upload, reference_url, reference_scan)
    generated_scan = _authoritative_generated_scan(state)
    minicpm = None
    if run is not None and reference_path:
        minicpm = judge_with_minicpm(
            prompt=getattr(getattr(run, "refined_prompt", None), "refined", DEFAULT_PROMPT),
            image_path=reference_path,
            scan=reference_scan,
            wardrobe_summary=_wardrobe_summary(run),
        )
    next_state = {
        **state,
        **({"reference_judge": minicpm.to_dict()} if minicpm else {}),
        "reference_metadata": reference_metadata,
        "reference_scan": reference_scan,
        "reference_export_gate": reference_scan.get("export_gate", "pending"),
        "export": state.get("export", generated_scan.get("export_gate", "pending")),
        "message": (
            "Reference scan complete. Generated artifact export gate is unchanged."
            if reference_scan.get("export_gate") == "clear"
            else "Reference scan requires review. Generated artifact export gate is unchanged."
        ),
    }
    rendered = _render_stateful(run, adult_mode, generated_scan, active_section, next_state)
    return (*rendered, generated_scan)


def approve_checkpoint(
    run: Any | None,
    adult_mode: bool,
    scan: dict[str, Any] | None,
    active_section: str,
    operator_state: dict[str, Any] | None,
) -> tuple[Any, ...]:
    """
    Approves the checkpoint if a run and generated artifact exist, blocking approval otherwise. Sets provider readiness based on the ST3GG export gate status.
    
    Returns:
    	tuple[Any, ...]: Updated dashboard and operator state reflecting the checkpoint decision.
    """
    state = operator_state or _default_operator_state()
    scan = _authoritative_generated_scan(state)
    if run is None:
        next_state = {**_default_operator_state(), "provider_state": "blocked", "message": "No run exists yet. Generate an image first."}
    elif not _generated_output_path(state):
        next_state = {
            **state,
            "provider_state": "blocked",
            "checkpoint": "pending",
            "message": "Checkpoint blocked: no generated artifact exists yet.",
        }
    else:
        export_state = scan.get("export_gate", "pending")
        next_state = {
            **state,
            "provider_state": "export_ready" if export_state == "clear" else "checkpointed",
            "checkpoint": "approved",
            "generated_scan": scan,
            "export": export_state,
            "message": (
                "Checkpoint approved. Export is ready after clear ST3GG scan."
                if export_state == "clear"
                else "Checkpoint approved. Add an override reason and click Prepare Audit Export to write an audit packet."
            ),
        }
    return _render_stateful(run, adult_mode, scan, active_section, next_state)


def export_packet(
    run: Any | None,
    adult_mode: bool,
    scan: dict[str, Any] | None,
    active_section: str,
    operator_state: dict[str, Any] | None,
    override_reason: str | None = None,
) -> tuple[Any, ...]:
    """
    Prepare an export packet for the generated artifact with precondition validation and ST3GG gating.
    
    Validates that a run, approved checkpoint, and generated artifact exist, and checks the
    ST3GG export gate status. Blocks export if any precondition fails or if the gate is not
    clear (unless an explicit override reason is provided). Writes a governed export packet
    when the gate is clear, or an audit-marked packet when overridden.
    
    Parameters:
        run: Active run packet; export is blocked if None.
        adult_mode: Whether adult content is enabled for the export.
        scan: ST3GG scan results; checked for export gate status.
        active_section: Current UI section for rendering.
        operator_state: Current operator state; defaults to idle state if None.
        override_reason: Reason to override when ST3GG gate is not clear.
    
    Returns:
        Tuple containing dashboard region HTML, run dict, catalog outputs, scan, operator state,
        and stop button interactive state.
    """
    state = operator_state or _default_operator_state()
    scan = _authoritative_generated_scan(state)
    override_reason = (override_reason or "").strip()
    if run is None:
        next_state = {**state, "provider_state": "blocked", "export": "blocked", "message": "Export waits for review: generate an image before preparing an audit packet."}
    elif state.get("checkpoint") != "approved":
        next_state = {**state, "provider_state": "blocked", "export": "blocked", "message": "Export gate active: approve the human checkpoint before release."}
    elif not _generated_output_path(state):
        next_state = {**state, "provider_state": "blocked", "export": "blocked", "message": "Export waits for review: generate an artifact before preparing evidence."}
    elif scan.get("export_gate") != "clear" and not override_reason:
        next_state = {**state, "provider_state": "blocked", "export": scan.get("export_gate", "blocked"), "message": "Export gate active: ST3GG is not clear. Add an explicit override reason to write an audit packet."}
    else:
        export_state = "clear" if scan.get("export_gate") == "clear" else "override"
        override_applies = scan.get("export_gate") != "clear" and bool(override_reason)
        export_operator_state = {
            **state,
            **({"st3gg_override_reason": override_reason} if override_applies else {}),
            "export": export_state,
        }
        export = write_export_packet(run=run, scan=scan, operator_state=export_operator_state, adult_mode=adult_mode)
        next_state = {
            **export_operator_state,
            "provider_state": "exported",
            "export": export_state,
            "export_packet": {"path": export["path"]},
            "message": f"Governed export packet prepared: {export['path']}" if export_state == "clear" else f"ST3GG override audit packet prepared: {export['path']}",
        }
    return _render_stateful(run, adult_mode, scan, active_section, next_state)


def stop_provider_job(
    run: Any | None,
    adult_mode: bool,
    scan: dict[str, Any] | None,
    active_section: str,
    operator_state: dict[str, Any] | None,
) -> tuple[Any, ...]:
    """
    Stop the active provider job.
    
    Halts the current image generation or provider handoff, preserving local evidence and 
    the dry-run packet. Re-renders the dashboard with provider state set to stopped.
    
    Returns:
        tuple[Any, ...]: Dashboard region HTML fragments, run dict, scan dict, operator state, and UI control updates.
    """
    scan = scan or scan_file(None)
    next_state = {
        **(operator_state or _default_operator_state()),
        "provider_state": "stopped",
        "message": "Provider handoff stopped. Local run packet and evidence remain available.",
    }
    return _render_stateful(run, adult_mode, scan, active_section, next_state)


def reset_demo(
    adult_mode: bool,
    active_section: str,
) -> tuple[Any, ...]:
    """
    Reset the application to its initial state by clearing all generated evidence and reinitializing operator state.
    
    Returns:
    	tuple[Any, ...]: Dashboard region HTML fragments, catalog table, empty run state, catalog summary, scan state, operator state, and button state for a reset application.
    """
    scan = scan_file(None)
    operator_state = _default_operator_state()
    regions = _dashboard_regions(adult_mode=adult_mode, scan=scan, active_section=active_section, operator_state=operator_state)
    return (
        regions["topbar"],
        regions["command_rail"],
        regions["workflow"],
        regions["operations"],
        regions["inspector"],
        regions["drawer"],
        regions["status"],
        regions["artifacts"],
        regions["providers"],
        render_catalog_table(adult_mode=adult_mode),
        {},
        catalog_summary(adult_mode),
        scan,
        None,
        scan,
        operator_state,
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
    )


initial_operator_state = _default_operator_state()
initial_regions = _dashboard_regions(scan=scan_file(None), operator_state=initial_operator_state)

with gr.Blocks(title="NEXUS Visual Weaver") as demo:
    active_run_state = gr.State(None)
    scan_state = gr.State(scan_file(None))
    operator_state = gr.State(initial_operator_state)
    topbar_html = gr.HTML(initial_regions["topbar"], container=False, visible=False)

    with gr.Row(elem_id="nw-creator-workbench", elem_classes=["nw-creator-workbench"]):
        with gr.Column(scale=5, min_width=520, elem_id="nw-creator-panel"):
            gr.Markdown("### Create Couture Image")
            gr.Markdown("Describe the look, choose wardrobe controls, then generate. Reference upload is optional.")
            prompt = gr.Textbox(
                value=DEFAULT_PROMPT,
                label="Describe the look",
                lines=4,
                max_lines=6,
            )

            with gr.Row():
                seed_value = gr.Number(value=-1, precision=0, label="Seed (-1 randomizes)")
                style_strength = gr.Dropdown(
                    ["Balanced", "High Fashion", "Cinematic"],
                    value="High Fashion",
                    label="Style Strength",
                )
                aspect = gr.Dropdown(["Portrait", "Square"], value="Portrait", label="Aspect")
            with gr.Row(elem_classes=["nw-primary-actions"]):
                run_btn = gr.Button("Generate Image", variant="primary", scale=2)
                reset_btn = gr.Button("Reset", scale=1)

            with gr.Row():
                silhouette = gr.Dropdown(
                    ["structured long coat", "fitted gothic bodice", "layered tactical silhouette"],
                    value="structured long coat",
                    label="Silhouette",
                )
                outerwear = gr.Dropdown(
                    ["black patent leather long coat", "faux fur collar coat", "tailored rain slicker"],
                    value="black patent leather long coat",
                    label="Outerwear",
                )
            with gr.Row():
                upper_body = gr.Dropdown(
                    ["Chantilly lace neckline", "black mesh layer", "structured corset bodice"],
                    value="Chantilly lace neckline",
                    label="Upper Body",
                )
                footwear = gr.Dropdown(
                    ["platform boots", "patent leather heels", "armored couture boots"],
                    value="platform boots",
                    label="Footwear",
                )
            with gr.Row():
                palette = gr.Dropdown(
                    ["black, crimson, cyan neon", "obsidian, pearl, crimson", "graphite, magenta, cold blue"],
                    value="black, crimson, cyan neon",
                    label="Palette",
                )
                hardware = gr.Dropdown(
                    ["crimson hardware", "silver occult buckles", "holographic NEXUS sigils"],
                    value="crimson hardware",
                    label="Hardware",
                )

            with gr.Accordion("Advanced: scan external file", open=False):
                gr.Markdown("Optional. Generate directly unless you need ST3GG to inspect an uploaded reference or output file.")
                with gr.Row():
                    reasoning_mode = gr.Radio(["Strict", "Frontier"], value="Strict", label="Reasoning Mode")
                    video_preset = gr.Dropdown(["Wan2.2 I2V", "LTX-2.3"], value="Wan2.2 I2V", label="Video preset (deferred)")
                with gr.Row():
                    adult_mode = gr.Checkbox(
                        value=False,
                        label="Adult Mode 18+ catalog scope",
                        info="Off by default. Never disables security, consent, or export gates.",
                    )
                    reference_url = gr.Textbox(
                        label="Reference URL (metadata only)",
                        placeholder="https://shop.example/reference-garment",
                    )
                upload = gr.File(label="Optional file for ST3GG scan", file_count="single", type="filepath")
                with gr.Row():
                    scan_btn = gr.Button("Scan Uploaded File", scale=1)
                    stop_btn = gr.Button("Stop Job", variant="stop", interactive=False, scale=1)

        with gr.Column(scale=4, min_width=460, elem_id="nw-output-panel"):
            gr.Markdown("### Output")
            artifact_html = gr.HTML(initial_regions["artifacts"], container=False)
            with gr.Row(elem_id="nw-checkpoint-actions", elem_classes=["nw-checkpoint-actions"]):
                checkpoint_btn = gr.Button("Approve Checkpoint", scale=1, interactive=False)
                export_btn = gr.Button("Prepare Audit Export", scale=1, interactive=False)
            override_reason = gr.Textbox(
                label="ST3GG Override Reason",
                placeholder="Required only when ST3GG asks for review; explain why this audit packet may be written.",
                lines=2,
                max_lines=3,
            )
            gr.Markdown("Generation is not export. Every artifact stays behind ST3GG review and human checkpoint.")

    with gr.Accordion("Run Anatomy", open=False):
        with gr.Row(elem_id="nw-workspace", elem_classes=["nw-workspace"]):
            with gr.Column(scale=1, min_width=160, elem_id="nw-native-rail"):
                section_nav = gr.Radio(SECTIONS, value="Forge", label="Technical Section", elem_id="nw-section-nav")
                command_rail_html = gr.HTML(initial_regions["command_rail"], container=False)
            with gr.Column(scale=5, min_width=620, elem_id="nw-main-column"):
                workflow_html = gr.HTML(initial_regions["workflow"], container=False)

    with gr.Accordion("Wardrobe Evidence", open=False):
        operations_html = gr.HTML(initial_regions["operations"], container=False)
        drawer_html = gr.HTML(initial_regions["drawer"], container=False)

    with gr.Accordion("Technical Evidence", open=False):
        status_html = gr.HTML(initial_regions["status"], container=False)
        inspector_html = gr.HTML(initial_regions["inspector"], container=False)
        with gr.Accordion("Provider Diagnostics", open=False):
            provider_html = gr.HTML(initial_regions["providers"], container=False)

    with gr.Accordion("Catalog, run record, and security evidence", open=False):
        catalog_html = gr.HTML(render_catalog_table(False), container=False)
        with gr.Row():
            run_json = gr.JSON(label="GenerationRun")
            catalog_json = gr.JSON(label="Catalog Summary")
            scan_json = gr.JSON(label="ST3GG Scan")

    dashboard_outputs = [
        topbar_html,
        command_rail_html,
        workflow_html,
        operations_html,
        inspector_html,
        drawer_html,
        status_html,
        artifact_html,
        provider_html,
        catalog_html,
        run_json,
        catalog_json,
        scan_json,
    ]

    stateful_outputs = dashboard_outputs + [active_run_state, scan_state, operator_state, checkpoint_btn, export_btn, stop_btn]

    operator_outputs = dashboard_outputs + [operator_state, checkpoint_btn, export_btn, stop_btn]

    run_click = run_btn.click(
        fn=run_weave,
        inputs=[
            prompt,
            reasoning_mode,
            video_preset,
            adult_mode,
            upload,
            section_nav,
            silhouette,
            outerwear,
            upper_body,
            footwear,
            palette,
            hardware,
            reference_url,
            seed_value,
            style_strength,
            aspect,
        ],
        outputs=stateful_outputs,
        api_name="run_active_weave",
        concurrency_limit=1,
        concurrency_id="flux-gpu",
    )
    run_submit = prompt.submit(
        fn=run_weave,
        inputs=[
            prompt,
            reasoning_mode,
            video_preset,
            adult_mode,
            upload,
            section_nav,
            silhouette,
            outerwear,
            upper_body,
            footwear,
            palette,
            hardware,
            reference_url,
            seed_value,
            style_strength,
            aspect,
        ],
        outputs=stateful_outputs,
        api_name=False,
        concurrency_limit=1,
        concurrency_id="flux-gpu",
    )
    adult_mode.change(
        fn=toggle_adult_visibility,
        inputs=[adult_mode, section_nav, upload],
        outputs=[
            topbar_html,
            command_rail_html,
            operations_html,
            inspector_html,
            artifact_html,
            provider_html,
            catalog_html,
            catalog_json,
            scan_json,
            operator_state,
        ],
        api_name="toggle_adult_catalog",
        queue=False,
    )
    section_nav.change(
        fn=refresh_section,
        inputs=[section_nav, adult_mode, active_run_state, scan_state, operator_state],
        outputs=[command_rail_html, operations_html, inspector_html, artifact_html, provider_html, scan_json],
        api_name=False,
        queue=False,
    )
    scan_btn.click(
        fn=scan_reference,
        inputs=[active_run_state, adult_mode, upload, section_nav, operator_state, reference_url],
        outputs=dashboard_outputs + [operator_state, checkpoint_btn, export_btn, stop_btn, scan_state],
        api_name="scan_reference",
        queue=False,
    )
    checkpoint_btn.click(
        fn=approve_checkpoint,
        inputs=[active_run_state, adult_mode, scan_state, section_nav, operator_state],
        outputs=operator_outputs,
        api_name="approve_checkpoint",
        queue=False,
    )
    export_btn.click(
        fn=export_packet,
        inputs=[active_run_state, adult_mode, scan_state, section_nav, operator_state, override_reason],
        outputs=operator_outputs,
        api_name="prepare_export_packet",
        queue=False,
    )
    stop_btn.click(
        fn=stop_provider_job,
        inputs=[active_run_state, adult_mode, scan_state, section_nav, operator_state],
        outputs=operator_outputs,
        api_name="stop_provider_job",
        queue=False,
        cancels=[run_click, run_submit],
    )
    reset_btn.click(
        fn=reset_demo,
        inputs=[adult_mode, section_nav],
        outputs=stateful_outputs,
        api_name="reset_demo_state",
        queue=False,
        cancels=[run_click, run_submit],
    )
    demo.load(
        fn=lambda: (render_catalog_table(False), catalog_summary(False), scan_file(None), scan_file(None), _default_operator_state()),
        outputs=[catalog_html, catalog_json, scan_json, scan_state, operator_state],
        api_name=False,
    )


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("NEXUS_PORT", os.environ.get("PORT", "7860"))),
        quiet=True,
        mcp_server=True,
        ssr_mode=False,
        css=APP_CSS,
        theme=APP_THEME,
    )
