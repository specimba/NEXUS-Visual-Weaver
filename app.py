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
    import spaces
except Exception:
    spaces = None

from nexus_visual_weaver.catalog import catalog_summary
from nexus_visual_weaver.exporter import write_export_packet
from nexus_visual_weaver.hf_runtime import generate_flux_image
from nexus_visual_weaver.model_relay import WeaverModelRelay
from nexus_visual_weaver.planner import build_command_center_run
from nexus_visual_weaver.provider_runtime import judge_with_minicpm, judge_with_nemotron
from nexus_visual_weaver.render import render_catalog_table, render_dashboard_regions
from nexus_visual_weaver.security import scan_file
from nexus_visual_weaver.styles import APP_CSS

APP_THEME = gr.themes.Soft()

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
    gpu_decorator = getattr(spaces, "GPU", None) if spaces is not None else None
    if gpu_decorator is None:
        return fn
    return gpu_decorator(duration=300)(fn)

def _relay_snapshot(adult_mode: bool = False) -> dict[str, Any]:
    return MODEL_RELAY.dashboard_snapshot(public_demo=not adult_mode)

def _file_path(uploaded: Any) -> str | None:
    if uploaded is None:
        return None
    if isinstance(uploaded, str):
        return uploaded
    path = getattr(uploaded, "name", None)
    return str(path) if path else None

def _safe_file_hash(path: str | None) -> tuple[str | None, int | None]:
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
    records: list[dict[str, Any]] = []
    path = _file_path(uploaded)
    if path:
        file_hash, size = _safe_file_hash(path)
        records.append({
            "source": "upload",
            "basename": Path(path).name,
            "sha256": file_hash,
            "size_bytes": size,
            "st3gg_status": scan.get("status"),
            "export_gate": scan.get("export_gate"),
            "magic": scan.get("magic"),
            "extension": scan.get("extension"),
        })
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
    generation = (operator_state or {}).get("generation") or {}
    output_path = generation.get("output_path")
    return str(output_path) if output_path else None

def _authoritative_generated_scan(operator_state: dict[str, Any] | None) -> dict[str, Any]:
    output_path = _generated_output_path(operator_state)
    if output_path:
        return scan_file(output_path)
    stored_scan = (operator_state or {}).get("generated_scan")
    return stored_scan if isinstance(stored_scan, dict) else scan_file(None)

def _checkpoint_seed(checkpoint_id: str) -> int:
    suffix = "".join(char for char in checkpoint_id[-8:] if char in "0123456789abcdefABCDEF")
    if not suffix:
        return 0
    try:
        return int(suffix, 16) % 1_000_000
    except ValueError:
        return 0

def _wardrobe_summary(run: Any) -> str:
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

# ─── Modal Integration ───
MODAL_AVAILABLE = False
try:
    import modal
    MODAL_AVAILABLE = True
except ImportError:
    pass

LORA_ADAPTERS = {
    "garment": {"repo": "NO8D/BodyControl", "desc": "Body/garment shape control", "weight": 0.75},
    "hardware": {"repo": "NO8D/ExpressionControl", "desc": "Expression/hardware detail", "weight": 0.70},
    "realism": {"repo": "fal/realism-detailer", "desc": "Photorealistic detail boost", "weight": 0.60},
    "metallic": {"repo": "ilkerzgi/metallic", "desc": "Metallic material finish", "weight": 0.55},
    "glittering": {"repo": "ilkerzgi/glittering-portrait", "desc": "Glittering portrait effects", "weight": 0.55},
    "embroidery": {"repo": "ilkerzgi/embroidery-patch", "desc": "Embroidery/patch textures", "weight": 0.55},
}

GPU_OPTIONS = {
    "A100-80GB": {"price": 1.80, "modal_gpu": "A100"},
    "A100-40GB": {"price": 1.10, "modal_gpu": "A10G"},
    "L40S": {"price": 1.05, "modal_gpu": "L40S"},
    "T4": {"price": 0.40, "modal_gpu": "T4"},
}

