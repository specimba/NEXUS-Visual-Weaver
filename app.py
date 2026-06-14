"""NEXUS Visual Weaver - Build Small Hackathon command center."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

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
from nexus_visual_weaver.hf_runtime import generate_flux_image
from nexus_visual_weaver.model_relay import WeaverModelRelay
from nexus_visual_weaver.planner import build_command_center_run
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


def _default_operator_state() -> dict[str, Any]:
    return {
        "provider_state": "idle",
        "checkpoint": "pending",
        "export": "pending",
        "message": "No operator action yet.",
    }


def _zero_gpu_entrypoint(fn: Any) -> Any:
    """Expose one callback to ZeroGPU without making local development depend on Spaces."""
    gpu_decorator = getattr(spaces, "GPU", None) if spaces is not None else None
    if gpu_decorator is None:
        return fn
    return gpu_decorator(duration=900)(fn)


def _relay_snapshot(adult_mode: bool = False) -> dict[str, Any]:
    return MODEL_RELAY.dashboard_snapshot(public_demo=not adult_mode)


def _file_path(uploaded: Any) -> str | None:
    if uploaded is None:
        return None
    if isinstance(uploaded, str):
        return uploaded
    path = getattr(uploaded, "name", None)
    return str(path) if path else None


SECTIONS = ["Forge", "Wardrobe", "Lore", "Models", "Security", "Runs"]


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
) -> tuple[str, str, str, str, str, str, str, str, str, str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    prompt = prompt.strip() or DEFAULT_PROMPT
    run = build_command_center_run(
        prompt=prompt,
        mode=reasoning_mode,
        video_preset=video_preset,
        adult_mode=adult_mode,
    )
    scan = scan_file(_file_path(upload))
    generation = generate_flux_image(run.refined_prompt.refined, seed=int(run.checkpoint.checkpoint_id[-6:], 16) % 1_000_000)
    operator_state = {
        "provider_state": generation.provider_state if generation.status in {"success", "error", "missing_runtime", "no_cuda"} else "checkpointed",
        "checkpoint": "pending_review",
        "export": scan.get("export_gate", "pending"),
        "message": generation.message or "Run packet generated. Human checkpoint required before provider promotion or export.",
        "generation": generation.to_dict(),
    }
    regions = _dashboard_regions(
        run=run,
        adult_mode=adult_mode,
        scan=scan,
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
        scan,
        run,
        scan,
        operator_state,
        gr.update(interactive=True),
    )


def toggle_adult_visibility(
    adult_mode: bool,
    active_section: str,
    upload: Any,
) -> tuple[str, str, str, str, str, str, str, dict[str, Any], dict[str, Any]]:
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
    Updates dashboard regions for the selected navigation section.
    
    Returns:
        A tuple containing HTML strings for command_rail, operations, inspector, artifacts, and providers regions, followed by the security scan results.
    """
    scan = scan_file(_file_path(upload))
    regions = _dashboard_regions(adult_mode=adult_mode, scan=scan, active_section=active_section)
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
) -> tuple[str, str, str, str, str, str, str, str, str, str, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Any]:
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
        gr.update(interactive=run is not None and operator_state.get("provider_state") not in {"idle", "stopped", "exported"}),
    )
    upload: Any,
) -> tuple[str, str, str, str, str, dict[str, Any]]:
    scan = scan_file(_file_path(upload))
    regions = _dashboard_regions(adult_mode=adult_mode, scan=scan, active_section=active_section)
    return regions["command_rail"], regions["operations"], regions["inspector"], regions["artifacts"], regions["providers"], scan


def scan_reference(
    run: Any | None,
    adult_mode: bool,
    upload: Any,
    active_section: str,
    operator_state: dict[str, Any] | None,
) -> tuple[str, str, str, str, str, str, str, str, str, str, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Any, dict[str, Any]]:
    scan = scan_file(_file_path(upload))
    next_state = {
        **(operator_state or _default_operator_state()),
        "export": scan.get("export_gate", "pending"),
        "message": "Reference scan complete. Export gate is clear." if scan.get("export_gate") == "clear" else "Reference scan requires review before export.",
    }
    rendered = _render_stateful(run, adult_mode, scan, active_section, next_state)
    return (*rendered, scan)


