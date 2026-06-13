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
) -> dict[str, str]:
    return render_dashboard_regions(
        run=run,
        adult_mode=adult_mode,
        scan=scan,
        relay_status=_relay_snapshot(adult_mode),
        active_section=active_section,
    )


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
    regions = _dashboard_regions(run=run, adult_mode=adult_mode, scan=scan, active_section=active_section)
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
    )


def toggle_adult_visibility(
    adult_mode: bool,
    active_section: str,
    upload: Any,
) -> tuple[str, str, str, str, str, str, str, dict[str, Any], dict[str, Any]]:
    scan = scan_file(_file_path(upload))
    regions = _dashboard_regions(adult_mode=adult_mode, scan=scan, active_section=active_section)
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
    )


def refresh_section(
    active_section: str,
    adult_mode: bool,
    upload: Any,
) -> tuple[str, str, str, str, str, dict[str, Any]]:
    scan = scan_file(_file_path(upload))
    regions = _dashboard_regions(adult_mode=adult_mode, scan=scan, active_section=active_section)
    return regions["command_rail"], regions["operations"], regions["inspector"], regions["artifacts"], regions["providers"], scan


initial_regions = _dashboard_regions(scan=scan_file(None))

with gr.Blocks(title="NEXUS Visual Weaver") as demo:
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

    run_btn.click(
        fn=run_weave,
        inputs=[prompt, reasoning_mode, video_preset, adult_mode, upload, section_nav],
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
        ],
        api_name="toggle_adult_catalog",
    )
    section_nav.change(
        fn=refresh_section,
        inputs=[section_nav, adult_mode, upload],
        outputs=[command_rail_html, operations_html, inspector_html, artifact_html, provider_html, scan_json],
        api_name=False,
    )
    demo.load(
        fn=lambda: (render_catalog_table(False), catalog_summary(False), scan_file(None)),
        outputs=[catalog_html, catalog_json, scan_json],
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