MODAL_COST_TRACKER = {"credits_remaining": 250.88, "total_spent": 0.0, "refinements": 0}

def _modal_refine_image(image_bytes: bytes, user_addition: str, gpu_type: str = "A100-80GB",
                         strength: float = 0.58, steps: int = 32, guidance_scale: float = 3.8,
                         seed: int = -1, lora_adapters: list | None = None,
                         negative_prompt: str = "blurry, low quality, deformed, extra limbs") -> tuple:
    if not MODAL_AVAILABLE:
        return None, "❌ Modal not installed"
    try:
        fn = modal.Function.lookup("nexus-couture-refine-v2", "refine_couture")
        result_bytes = fn.remote(
            image_bytes=image_bytes,
            user_addition=user_addition,
            strength=strength,
            steps=steps,
            guidance_scale=guidance_scale,
            seed=seed,
            lora_adapters=lora_adapters or ["garment"],
            negative_prompt=negative_prompt,
            gpu_type=gpu_type,
        )
        gpu_info = GPU_OPTIONS.get(gpu_type, GPU_OPTIONS["A100-80GB"])
        est_cost = round(gpu_info["price"] * (steps / 60), 4)
        MODAL_COST_TRACKER["total_spent"] += est_cost
        MODAL_COST_TRACKER["credits_remaining"] -= est_cost
        MODAL_COST_TRACKER["refinements"] += 1
        return result_bytes, f"✅ Modal refinement complete on {gpu_type}"
    except Exception as e:
        return None, f"❌ Modal error: {str(e)[:200]}"

def _modal_health_check() -> dict:
    if not MODAL_AVAILABLE:
        return {"status": "unavailable", "message": "Modal not installed"}
    try:
        fn = modal.Function.lookup("nexus-couture-refine-v2", "check_modal_health")
        return fn.remote()
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}

@_zero_gpu_entrypoint
def run_weave(
    prompt, reasoning_mode, video_preset, adult_mode, upload, active_section,
    silhouette=None, outerwear=None, upper_body=None, footwear=None, palette=None,
    hardware=None, reference_url=None, seed_value=-1, style_strength="High Fashion", aspect="Portrait",
):
    prompt = prompt.strip() or DEFAULT_PROMPT
    resolved_seed = _resolve_seed(seed_value)
    width, height = _generation_dimensions(aspect)
    controls = _creator_controls(
        reasoning_mode=reasoning_mode, video_preset=video_preset,
        silhouette=silhouette, outerwear=outerwear, upper_body=upper_body,
        footwear=footwear, palette=palette, hardware=hardware,
        seed=resolved_seed, style_strength=style_strength, aspect=aspect,
    )
    controlled_prompt = _prompt_with_controls(prompt, controls)
    reference_scan = scan_file(_file_path(upload))
    reference_metadata = _reference_metadata(upload, reference_url, reference_scan)
    run = build_command_center_run(
        prompt=controlled_prompt, mode=reasoning_mode, video_preset=video_preset,
        adult_mode=adult_mode, creator_controls=controls, reference_metadata=reference_metadata,
    )
    generation = generate_flux_image(
        run.refined_prompt.refined, seed=resolved_seed, width=width, height=height, adult_mode=adult_mode,
    )
    generated_scan = scan_file(generation.output_path) if generation.output_path else scan_file(None)
    minicpm = judge_with_minicpm(
        prompt=run.refined_prompt.refined, image_path=generation.output_path,
        scan=generated_scan, wardrobe_summary=_wardrobe_summary(run),
    )
    nemotron = judge_with_nemotron(
        prompt=run.refined_prompt.refined, run_packet=run.to_dict(), minicpm_result=minicpm.to_dict(),
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
        run=run, adult_mode=adult_mode, scan=generated_scan,
        active_section=active_section, operator_state=operator_state,
    )
    catalog = render_catalog_table(adult_mode=adult_mode)
    return (
        regions["topbar"], regions["command_rail"], regions["workflow"],
        regions["operations"], regions["inspector"], regions["drawer"],
        regions["status"], regions["artifacts"], regions["providers"],
        catalog, run.to_dict(), catalog_summary(adult_mode),
        generated_scan, run, generated_scan, operator_state,
        *_button_updates(run, operator_state),
    )