def approve_checkpoint(
    run: Any | None,
    adult_mode: bool,
    scan: dict[str, Any] | None,
    active_section: str,
    operator_state: dict[str, Any] | None,
) -> tuple[str, str, str, str, str, str, str, str, str, str, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Any]:
    scan = scan or scan_file(None)
    if run is None:
        next_state = {**_default_operator_state(), "provider_state": "blocked", "message": "No run exists yet. Run Active Weave first."}
    else:
        export_state = scan.get("export_gate", "pending")
        next_state = {
            **(operator_state or _default_operator_state()),
            "provider_state": "export_ready" if export_state == "clear" else "checkpointed",
            "checkpoint": "approved",
            "export": export_state,
            "message": "Checkpoint approved. Export is ready after clear ST3GG scan." if export_state == "clear" else "Checkpoint approved, but export still waits on ST3GG review.",
        }
    return _render_stateful(run, adult_mode, scan, active_section, next_state)


def export_packet(
    run: Any | None,
    adult_mode: bool,
    scan: dict[str, Any] | None,
    active_section: str,
    operator_state: dict[str, Any] | None,
) -> tuple[str, str, str, str, str, str, str, str, str, str, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Any]:
    scan = scan or scan_file(None)
    state = operator_state or _default_operator_state()
    if run is None:
        next_state = {**state, "provider_state": "blocked", "export": "blocked", "message": "Export blocked: no active run packet exists."}
    elif state.get("checkpoint") != "approved":
        next_state = {**state, "provider_state": "blocked", "export": "blocked", "message": "Export blocked: human checkpoint has not been approved."}
    elif scan.get("export_gate") != "clear":
        next_state = {**state, "provider_state": "blocked", "export": scan.get("export_gate", "blocked"), "message": "Export blocked: ST3GG gate is not clear."}
    else:
        next_state = {**state, "provider_state": "exported", "export": "clear", "message": "Governed export packet prepared with run, catalog, and ST3GG evidence."}
    return _render_stateful(run, adult_mode, scan, active_section, next_state)


def stop_provider_job(
    run: Any | None,
    adult_mode: bool,
    scan: dict[str, Any] | None,
    active_section: str,
    operator_state: dict[str, Any] | None,
) -> tuple[str, str, str, str, str, str, str, str, str, str, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Any]:
    scan = scan or scan_file(None)
    next_state = {
        **(operator_state or _default_operator_state()),
        "provider_state": "stopped",
        "message": "Provider handoff stopped. Local dry-run packet and evidence remain available.",
    }
    return _render_stateful(run, adult_mode, scan, active_section, next_state)


def reset_demo(
    adult_mode: bool,
    active_section: str,
) -> tuple[str, str, str, str, str, str, str, str, str, str, dict[str, Any], dict[str, Any], dict[str, Any], None, dict[str, Any], dict[str, Any], Any]:
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
    )


initial_operator_state = _default_operator_state()
initial_regions = _dashboard_regions(scan=scan_file(None), operator_state=initial_operator_state)