def toggle_adult_visibility(adult_mode, active_section, upload):
    scan = scan_file(_file_path(upload))
    operator_state = {
        **_default_operator_state(),
        "message": "Adult catalog visibility changed. ST3GG, consent, and export gates remain active.",
    }
    regions = _dashboard_regions(adult_mode=adult_mode, scan=scan, active_section=active_section, operator_state=operator_state)
    return (
        regions["topbar"], regions["command_rail"], regions["operations"],
        regions["inspector"], regions["artifacts"], regions["providers"],
        render_catalog_table(adult_mode=adult_mode), catalog_summary(adult_mode), scan, operator_state,
    )

def refresh_section(active_section, adult_mode, run, scan, operator_state):
    scan = scan or scan_file(None)
    regions = _dashboard_regions(
        run=run, adult_mode=adult_mode, scan=scan,
        active_section=active_section, operator_state=operator_state or _default_operator_state(),
    )
    return regions["command_rail"], regions["operations"], regions["inspector"], regions["artifacts"], regions["providers"], scan

def _render_stateful(run, adult_mode, scan, active_section, operator_state):
    scan = scan or scan_file(None)
    regions = _dashboard_regions(
        run=run, adult_mode=adult_mode, scan=scan,
        active_section=active_section, operator_state=operator_state,
    )
    return (
        regions["topbar"], regions["command_rail"], regions["workflow"],
        regions["operations"], regions["inspector"], regions["drawer"],
        regions["status"], regions["artifacts"], regions["providers"],
        render_catalog_table(adult_mode=adult_mode),
        run.to_dict() if hasattr(run, "to_dict") else {},
        catalog_summary(adult_mode), scan, operator_state,
        *_button_updates(run, operator_state),
    )

def scan_reference(run, adult_mode, upload, active_section, operator_state, reference_url=None):
    state = operator_state or _default_operator_state()
    reference_path = _file_path(upload)
    reference_scan = scan_file(reference_path)
    reference_metadata = _reference_metadata(upload, reference_url, reference_scan)
    generated_scan = _authoritative_generated_scan(state)
    minicpm = None
    if run is not None and reference_path:
        minicpm = judge_with_minicpm(
            prompt=getattr(getattr(run, "refined_prompt", None), "refined", DEFAULT_PROMPT),
            image_path=reference_path, scan=reference_scan, wardrobe_summary=_wardrobe_summary(run),
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

def approve_checkpoint(run, adult_mode, scan, active_section, operator_state):
    state = operator_state or _default_operator_state()
    scan = _authoritative_generated_scan(state)
    if run is None:
        next_state = {**_default_operator_state(), "provider_state": "blocked", "message": "No run exists yet. Generate an image first."}
    elif not _generated_output_path(state):
        next_state = {**state, "provider_state": "blocked", "checkpoint": "pending", "message": "Checkpoint blocked: no generated artifact exists yet."}
    else:
        export_state = scan.get("export_gate", "pending")
        next_state = {
            **state,
            "provider_state": "export_ready" if export_state == "clear" else "checkpointed",
            "checkpoint": "approved", "generated_scan": scan, "export": export_state,
            "message": (
                "Checkpoint approved. Export is ready after clear ST3GG scan."
                if export_state == "clear"
                else "Checkpoint approved. Add an override reason and click Prepare Audit Export to write an audit packet."
            ),
        }
    return _render_stateful(run, adult_mode, scan, active_section, next_state)

def export_packet(run, adult_mode, scan, active_section, operator_state, override_reason=None):
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
        export_operator_state = {**state, **({"st3gg_override_reason": override_reason} if override_applies else {}), "export": export_state}
        export = write_export_packet(run=run, scan=scan, operator_state=export_operator_state, adult_mode=adult_mode)
        next_state = {
            **export_operator_state, "provider_state": "exported", "export": export_state,
            "export_packet": {"path": export["path"]},
            "message": f"Governed export packet prepared: {export['path']}" if export_state == "clear" else f"ST3GG override audit packet prepared: {export['path']}",
        }
    return _render_stateful(run, adult_mode, scan, active_section, next_state)

def stop_provider_job(run, adult_mode, scan, active_section, operator_state):
    scan = scan or scan_file(None)
    next_state = {
        **(operator_state or _default_operator_state()),
        "provider_state": "stopped",
        "message": "Provider handoff stopped. Local run packet and evidence remain available.",
    }
    return _render_stateful(run, adult_mode, scan, active_section, next_state)

def reset_demo(adult_mode, active_section):
    scan = scan_file(None)
    operator_state = _default_operator_state()
    regions = _dashboard_regions(adult_mode=adult_mode, scan=scan, active_section=active_section, operator_state=operator_state)
    return (
        regions["topbar"], regions["command_rail"], regions["workflow"],
        regions["operations"], regions["inspector"], regions["drawer"],
        regions["status"], regions["artifacts"], regions["providers"],
        render_catalog_table(adult_mode=adult_mode),
        {}, catalog_summary(adult_mode), scan, None, scan, operator_state,
        gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False),
    )

# ─── Modal Tab Handlers ───
def modal_refine_handler(input_image, user_addition, gpu_type, strength, steps, guidance, seed, lora_choices, negative_prompt):
    if input_image is None:
        return None, "❌ No input image provided"
    from PIL import Image as PILImage
    from io import BytesIO
    buf = BytesIO()
    if isinstance(input_image, str):
        img = PILImage.open(input_image)
    else:
        img = PILImage.open(input_image)
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()
    result_bytes, message = _modal_refine_image(
        image_bytes=image_bytes, user_addition=user_addition,
        gpu_type=gpu_type, strength=strength, steps=int(steps),
        guidance_scale=guidance, seed=int(seed),
        lora_adapters=lora_choices if lora_choices else ["garment"],
        negative_prompt=negative_prompt,
    )
    if result_bytes:
        result_img = PILImage.open(BytesIO(result_bytes))
        cost_info = f"Credits remaining: ${MODAL_COST_TRACKER['credits_remaining']:.2f} | Refinements: {MODAL_COST_TRACKER['refinements']}"
        return result_img, f"{message}\n{cost_info}"
    return None, message

def modal_health_handler():
    result = _modal_health_check()
    if result.get("status") == "healthy":
        return f"✅ Modal connected\nGPU: {result.get('gpu', 'N/A')}"
    elif result.get("status") == "unavailable":
        return f"⚠️ {result.get('message', 'Modal not available')}"
    else:
        return f"❌ Modal error: {result.get('message', 'Unknown')}"

initial_operator_state = _default_operator_state()
initial_regions = _dashboard_regions(scan=scan_file(None), operator_state=initial_operator_state)