with gr.Blocks(title="NEXUS Visual Weaver") as demo:
    active_run_state = gr.State(None)
    scan_state = gr.State(scan_file(None))
    operator_state = gr.State(initial_operator_state)
    topbar_html = gr.HTML(initial_regions["topbar"], container=False)

    with gr.Group(elem_id="nw-inputs", elem_classes=["nw-control-panel"]):
        gr.HTML(render_command_header(), container=False)
        with gr.Row():
            prompt = gr.Textbox(
                value=DEFAULT_PROMPT,
                label="Creative Brief",
                lines=3,
                max_lines=6,
                scale=5,
            )
            with gr.Column(scale=2):
                reasoning_mode = gr.Radio(
                    ["Strict", "Frontier"],
                    value="Strict",
                    label="Reasoning Mode",
                )
                video_preset = gr.Dropdown(
                    ["Wan2.2 I2V", "LTX-2.3"],
                    value="Wan2.2 I2V",
                    label="Video Path Preset",
                )
        with gr.Row():
            upload = gr.File(
                label="Reference / Output For ST3GG Scan",
                file_count="single",
                type="filepath",
                scale=3,
            )
            adult_mode = gr.Checkbox(
                value=False,
                label="Adult Mode 18+ catalog scope",
                info="Off by default. Enables adult-tagged catalog entries but does not disable security, consent, or export gates.",
                scale=2,
            )
            run_btn = gr.Button("Run Active Weave", variant="primary", scale=1)
            stop_btn = gr.Button("Stop Provider Job", variant="stop", interactive=False, scale=1)
        with gr.Row(elem_id="nw-operator-actions", elem_classes=["nw-operator-actions"]):
            scan_btn = gr.Button("Scan Reference", scale=1)
            checkpoint_btn = gr.Button("Approve Checkpoint", scale=1)
            export_btn = gr.Button("Prepare Export Packet", scale=1)
            reset_btn = gr.Button("Reset Demo State", scale=1)

    with gr.Row(elem_id="nw-workspace", elem_classes=["nw-workspace"]):
        with gr.Column(scale=1, min_width=150, elem_id="nw-native-rail"):
            section_nav = gr.Radio(
                SECTIONS,
                value="Forge",
                label="Command Rail",
                elem_id="nw-section-nav",
            )
            command_rail_html = gr.HTML(initial_regions["command_rail"], container=False)
        with gr.Column(scale=5, min_width=620, elem_id="nw-main-column"):
            workflow_html = gr.HTML(initial_regions["workflow"], container=False)
            operations_html = gr.HTML(initial_regions["operations"], container=False)
            artifact_html = gr.HTML(initial_regions["artifacts"], container=False)
            drawer_html = gr.HTML(initial_regions["drawer"], container=False)
        with gr.Column(scale=2, min_width=340, elem_id="nw-side-column"):
            inspector_html = gr.HTML(initial_regions["inspector"], container=False)
            provider_html = gr.HTML(initial_regions["providers"], container=False)

    status_html = gr.HTML(initial_regions["status"], container=False)

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

    stateful_outputs = dashboard_outputs + [active_run_state, scan_state, operator_state, stop_btn]

    operator_outputs = dashboard_outputs + [operator_state, stop_btn]

    run_btn.click(
        fn=run_weave,
        inputs=[prompt, reasoning_mode, video_preset, adult_mode, upload, section_nav],
        outputs=stateful_outputs,
        outputs=[
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
        ],
        api_name="run_active_weave",
    )
    prompt.submit(
        fn=run_weave,
        inputs=[prompt, reasoning_mode, video_preset, adult_mode, upload, section_nav],
        outputs=stateful_outputs,
        outputs=[
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
        ],
        api_name=False,
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
    )
    section_nav.change(
        fn=refresh_section,
        inputs=[section_nav, adult_mode, active_run_state, scan_state, operator_state],
        inputs=[section_nav, adult_mode, upload],
        outputs=[command_rail_html, operations_html, inspector_html, artifact_html, provider_html, scan_json],
        api_name=False,
    )
    scan_btn.click(
        fn=scan_reference,
        inputs=[active_run_state, adult_mode, upload, section_nav, operator_state],
        outputs=dashboard_outputs + [operator_state, stop_btn, scan_state],
        api_name="scan_reference",
    )
    checkpoint_btn.click(
        fn=approve_checkpoint,
        inputs=[active_run_state, adult_mode, scan_state, section_nav, operator_state],
        outputs=operator_outputs,
        api_name="approve_checkpoint",
    )
    export_btn.click(
        fn=export_packet,
        inputs=[active_run_state, adult_mode, scan_state, section_nav, operator_state],
        outputs=operator_outputs,
        api_name="prepare_export_packet",
    )
    stop_btn.click(
        fn=stop_provider_job,
        inputs=[active_run_state, adult_mode, scan_state, section_nav, operator_state],
        outputs=operator_outputs,
        api_name="stop_provider_job",
    )
    reset_btn.click(
        fn=reset_demo,
        inputs=[adult_mode, section_nav],
        outputs=stateful_outputs,
        api_name="reset_demo_state",
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