with gr.Blocks(title="NEXUS Visual Weaver") as demo:
    active_run_state = gr.State(None)
    scan_state = gr.State(scan_file(None))
    operator_state = gr.State(initial_operator_state)
    topbar_html = gr.HTML(initial_regions["topbar"], container=False, visible=False)

    with gr.Tabs():
        # ═══ Tab 1: Studio ═══
        with gr.Tab("🧵 Studio"):
            with gr.Row(elem_id="nw-creator-workbench", elem_classes=["nw-creator-workbench"]):
                with gr.Column(scale=5, min_width=520, elem_id="nw-creator-panel"):
                    gr.Markdown("### Create Couture Image")
                    gr.Markdown("Describe the look, choose wardrobe controls, then generate. Reference upload is optional.")
                    prompt = gr.Textbox(value=DEFAULT_PROMPT, label="Describe the look", lines=4, max_lines=6)
                    with gr.Row():
                        seed_value = gr.Number(value=-1, precision=0, label="Seed (-1 randomizes)")
                        style_strength = gr.Dropdown(["Balanced", "High Fashion", "Cinematic"], value="High Fashion", label="Style Strength")
                        aspect = gr.Dropdown(["Portrait", "Square"], value="Portrait", label="Aspect")
                    with gr.Row(elem_classes=["nw-primary-actions"]):
                        run_btn = gr.Button("Generate Image", variant="primary", scale=2)
                        reset_btn = gr.Button("Reset", scale=1)
                    with gr.Row():
                        silhouette = gr.Dropdown(["structured long coat", "fitted gothic bodice", "layered tactical silhouette"], value="structured long coat", label="Silhouette")
                        outerwear = gr.Dropdown(["black patent leather long coat", "faux fur collar coat", "tailored rain slicker"], value="black patent leather long coat", label="Outerwear")
                    with gr.Row():
                        upper_body = gr.Dropdown(["Chantilly lace neckline", "black mesh layer", "structured corset bodice"], value="Chantilly lace neckline", label="Upper Body")
                        footwear = gr.Dropdown(["platform boots", "patent leather heels", "armored couture boots"], value="platform boots", label="Footwear")
                    with gr.Row():
                        palette = gr.Dropdown(["black, crimson, cyan neon", "obsidian, pearl, crimson", "graphite, magenta, cold blue"], value="black, crimson, cyan neon", label="Palette")
                        hardware = gr.Dropdown(["crimson hardware", "silver occult buckles", "holographic NEXUS sigils"], value="crimson hardware", label="Hardware")
                    with gr.Accordion("Advanced: scan external file", open=False):
                        gr.Markdown("Optional. Generate directly unless you need ST3GG to inspect an uploaded reference or output file.")
                        with gr.Row():
                            reasoning_mode = gr.Radio(["Strict", "Frontier"], value="Strict", label="Reasoning Mode")
                            video_preset = gr.Dropdown(["Wan2.2 I2V", "LTX-2.3"], value="Wan2.2 I2V", label="Video preset (deferred)")
                        with gr.Row():
                            adult_mode = gr.Checkbox(value=False, label="Adult Mode 18+ catalog scope", info="Off by default. Never disables security, consent, or export gates.")
                            reference_url = gr.Textbox(label="Reference URL (metadata only)", placeholder="https://shop.example/reference-garment")
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
                        lines=2, max_lines=3,
                    )
                    gr.Markdown("Generation is not export. Every artifact stays behind ST3GG review and human checkpoint.")

        # ═══ Tab 2: Modal Refinement (ACTIVE) ═══
        with gr.Tab("⚡ Modal"):
            gr.Markdown("## ⚡ Modal GPU Refinement")
            gr.Markdown("Send a generated image to Modal for FLUX.1-Kontext-dev refinement with multi-LoRA on dedicated GPU.")
            with gr.Row():
                with gr.Column(scale=1):
                    modal_input_image = gr.Image(label="Input Image (from Studio or upload)", type="filepath")
                    modal_user_addition = gr.Textbox(label="Additional prompt text", placeholder="glowing crimson buckles, wet pavement reflection", value="")
                    modal_gpu = gr.Dropdown(choices=list(GPU_OPTIONS.keys()), value="A100-80GB", label="GPU Type")
                    modal_loras = gr.CheckboxGroup(choices=list(LORA_ADAPTERS.keys()), value=["garment", "realism"], label="LoRA Adapters")
                    with gr.Row():
                        modal_strength = gr.Slider(0.1, 1.0, value=0.58, step=0.02, label="Strength")
                        modal_steps = gr.Slider(10, 64, value=32, step=2, label="Steps")
                    with gr.Row():
                        modal_guidance = gr.Slider(1.0, 15.0, value=3.8, step=0.2, label="Guidance Scale")
                        modal_seed = gr.Number(value=-1, precision=0, label="Seed (-1 random)")
                    modal_negative = gr.Textbox(label="Negative Prompt", value="blurry, low quality, deformed, extra limbs, bad anatomy, watermark, text")
                    with gr.Row():
                        modal_refine_btn = gr.Button("🎨 Refine on Modal", variant="primary")
                        modal_health_btn = gr.Button("🔍 Health Check", variant="secondary")
                with gr.Column(scale=1):
                    modal_output_image = gr.Image(label="Refined Output")
                    modal_status = gr.Textbox(label="Status", lines=3, interactive=False)
                    modal_cost_display = gr.Markdown(
                        f"**Credits Remaining:** ${MODAL_COST_TRACKER['credits_remaining']:.2f} | "
                        f"**Spent:** ${MODAL_COST_TRACKER['total_spent']:.4f} | "
                        f"**Refinements:** {MODAL_COST_TRACKER['refinements']}"
                    )
            modal_refine_btn.click(
                fn=modal_refine_handler,
                inputs=[modal_input_image, modal_user_addition, modal_gpu, modal_strength,
                        modal_steps, modal_guidance, modal_seed, modal_loras, modal_negative],
                outputs=[modal_output_image, modal_status],
            )
            modal_health_btn.click(fn=modal_health_handler, inputs=[], outputs=[modal_status])

        # ═══ Tab 3: LoRA Lab (ACTIVE) ═══
        with gr.Tab("🧪 LoRA Lab"):
            gr.Markdown("## 🧪 LoRA Training Lab")
            gr.Markdown("Train custom LoRA adapters on Modal GPU. Connect a dataset repo and configure training parameters.")
            with gr.Row():
                with gr.Column(scale=1):
                    lora_dataset_repo = gr.Textbox(label="Dataset Repo (HF)", value="specimba/nexus-couture-training", placeholder="username/dataset-name")
                    lora_output_name = gr.Textbox(label="Output Adapter Name", value="nexus-couture-v1")
                    with gr.Row():
                        lora_rank = gr.Slider(4, 64, value=16, step=4, label="Rank")
                        lora_lr = gr.Textbox(label="Learning Rate", value="1e-4")
                    with gr.Row():
                        lora_steps = gr.Slider(100, 3000, value=800, step=100, label="Training Steps")
                        lora_batch = gr.Slider(1, 16, value=4, step=1, label="Batch Size")
                    lora_push = gr.Checkbox(label="Push to Hub after training", value=False)
                    lora_hub_repo = gr.Textbox(label="Hub Repo (if pushing)", value="build-small-hackathon/nexus-couture-lora")
                    lora_train_btn = gr.Button("🚀 Start Training on Modal", variant="primary")
                with gr.Column(scale=1):
                    lora_train_status = gr.Textbox(label="Training Status", lines=8, interactive=False)
                    gr.Markdown("### Available LoRA Adapters")
                    lora_catalog_md = "\n".join(
                        f"- **{k}**: {v['desc']} (`{v['repo']}`, weight={v['weight']})"
                        for k, v in LORA_ADAPTERS.items()
                    )
                    gr.Markdown(lora_catalog_md)
            def lora_train_handler(dataset_repo, output_name, rank, lr, steps, batch, push, hub_repo):
                if not MODAL_AVAILABLE:
                    return "❌ Modal not installed"
                try:
                    fn = modal.Function.lookup("nexus-couture-lora-trainer", "train_nexus_couture_lora")
                    fn.remote(
                        dataset_repo=dataset_repo, output_name=output_name,
                        rank=int(rank), steps=int(steps), learning_rate=float(lr),
                        batch_size=int(batch), push_to_hub=push, hub_repo=hub_repo,
                    )
                    return f"✅ Training triggered on Modal!\nDataset: {dataset_repo}\nOutput: {output_name}\nRank: {rank}, Steps: {steps}, LR: {lr}"
                except Exception as e:
                    return f"❌ Training error: {str(e)[:300]}"
            lora_train_btn.click(
                fn=lora_train_handler,
                inputs=[lora_dataset_repo, lora_output_name, lora_rank, lora_lr,
                        lora_steps, lora_batch, lora_push, lora_hub_repo],
                outputs=[lora_train_status],
            )

        # ═══ Tab 4: Technical Evidence ═══
        with gr.Tab("🔍 Evidence"):
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
        topbar_html, command_rail_html, workflow_html, operations_html,
        inspector_html, drawer_html, status_html, artifact_html,
        provider_html, catalog_html, run_json, catalog_json, scan_json,
    ]
    stateful_outputs = dashboard_outputs + [active_run_state, scan_state, operator_state, checkpoint_btn, export_btn, stop_btn]
    operator_outputs = dashboard_outputs + [operator_state, checkpoint_btn, export_btn, stop_btn]

    run_click = run_btn.click(
        fn=run_weave,
        inputs=[prompt, reasoning_mode, video_preset, adult_mode, upload, section_nav,
                silhouette, outerwear, upper_body, footwear, palette, hardware,
                reference_url, seed_value, style_strength, aspect],
        outputs=stateful_outputs, api_name="run_active_weave",
        concurrency_limit=1, concurrency_id="flux-gpu",
    )

    run_submit = prompt.submit(
        fn=run_weave,
        inputs=[prompt, reasoning_mode, video_preset, adult_mode, upload, section_nav,
                silhouette, outerwear, upper_body, footwear, palette, hardware,
                reference_url, seed_value, style_strength, aspect],
        outputs=stateful_outputs, api_name=False,
        concurrency_limit=1, concurrency_id="flux-gpu",
    )

    adult_mode.change(
        fn=toggle_adult_visibility,
        inputs=[adult_mode, section_nav, upload],
        outputs=[topbar_html, command_rail_html, operations_html, inspector_html,
                 artifact_html, provider_html, catalog_html, catalog_json, scan_json, operator_state],
        api_name="toggle_adult_catalog", queue=False,
    )

    section_nav.change(
        fn=refresh_section,
        inputs=[section_nav, adult_mode, active_run_state, scan_state, operator_state],
        outputs=[command_rail_html, operations_html, inspector_html, artifact_html, provider_html, scan_json],
        api_name=False, queue=False,
    )

    scan_btn.click(
        fn=scan_reference,
        inputs=[active_run_state, adult_mode, upload, section_nav, operator_state, reference_url],
        outputs=dashboard_outputs + [operator_state, checkpoint_btn, export_btn, stop_btn, scan_state],
        api_name="scan_reference", queue=False,
    )

    checkpoint_btn.click(
        fn=approve_checkpoint,
        inputs=[active_run_state, adult_mode, scan_state, section_nav, operator_state],
        outputs=operator_outputs, api_name="approve_checkpoint", queue=False,
    )

    export_btn.click(
        fn=export_packet,
        inputs=[active_run_state, adult_mode, scan_state, section_nav, operator_state, override_reason],
        outputs=operator_outputs, api_name="prepare_export_packet", queue=False,
    )

    stop_btn.click(
        fn=stop_provider_job,
        inputs=[active_run_state, adult_mode, scan_state, section_nav, operator_state],
        outputs=operator_outputs, api_name="stop_provider_job", queue=False,
        cancels=[run_click, run_submit],
    )

    reset_btn.click(
        fn=reset_demo,
        inputs=[adult_mode, section_nav],
        outputs=stateful_outputs, api_name="reset_demo_state", queue=False,
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
    )
