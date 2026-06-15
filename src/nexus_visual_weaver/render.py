"""HTML rendering helpers for the Gradio command center."""

from __future__ import annotations

import os
import base64
from html import escape
from pathlib import Path

from .catalog import catalog_summary, parameter_budget
from .schema import GenerationRun


def badge(label: str, tone: str = "neutral") -> str:
    """
    Generate an HTML badge element with a tone-specific CSS class.
    
    Parameters:
        label (str): The badge text content.
        tone (str): A CSS class modifier for the badge style; defaults to "neutral".
    
    Returns:
        str: An HTML span element with the specified tone class.
    """
    return f'<span class="nw-badge nw-{tone}">{escape(label)}</span>'


def icon(name: str) -> str:
    paths = {
        "forge": '<path d="M12 2l2.2 5.1L19 9.1l-4.8 2L12 16l-2.2-4.9L5 9.1l4.8-2L12 2z"/><path d="M4 14l1.3 3L8 18.2l-2.7 1.1L4 22l-1.3-2.7L0 18.2 2.7 17 4 14z" transform="translate(2 -1)"/>',
        "wardrobe": '<path d="M9 3h6l1.5 3 3 1.5-2 4.5-2.5-1.1V21H9V10.9L6.5 12l-2-4.5 3-1.5L9 3z"/><path d="M9 3c.5 1.5 1.5 2.3 3 2.3S14.5 4.5 15 3"/>',
        "lore": '<path d="M5 4h10a4 4 0 014 4v12H8a3 3 0 00-3-3V4z"/><path d="M5 17a3 3 0 013-3h11"/><path d="M9 8h6M9 11h5"/>',
        "models": '<path d="M12 2l8 4.6v9.2L12 20.5l-8-4.7V6.6L12 2z"/><path d="M4 6.6l8 4.6 8-4.6M12 11.2v9.3"/>',
        "security": '<path d="M12 2l8 3v6c0 5-3.4 9.2-8 11-4.6-1.8-8-6-8-11V5l8-3z"/><path d="M8.5 12l2.2 2.2 4.8-5"/>',
        "runs": '<path d="M6 4h12v16H6z"/><path d="M9 8h6M9 12h6M9 16h3"/>',
        "zoom": '<circle cx="10" cy="10" r="5"/><path d="M14 14l5 5M10 7v6M7 10h6"/>',
        "frame": '<path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/>',
        "lock": '<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 018 0v3"/>',
        "dot": '<circle cx="12" cy="12" r="5"/>',
    }
    return f'<svg class="nw-icon" viewBox="0 0 24 24" aria-hidden="true">{paths.get(name, paths["dot"])}</svg>'


def _metric(label: str, value: str, tone: str = "neutral") -> str:
    """
    Render an HTML metric block with a label and value.
    
    Parameters:
        tone (str): The styling variant name (default: "neutral").
    
    Returns:
        str: HTML markup for the metric.
    """
    return f'<div class="nw-metric nw-metric-{tone}"><small>{escape(label)}</small><strong>{escape(value)}</strong></div>'


def _display_state(value: str) -> str:
    """Return user-facing state labels without changing machine state values."""
    normalized = str(value or "").replace("_", " ").strip().lower()
    labels = {
        "blocked": "Export Gate Active",
        "generated": "Generated",
        "missing secret": "Optional - Secret Required",
        "missing_secret": "Optional - Secret Required",
        "export_ready": "Export Ready",
        "configured": "CONFIGURED",
        "dry-run": "Dry Run",
        "dry run": "Dry Run",
        "success": "SUCCESS",
    }
    return labels.get(normalized, normalized.title() if normalized else "Pending")


def _gate_label(export_gate: str) -> str:
    normalized = str(export_gate or "pending").upper()
    if normalized == "BLOCKED":
        return "Export Blocked - Override Available"
    if normalized == "CLEAR":
        return "EXPORT CLEAR"
    return f"EXPORT {normalized}"


def _env_configured(*names: str) -> bool:
    """
    Determine whether any of the provided environment variables are set and truthy.
    
    Returns:
        True if any of the environment variables exists and is truthy, False otherwise.
    """
    return any(bool(os.environ.get(name)) for name in names)


def _provider_configured(base_url_name: str, *key_names: str) -> bool:
    """
    Determines if a provider is configured with both a base URL and authentication keys.
    
    Returns:
        True if the base URL environment variable is set and at least one of the
        provided key environment variables is set, False otherwise.
    """
    return bool(os.environ.get(base_url_name)) and _env_configured(*key_names)


_SCAN_REDACTION_TERMS = (
    "payload",
    "payload_excerpt",
    "hidden content",
    "recovered",
    "raw byte",
    "base64",
    "hex dump",
)


def _redact_scan_text(value: object) -> str:
    """
    Sanitizes scan text by redacting sensitive content and truncating excessively long values.
    
    Parameters:
        value (object): A scan detail to sanitize.
    
    Returns:
        str: A redaction notice if the text contains sensitive terms; the original text truncated
             to 177 characters plus "..." if it exceeds 180 characters; otherwise the original
             text converted to a string.
    """
    text = str(value)
    lowered = text.lower()
    if any(term in lowered for term in _SCAN_REDACTION_TERMS):
        return "Redacted scan detail; review the gated ST3GG evidence packet."
    if len(text) > 180:
        return text[:177] + "..."
    return text


def _space_runtime_status() -> dict[str, str]:
    """
    Determines the current runtime environment and active provider configuration.
    
    Returns:
        dict[str, str]: A dict with `space_id`, `hardware`, `bucket`, and `secrets` keys describing the deployment context and configured provider secrets.
    """
    space_id = os.environ.get("SPACE_ID") or os.environ.get("HF_SPACE_ID") or "local-preview"
    hardware = os.environ.get("SPACE_HARDWARE") or os.environ.get("NEXUS_SPACE_HARDWARE") or "ZeroGPU"
    bucket = "/data mounted" if os.path.isdir("/data") else "bucket optional"
    configured = []
    if _env_configured("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        configured.append("HF")
    if _provider_configured("MINICPM_BASE_URL", "MINICPM_API_KEY", "OPENBMB_API_KEY"):
        configured.append("MiniCPM")
    if _provider_configured("NEMOTRON_BASE_URL", "NEMOTRON_API_KEY", "NVIDIA_API_KEY"):
        configured.append("Nemotron")
    if _env_configured("FAL_KEY", "NETLIFY_AUTH_TOKEN", "OPENAI_API_KEY", "MODAL_TOKEN_ID"):
        configured.append("optional")
    secrets = "configured: " + ", ".join(configured) if configured else "no provider secrets"
    return {
        "space_id": space_id,
        "hardware": hardware,
        "bucket": bucket,
        "secrets": secrets,
    }


def _image_data_uri(path: str | None) -> str | None:
    """
    Create a data URI string from a file's contents, selecting MIME type by extension.
    
    Returns:
    	data_uri (str | None): A data URI string with base64-encoded file contents if the path exists and is readable; `None` otherwise. MIME type is determined by file extension (.png, .jpg/.jpeg, .webp; otherwise application/octet-stream).
    """
    if not path:
        return None
    target = Path(path)
    if not target.exists() or not target.is_file():
        return None
    suffix = target.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/webp" if suffix == ".webp" else "application/octet-stream"
    data = base64.b64encode(target.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def render_command_header() -> str:
    """
    Render the command header section of the dashboard.
    
    Returns:
        An HTML string containing the command header, description, and status badges.
    """
    return f"""
    <section class="nw-command-header">
      <div>
        <small>COMMAND INPUT</small>
        <strong>Raven Chronicle Active Weave</strong>
        <span>Prompt, reference scan, model route, and checkpoint controls stay in one sticky operator strip.</span>
      </div>
      <div class="nw-command-pills">
        {badge("SFW DEFAULT", "pass")}
        {badge("ST3GG ALWAYS ON", "cyan")}
        {badge("FLUX.2 9B PINNED", "accent")}
        {badge("4B SIDECAR", "cyan")}
        {badge("HUMAN CHECKPOINT", "warn")}
      </div>
    </section>
    """


def render_trust_strip(scan: dict | None = None, operator_state: dict | None = None) -> str:
    """
    Renders a trust model strip showing scan findings, export gate status, and safety checkpoint state.
    
    Returns:
        An HTML string for the trust strip section containing badge cards with redacted scan details.
    """
    scan = scan or {"status": "idle", "export_gate": "pending", "findings": [], "purification_actions": []}
    operator_state = operator_state or {}
    status = str(scan.get("status", "idle")).upper()
    export_gate = str(scan.get("export_gate", "pending")).upper()
    checkpoint = str(operator_state.get("checkpoint", "pending")).replace("_", " ").title()
    raw_findings = scan.get("findings")
    if raw_findings is None:
        default_finding = "No upload selected. Always-on scanner ready." if status == "IDLE" else "No findings."
        raw_findings = [default_finding]
    elif not raw_findings:
        raw_findings = ["No findings." if status != "IDLE" else "No upload selected. Always-on scanner ready."]
    findings = [_redact_scan_text(item) for item in raw_findings]
    actions = [_redact_scan_text(item) for item in (scan.get("purification_actions") or [
        "strip metadata before export",
        "truncate PNG after IEND when needed",
        "run LSB statistical review",
    ])]
    tone = _scan_status_tone(str(scan.get("status", "idle")))
    return f"""
    <section class="nw-trust-strip">
      <div class="nw-trust-primary">
        <small>TRUST MODEL</small>
        <strong>Generation is not export.</strong>
        <span>Every artifact must pass ST3GG scan, purification, and human checkpoint before release.</span>
      </div>
      <div class="nw-trust-card">{badge(f"ST3GG {status}", tone)}<span>{escape(str(findings[0]))}</span></div>
      <div class="nw-trust-card">{badge(_gate_label(export_gate), "pass" if export_gate == "CLEAR" else "warn" if export_gate == "BLOCKED" else "muted")}<span>{escape(str(actions[0]))}</span></div>
      <div class="nw-trust-card">{badge(f"CHECKPOINT {checkpoint.upper()}", "pass" if checkpoint == "Approved" else "muted")}<span>Adult Mode never bypasses safety, consent, provenance, or dataset gates.</span></div>
      <div class="nw-trust-card nw-trust-examples">{badge("FIXTURE EVIDENCE", "cyan")}<span>Clean PNG -> pass. PNG trailing bytes -> blocked.</span></div>
    </section>
    """


def render_topbar(
    adult_mode: bool = False,
    relay_status: dict | None = None,
    scan: dict | None = None,
    operator_state: dict | None = None,
) -> str:
    """
    Render the dashboard topbar with budget metrics, relay status, adult mode controls, and trust model information.
    
    Parameters:
        relay_status: Dictionary with relay rotation safety information.
        scan: Dictionary with scan status and findings.
        operator_state: Dictionary with operator checkpoint and provider state.
    
    Returns:
        HTML markup for the topbar and trust strip sections.
    """
    summary = catalog_summary(adult_mode)
    active = float(summary["active_b"])
    pct = max(0, min(100, int((active / 32.0) * 100)))
    adult_label = "ON - research partition" if adult_mode else "OFF"
    relay_status = relay_status or {}
    rotation_safe = bool(relay_status.get("rotation_safe", True))
    relay_label = "Rotation Safe" if rotation_safe else "Rotation Limited"
    relay_tone = "pass" if rotation_safe else "warn"
    space = _space_runtime_status()
    return f"""
    <div class="nw-topbar">
      <div class="nw-brand"><span>NEXUS</span><strong>Visual Weaver</strong></div>
      <div class="nw-topitem"><small>Project</small><strong>Raven Chronicle</strong><i></i></div>
      <div class="nw-topitem"><small>Active Preset</small><strong>Dark Couture v2.4</strong><i></i></div>
      <div class="nw-budget">
        <div><strong>32B Parameter Budget</strong><small>{active:.2f}B / 32B ({pct}%)</small></div>
        <div class="nw-meter"><i style="width:{pct}%"></i></div>
      </div>
      <div class="nw-status"><span class="nw-live-dot"></span><strong>HF Connected</strong><small>Hugging Face</small></div>
      <div class="nw-status nw-gmr"><small>HF / Modal / GMR</small>{badge(relay_label, relay_tone)}<small>Helper rotation only</small></div>
      <div class="nw-status nw-space"><small>{escape(space["space_id"])}</small><strong>{escape(space["hardware"])}</strong><small>{escape(space["bucket"])} / {escape(space["secrets"])}</small></div>
      <div class="nw-adult">
        <strong>Adult Mode {icon("lock")}</strong>
        <span class="nw-toggle {'is-on' if adult_mode else ''}"><i></i>{escape(adult_label)}</span>
      </div>
      <div class="nw-locked"><b>18+</b><span>Locked. Enable in Security with explicit justification.</span></div>
    </div>
    {render_trust_strip(scan, operator_state)}
    """


def render_left_rail(active_section: str = "Forge") -> str:
    items = [("Forge", "forge"), ("Wardrobe", "wardrobe"), ("Lore", "lore"), ("Models", "models"), ("Security", "security"), ("Runs", "runs")]
    rows = "".join(
        f'<div class="nw-rail-item {"active" if label == active_section else ""}">{icon(icon_name)}<span>{escape(label)}</span></div>'
        for label, icon_name in items
    )
    return f"""
    <nav class="nw-rail">
      <div class="nw-rail-main">{rows}</div>
      <div class="nw-rail-foot">
        <div>{icon("security")}<strong>Security Guardian</strong><span>Active</span></div>
        <div>{icon("lock")}<strong>ST3GG v2.3.1</strong><span>Always-on</span></div>
      </div>
    </nav>
    """


def render_command_rail(active_section: str = "Forge") -> str:
    """
    Render a contextual command rail for the selected section.
    
    Returns:
    	str: An HTML string with the command rail displaying the section's title, description, and selection badge.
    """
    section = escape(active_section)
    hints = {
        "Forge": ("Active Weave", "Prompt, judge, locate, generate, checkpoint."),
        "Wardrobe": ("Outfit Slots", "Materials, footwear, locks, reference regions."),
        "Lore": ("Video Continuity", "Identity, garment meaning, scene motion."),
        "Models": ("Relay Stack", "Pinned core plus quota-aware helper rotation."),
        "Security": ("ST3GG Gate", "Scan, purify, provenance, export decision."),
        "Runs": ("Run Ledger", "Checkpointed dry-runs and handoff packets."),
    }
    title, body = hints.get(active_section, hints["Forge"])
    return f"""
    <div class="nw-native-rail">
      <strong>{escape(title)}</strong>
      <span>{escape(body)}</span>
      {badge(f"Selected: {section}", "muted")}
    </div>
    """


def render_workflow(run: GenerationRun | None = None, operator_state: dict | None = None) -> str:
    """
    Render an SVG workflow diagram and console showing the generation pipeline.
    
    The diagram visualizes a multi-stage workflow (seed prompt, refine, judge, locate, generate, video, checkpoint)
    with nodes, edges, and status indicators. Node content and labels reflect the provided run and operator context.
    
    Parameters:
    	run: GenerationRun object providing run-specific values for trust score, checkpoint ID, model labels,
    	     video preset, and required actions. Defaults to mock values if None.
    	operator_state: Dict containing operator context including checkpoint status, provider state, recommendation,
    	                 and message. Defaults to an empty dict.
    
    Returns:
    	str: HTML section containing SVG workflow graph, legend badges, and console cards with checkpoint,
    	     action, model lane, and signal information.
    """
    operator_state = operator_state or {}
    score = run.checkpoint.trust_score if run else 0.82
    checkpoint_id = run.checkpoint.checkpoint_id if run else "nw-dry-run"
    checkpoint_status = str(operator_state.get("checkpoint", "pending_review" if run else "pending"))
    provider_state = str(operator_state.get("provider_state", "dry-run" if run else "idle"))
    recommendation = operator_state.get("message") or (run.checkpoint.recommendation.replace("_", " ").title() if run else "Awaiting Run")
    required_actions = run.checkpoint.required_actions if run else ["Review candidate thumbnails before promotion"]
    action_label = required_actions[0] if required_actions else "No action pending"
    if checkpoint_status == "approved":
        action_label = "Checkpoint approved; export packet may be prepared after ST3GG gate."
    elif provider_state == "stopped":
        action_label = "Provider handoff stopped; dry-run evidence remains available."
    model_label = _short_repo(run.model_stack[0].repo_id) if run and run.model_stack else "FLUX.2"
    locate_label = run.inspection.locate_model.split("/")[-1] if run else "LocateAnything-3B"
    nodes = {
        "seed": (35, 52, 190, 210, "Seed Prompt", ["Rogue archivist moving", "through rain-slick neon", "city, couture layers."], "Text-to-Image (FLUX.2)", "complete", "red"),
        "refine": (275, 52, 185, 160, "Refine", ["Prompt Refiner", "Style Harmonizer", "Negative Purge"], "Qwen2.5-7B", "complete", "violet"),
        "judge": (540, 52, 185, 160, "Judge", ["Aesthetic Scorer", "ST3GG Policy Filter", f"Score {score:.2f}"], "MiniCPM / Nemotron", "complete", "blue"),
        "locate": (785, 52, 185, 160, "Locate", ["Reference Locator", "Pose & Composition", "IP-Adapter"], "Refs 3/5", "complete", "cyan"),
        "generate": (275, 280, 235, 210, "Generate", ["Image / Video Generation", "FLUX.2 9B + adapter stack", "4B sidecar fallback"], "Steps 4  CFG 1.0", "ready", "green"),
        "video": (590, 280, 235, 210, "Video Path", ["Image to Video", "Frame interpolation", run.video.preset if run else "Wan2.2 / LTX swap"], "Duration 5.6s  24fps", "ready", "blue"),
        "checkpoint": (880, 285, 185, 185, "Human Checkpoint", ["Human review required", "Verify intent, vibe,", "and output before final."], "Review Now", "paused", "amber"),
    }
    edges = [
        ("seed", "refine"), ("refine", "judge"), ("judge", "locate"), ("locate", "video"),
        ("refine", "generate"), ("generate", "video"), ("video", "checkpoint"), ("judge", "checkpoint"),
    ]
    lines = []
    for source, target in edges:
        x1, y1, w1, h1, *_ = nodes[source]
        x2, y2, w2, h2, *_ = nodes[target]
        y_offset = 76 if source in {"seed", "refine", "judge", "locate"} else 96
        lines.append(
            f'<path d="M{x1 + w1} {y1 + y_offset} C{x1 + w1 + 55} {y1 + y_offset}, {x2 - 55} {y2 + 76}, {x2} {y2 + 76}" />'
        )
    cards = []
    for node_id, (x, y, width, height, title, body, footer, status, tone) in nodes.items():
        body_lines = "".join(f'<text x="{x + 16}" y="{y + 74 + idx * 22}" class="nw-node-line">{escape(line)}</text>' for idx, line in enumerate(body))
        thumb_strip = ""
        if node_id in {"generate", "video"}:
            thumbs = []
            for idx in range(4):
                tx = x + 16 + idx * 47
                thumbs.append(
                    f'<rect class="nw-thumb nw-thumb-{idx}" x="{tx}" y="{y + 112}" rx="4" width="39" height="52"></rect>'
                )
            thumb_strip = "".join(thumbs)
        cards.append(
            f"""
            <g class="nw-node nw-node-{status} nw-node-{tone}">
              <rect x="{x}" y="{y}" rx="9" width="{width}" height="{height}"></rect>
              <text x="{x + 16}" y="{y + 31}" class="nw-node-title">{escape(title)}</text>
              {body_lines}
              {thumb_strip}
              <line x1="{x + 16}" y1="{y + height - 48}" x2="{x + width - 16}" y2="{y + height - 48}" class="nw-node-sep" />
              <text x="{x + 16}" y="{y + height - 20}" class="nw-node-footer">{escape(footer)}</text>
              <circle cx="{x + width - 20}" cy="{y + height - 20}" r="5" class="nw-node-ok"></circle>
            </g>
            """
        )
    generation = operator_state.get("generation") or {}
    generated = isinstance(generation, dict) and generation.get("status") == "success"
    output_summary = "Real FLUX.2 Klein 9B artifact generated" if generated else "Awaiting generated artifact"
    checkpoint_summary = _display_state(checkpoint_status)
    export_summary = _display_state(str(operator_state.get("export", provider_state)))
    next_summary = "Add override reason or complete review" if provider_state == "blocked" else action_label
    return f"""
    <section class="nw-panel nw-canvas">
      <div class="nw-panel-head nw-canvas-head">
        <div><strong>Active Weave</strong><small><span class="nw-live-dot"></span> Live / Weave ID: 4f7c9e2b</small></div>
        <div class="nw-tools nw-static-tools"><span>Layout Auto</span><span>{icon("zoom")}</span><span>{icon("frame")}</span></div>
      </div>
      <div class="nw-run-summary">
        <strong>Current Run Summary</strong>
        <span><b>Output</b>{escape(output_summary)}</span>
        <span><b>Security</b>ST3GG review active</span>
        <span><b>Checkpoint</b>{escape(checkpoint_summary)}</span>
        <span><b>Export</b>{escape(export_summary)}</span>
        <span><b>Next</b>{escape(next_summary)}</span>
      </div>
      <svg class="nw-graph" viewBox="0 0 1110 530" role="img" aria-label="NEXUS workflow graph">
        <defs>
          <pattern id="nw-grid" width="12" height="12" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="0.8" fill="#2d3944" />
          </pattern>
          <linearGradient id="nw-node-shine" x1="0" x2="1"><stop offset="0" stop-color="rgba(255,255,255,.07)" /><stop offset="1" stop-color="rgba(255,255,255,0)" /></linearGradient>
        </defs>
        <rect width="1110" height="530" fill="url(#nw-grid)"></rect>
        <g class="nw-edges">{"".join(lines)}</g>
        {"".join(cards)}
      </svg>
      <div class="nw-legend">
        {badge("Text Flow", "accent")} {badge("Refine Loop", "violet")} {badge("Policy Gate", "blue")} {badge("Media Flow", "cyan")} {badge("Human Gate", "warn")} {badge(_display_state(provider_state), "pass" if provider_state == "exported" else "warn" if provider_state in {"blocked", "stopped"} else "muted")}
      </div>
      <div class="nw-weave-console">
        <div class="nw-console-card nw-console-primary">
          <small>Selected Node</small>
          <strong>Human Checkpoint</strong>
          <span>{escape(str(recommendation))} / {escape(checkpoint_id)}</span>
        </div>
        <div class="nw-console-card">
          <small>Next Operator Action</small>
          <strong>{escape(action_label)}</strong>
          <span>Checkpoint blocks video promotion until reviewed.</span>
        </div>
        <div class="nw-console-card">
          <small>Pinned Model Lanes</small>
          <strong>{escape(model_label)} + {escape(locate_label)} + ST3GG</strong>
          <span>Core lanes stay fixed; helper lanes may rotate.</span>
        </div>
        <div class="nw-console-card">
          <small>Hackathon Signal</small>
          <strong>Workflow, governance, visual creation</strong>
          <span>Judge view keeps product purpose visible without a landing page.</span>
        </div>
      </div>
    </section>
    """


def render_artifact_lane(run: GenerationRun | None = None, scan: dict | None = None, operator_state: dict | None = None) -> str:
    """
    Render an artifact preview panel with generated output and status cards.
    
    Displays the current artifact output (if available from a provider call), preview metadata 
    about checkpoint and export status, and a grid of artifact cards showing progress through 
    generation stages. Supports both dry-run and live provider output scenarios.
    
    Parameters:
        run (GenerationRun | None): Generation run with output image path, refined prompt, and continuity data. 
            If None, shows dry-run placeholder content.
        scan (dict | None): Security scan state with status and export gate information.
            Defaults to {"status": "idle", "export_gate": "pending"}.
        operator_state (dict | None): Operator context including checkpoint status, provider state, and generated output.
            Defaults to {}.
    
    Returns:
        str: HTML markup for the artifact preview section.
    """
    scan = scan or {"status": "idle", "export_gate": "pending"}
    operator_state = operator_state or {}
    prompt_label = "Prompt proof"
    outfit_label = "Outfit map"
    locate_label = "Grounding overlay"
    video_label = run.video.preset if run else "Video path"
    active_prompt = run.refined_prompt.refined[:150] if run else "Awaiting first weave. Real output and export evidence appear here after generation."
    checkpoint = operator_state.get("checkpoint", getattr(run.checkpoint, "recommendation", "pending") if run else "pending")
    provider_state = str(operator_state.get("provider_state", "dry-run" if run else "idle"))
    generation = operator_state.get("generation") or {}
    generated_uri = _image_data_uri(generation.get("output_path")) if isinstance(generation, dict) else None
    generated_status = str(generation.get("status", "")) if isinstance(generation, dict) else ""
    generated_message = str(generation.get("message", "")) if isinstance(generation, dict) else ""
    preview_mode = {
        "idle": "Idle",
        "dry-run": "Dry Run",
        "checkpointed": "Checkpointed",
        "export_ready": "Export Ready",
        "exported": "Exported",
        "blocked": "Export Gate Active",
        "stopped": "Stopped",
    }.get(provider_state, provider_state.replace("_", " ").title())
    demo_seed = (run.checkpoint.checkpoint_id[-4:] if run else "0000").upper()
    artifacts = [
        (prompt_label, "Taste-refined brief", "dry-run", "material-0", "01"),
        (outfit_label, "Wardrobe slots and locks", "checkpointed", "material-1", "02"),
        (locate_label, "LocateAnything region plan", "configured", "material-4", "03"),
        (video_label, "Checkpointed storyboard", "deferred" if scan.get("export_gate") == "blocked" or provider_state == "blocked" else "ready", "story-2", "04"),
    ]
    cards = "".join(
        f"""
        <div class="nw-artifact-card">
          <small>{escape(index)}</small>
          <i class="nw-{texture}"></i>
          <strong>{escape(title)}</strong>
          <span>{escape(body)}</span>
          {badge("Gated" if status == "deferred" else status.upper(), "warn" if status in {"blocked", "deferred"} else "muted")}
        </div>
        """
        for title, body, status, texture, index in artifacts
    )
    export_gate = str(scan.get("export_gate", "pending")).upper()
    continuity = ", ".join(run.video.continuity_locks[:4]) if run else "outerwear, footwear, jewelry, NEXUS sigils"
    return f"""
    <section class="nw-panel nw-artifacts">
      <div class="nw-panel-head">
        <div><strong>Artifact Preview Lane</strong><small>Real output and export evidence appear here</small></div>
        {badge(_gate_label(export_gate), "warn" if export_gate == "BLOCKED" else "pass" if export_gate == "CLEAR" else "muted")}
      </div>
      <div class="nw-preview-stage">
        <div class="nw-preview-frame">
          {'<img class="nw-preview-real-image" src="' + generated_uri + '" alt="Generated FLUX artifact" />' if generated_uri else '<i class="nw-preview-image"></i>'}
          <div class="nw-preview-caption">
            <small>PRIMARY OUTPUT STAGE / {escape(generated_status.upper() or "JUDGE-SAFE DEMO OUTPUT")} / SEED {escape(demo_seed)}</small>
            <strong>{'Real FLUX.2 Klein artifact' if generated_uri else 'Deterministic Raven Chronicle proof frame'}</strong>
            <span>{escape(generated_message or active_prompt)}</span>
          </div>
        </div>
        <div class="nw-preview-meta">
          <div><small>checkpoint</small><strong>{escape(str(checkpoint).replace("_", " ").title())}</strong></div>
          <div><small>export gate</small><strong>{escape(export_gate)}</strong></div>
          <div><small>preview mode</small><strong>{escape(preview_mode)}</strong></div>
        </div>
      </div>
      <div class="nw-preview-ribbon">
        <span>{icon("security")} ST3GG before export</span>
        <span>{icon("wardrobe")} continuity: {escape(continuity)}</span>
        <span>{icon("models")} provider call remains checkpointed; state: dry-run / configured / gated / failed / exported; current: {escape(_display_state(provider_state))}</span>
      </div>
      <div class="nw-artifact-grid">{cards}</div>
    </section>
    """


def render_operations_panel(
    active_section: str = "Forge",
    run: GenerationRun | None = None,
    scan: dict | None = None,
    relay_status: dict | None = None,
    *,
    adult_mode: bool = False,
    operator_state: dict | None = None,
) -> str:
    """
    Render an operations panel with section-specific operation cards.
    
    Generates an HTML section containing three operation cards tailored to the selected section,
    with content drawn from run state, scan results, relay decisions, and operator context.
    Invalid section names default to "Forge".
    
    Parameters:
    	active_section (str): The section name determining which operation cards to display.
    		Valid sections are "Forge", "Wardrobe", "Lore", "Models", "Security", and "Runs".
    	adult_mode (bool): If True, scope label is "Private research scope"; otherwise "Public demo scope".
    	operator_state (dict | None): Operator context dict with "provider_state" and "message" keys.
    
    Returns:
    	str: HTML string representing the operations panel section.
    """
    scan = scan or {"status": "idle", "export_gate": "pending", "findings": []}
    relay_status = relay_status or {}
    operator_state = operator_state or {}
    section = active_section if active_section in {"Forge", "Wardrobe", "Lore", "Models", "Security", "Runs"} else "Forge"
    checkpoint = getattr(run, "checkpoint", None) if run else None
    outfit = getattr(run, "outfit", None) if run else None
    lore = getattr(run, "lore", None) if run else None
    run_id = getattr(checkpoint, "checkpoint_id", "not-started")
    outfit_count = len(getattr(outfit, "slots", []) or [])
    lore_count = len(getattr(lore, "beats", []) or [])
    scan_status = str(scan.get("status", "idle")).upper()
    export_gate = str(scan.get("export_gate", "pending")).upper()
    provider_state = str(operator_state.get("provider_state", "idle")).replace("_", " ").upper()
    operator_message = str(operator_state.get("message", "No operator action yet."))
    decisions = relay_status.get("decisions", [])
    first_decision = decisions[0] if decisions else {}
    first_primary = (first_decision.get("primary") or {}) if first_decision else {}
    adult_scope = "Private research scope" if adult_mode else "Public demo scope"
    panels = {
        "Forge": [
            ("Prompt contract", "Taste-refined prompt, material locks, negative purge, and checkpoint requirements."),
            ("Active run", f"{run_id} / checkpoint remains human-reviewed before video promotion."),
            ("Provider posture", f"{provider_state}: {operator_message}"),
        ],
        "Wardrobe": [
            ("Slot coverage", f"{outfit_count or 9} garment/accessory regions tracked with locks and edit priority."),
            ("Footwear focus", "Platform boots, stilettos, high-heel boots, hardware, and silhouette constraints stay first-class."),
            ("Locate map", "Reference regions feed preflight and post-generation outfit verification."),
        ],
        "Lore": [
            ("Beat budget", f"{lore_count or 6} compact beats: identity, garment meaning, world context, emotion, motion."),
            ("Video checkpoint", "Video presets remain handoff plans until human approval."),
            ("Continuity locks", "Lore-to-video keeps garment meaning and motion cue visible without tab sprawl."),
        ],
        "Models": [
            ("Primary helper", _short_repo(str(first_primary.get("repo_id", "pending")))),
            ("Rotation mode", "Pinned core stays fixed; helper lanes rotate by license, budget, quota, and health."),
            ("Scope", adult_scope),
        ],
        "Security": [
            ("ST3GG state", f"{scan_status} / export {export_gate}"),
            (
                "Findings",
                "; ".join(_redact_scan_text(item) for item in (scan.get("findings") or [])[:2])
                or ("No findings." if scan_status != "IDLE" else "No upload selected."),
            ),
            ("Public export", "Consent, provenance, metadata, age, dataset, and payload gates stay active."),
        ],
        "Runs": [
            ("Current checkpoint", run_id),
            ("Ledger mode", f"Operator state: {provider_state}. Run JSON, catalog summary, and ST3GG evidence remain in the evidence accordion."),
            ("Rollback path", "Feature branches and draft PRs carry implementation checkpoints."),
        ],
    }
    rows = "".join(
        f"""
        <div class="nw-operation-card">
          <small>{escape(title)}</small>
          <strong>{escape(body)}</strong>
          <i></i>
        </div>
        """
        for title, body in panels[section]
    )
    return f"""
    <section class="nw-panel nw-operations">
      <div class="nw-panel-head">
        <div><strong>{escape(section)} Operations</strong><small>Section-aware control surface for the selected command rail lane</small></div>
        {badge(f"{escape(section).upper()} ACTIVE", "cyan")}
      </div>
      <div class="nw-operation-grid">{rows}</div>
    </section>
    """


def _short_repo(repo_id: str) -> str:
    """
    Extract the repository name from a repository identifier.
    
    Returns the last segment after splitting on forward slashes.
    
    Returns:
        str: The repository name
    """
    return repo_id.split("/")[-1]


def _render_relay_panel(relay_status: dict | None = None) -> str:
    """
    Render an HTML panel summarizing model relay decisions and pinned lanes.
    
    Returns:
    	str: An HTML string containing the GMR panel with pinned core lanes, up to two decisions, and dedup metrics.
    """
    relay_status = relay_status or {}
    pinned = relay_status.get("pinned", {})
    decisions = relay_status.get("decisions", [])
    pinned_labels = []
    for lane in ["image_generation", "grounding", "security"]:
        record = pinned.get(lane)
        if record:
            pinned_labels.append(_short_repo(record["repo_id"]))
    pinned_rows = [
        f"""
        <li>
          <span>pinned core</span>
          <strong>{escape(" / ".join(pinned_labels[:3]) or "pending")}</strong>
          <em>image, grounding, and security never rotate</em>
        </li>
        """
    ]
    decision_rows = []
    for decision in decisions[:2]:
        primary = decision.get("primary") or {}
        fallbacks = decision.get("fallbacks") or []
        fallback_label = ", ".join(_short_repo(item["repo_id"]) for item in fallbacks[:2]) or "none"
        decision_rows.append(
            f"""
            <li>
              <span>{escape(decision["lane"].replace("_", " "))}</span>
              <strong>{escape(_short_repo(primary.get("repo_id", "blocked")))}</strong>
              <em>{escape(decision["strategy"])} / fallback: {escape(fallback_label)}</em>
            </li>
            """
        )
    rows = "".join(pinned_rows + decision_rows)
    if not rows:
        rows = "<li><span>GMR</span><strong>snapshot pending</strong><em>relay idle</em></li>"
    dedup_hits = relay_status.get("dedup_hits", 0)
    return f"""
    <h3>GMR ModelRelay</h3>
    <ul class="nw-relay">{rows}</ul>
    <div class="nw-relay-foot">
      {badge("FLUX.2 9B pinned", "pass")} {badge("4B sidecar", "cyan")} {badge("LocateAnything pinned", "pass")} {badge(f"dedup hits {dedup_hits}", "muted")}
    </div>
    """


def render_provider_cards(relay_status: dict | None = None, adult_mode: bool = False) -> str:
    """
    Generates an HTML panel displaying provider cards with operational status and licensing information.
    
    Constructs cards for each relay-decided provider showing the lane, repository, provider name, license gate status, and health meter. Includes optional provider cards for off-by-default gateways. The panel header shows the current operational mode (private research or public demo).
    
    Parameters:
        relay_status (dict | None): Relay status containing provider decisions with quota impact and license gate data. If None, defaults to empty dict.
        adult_mode (bool): If True, displays "PRIVATE RESEARCH" mode label; otherwise displays "PUBLIC DEMO SAFE".
    
    Returns:
        str: HTML section markup for the provider cards panel.
    """
    relay_status = relay_status or {}
    decisions = relay_status.get("decisions", [])
    optional_statuses = {
        "openbmb": "configured" if _provider_configured("MINICPM_BASE_URL", "MINICPM_API_KEY", "OPENBMB_API_KEY") else "missing secret",
        "nvidia": "configured" if _provider_configured("NEMOTRON_BASE_URL", "NEMOTRON_API_KEY", "NVIDIA_API_KEY") else "missing secret",
        "fal": "configured" if _env_configured("FAL_KEY") else "deferred",
        "netlify": "configured" if _env_configured("NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID", "OPENAI_BASE_URL") else "deferred",
        "cloudflare": "configured" if _env_configured("CLOUDFLARE_API_TOKEN", "CF_ACCOUNT_ID") else "deferred",
    }
    cards = []
    for decision in decisions[:5]:
        primary = decision.get("primary") or {}
        quota = decision.get("quota_impact") or {}
        provider = primary.get("provider", "blocked")
        repo = _short_repo(primary.get("repo_id", "blocked"))
        lane = decision.get("lane", "helper").replace("_", " ")
        status = quota.get("status", "blocked")
        provider_state = "dry-run" if status == "ready" else "blocked" if status == "blocked" else "limited"
        if provider in optional_statuses:
            provider_state = optional_statuses[provider]
        tone = "pass" if provider_state == "configured" else "warn" if provider_state in {"limited", "failed"} else "muted"
        gate = primary.get("license_gate", "unknown")
        cards.append(
            f"""
            <div class="nw-provider-card">
              <small>{escape(lane)}</small>
              <strong>{escape(repo)}</strong>
              <span>{escape(str(provider))} / {escape(str(gate))}</span>
              <i class="nw-provider-meter" style="--health:{'86' if provider_state in {'configured', 'dry-run'} else '52' if provider_state == 'limited' else '22'}"></i>
              <div>{badge(_display_state(provider_state), tone)}{badge("CHECKPOINTED", "muted")}</div>
            </div>
            """
        )
    if not cards:
        cards.append('<div class="nw-provider-card"><small>providers</small><strong>snapshot pending</strong><span>relay idle</span><div>{}</div></div>'.format(badge("DRY-RUN", "muted")))
    for provider, state in optional_statuses.items():
        cards.append(
            f"""
            <div class="nw-provider-card nw-provider-optional">
              <small>optional gateway</small>
              <strong>{escape(provider.title())}</strong>
              <span>optional lane / secrets required</span>
              <i class="nw-provider-meter" style="--health:{'74' if state == 'configured' else '18'}"></i>
              <div>{badge(_display_state(state), "pass" if state == "configured" else "muted")}{badge("SPONSOR LANE" if provider in {"openbmb", "nvidia", "hf_nvidia"} else "DEFERRED", "muted")}</div>
            </div>
            """
        )
    mode_label = "private research" if adult_mode else "public demo safe"
    return f"""
    <section class="nw-panel nw-providers">
      <div class="nw-panel-head">
        <div><strong>Optional Provider Lanes</strong><small>Visible capability cards; success is claimed only after configured calls</small></div>
        {badge(mode_label.upper(), "warn" if adult_mode else "pass")}
      </div>
      <div class="nw-provider-grid">{"".join(cards)}</div>
    </section>
    """


def _scan_status_tone(scan_status: str) -> str:
    """
    Map a scan status to a display tone.
    
    Returns:
        str: "pass" if status is "pass", "warn" if status is "review" or "error", "muted" otherwise.
    """
    if scan_status == "pass":
        return "pass"
    if scan_status in {"review", "error"}:
        return "warn"
    return "muted"


def render_inspector(
    run: GenerationRun | None = None,
    scan: dict | None = None,
    relay_status: dict | None = None,
    operator_state: dict | None = None,
) -> str:
    """
    Render an inspector sidebar with taste profile, material checklist, model stack, sponsor evidence, and ST3GG scan details.
    
    Returns:
        str: HTML markup for the inspector panel.
    """
    if run:
        checks = [
            ("Patent Leather", True),
            ("Faux Fur", any(slot.material == "faux_fur" for slot in run.outfit.slots)),
            ("Lace / Mesh", any("lace" in slot.material for slot in run.outfit.slots)),
            ("Crimson Hardware", any(slot.material == "crimson_hardware" for slot in run.outfit.slots)),
            ("Platform Boots", any(slot.name == "footwear" for slot in run.outfit.slots)),
            ("Layered Garments", True),
        ]
        stack_label = " / ".join(_short_repo(model.repo_id) for model in run.model_stack[:3])
        model_rows = f"<li><span>active stack</span><strong>{escape(stack_label)}</strong></li>"
        score = int(run.checkpoint.trust_score * 100)
        scan_status = (scan or {}).get("status", "pass")
    else:
        checks = [(label, True) for label in ["Patent Leather", "Faux Fur", "Lace / Mesh", "Crimson Hardware", "Platform Boots", "Layered Garments"]]
        model_rows = "<li><span>active stack</span><strong>FLUX.2 9B / MiniCPM / LocateAnything</strong></li>"
        score = 86
        scan_status = (scan or {}).get("status", "pass")
    checks_html = "".join(f'<li><span>{"✓" if ok else "!"}</span>{escape(label)}</li>' for label, ok in checks)
    relay = _render_relay_panel(relay_status)
    scan = scan or {"status": scan_status, "findings": [], "purification_actions": [], "export_gate": "pending"}
    operator_state = operator_state or {}
    minicpm = operator_state.get("minicpm_judge") or {}
    nemotron = operator_state.get("nemotron_evidence") or {}
    sponsor_rows = "".join(
        f"<li><span>{escape(label)}</span><strong>{escape(_display_state(str(result.get('status', 'pending'))))}</strong><em>{escape(str(result.get('repo_id', repo)))}</em></li>"
        for label, repo, result in [
            ("OpenBMB MiniCPM", "openbmb/MiniCPM-V-4.6", minicpm),
            ("NVIDIA Nemotron", "nvidia/NVIDIA-Nemotron-Parse-v1.2", nemotron),
        ]
    )
    findings = [_redact_scan_text(item) for item in (scan.get("findings") or [])]
    actions = [_redact_scan_text(item) for item in (scan.get("purification_actions") or ["metadata strip ready", "IEND truncation ready", "LSB review ready"])]
    finding_rows = "".join(f"<li>{escape(item)}</li>" for item in findings[:4]) or "<li>No upload selected. Scanner ready.</li>"
    action_rows = "".join(f"<li>{escape(item)}</li>" for item in actions[:4])
    export_gate = str(scan.get("export_gate", "pending")).upper()
    return f"""
    <aside class="nw-panel nw-inspector">
      <div class="nw-panel-head"><strong>Inspector</strong>{badge("Selected: Judge", "muted")}</div>
      <h3>Taste Profile</h3>
      <div class="nw-rings">
        <div style="--v:{score};--ring:#f59e42"><b>{score}</b><small>Composition</small></div>
        <div style="--v:82;--ring:#fb6b5f"><b>82</b><small>Color</small></div>
        <div style="--v:79;--ring:#e86158"><b>79</b><small>Mood</small></div>
        <div style="--v:91;--ring:#ec4899"><b>91</b><small>Cohesion</small></div>
      </div>
      <h3>Material Checklist</h3>
      <ul class="nw-checks">{checks_html}</ul>
      <h3>Model Stack</h3>
      <ul class="nw-models">{model_rows}</ul>
      <h3>Sponsor Evidence</h3>
      <ul class="nw-relay">{sponsor_rows}</ul>
      <h3>ST3GG Scan</h3>
      <div class="nw-scan">
        <div>{badge(str(scan_status).upper(), _scan_status_tone(str(scan_status)))}<span>Always-on defensive review</span></div>
        <i style="width:78%"></i>
        <dl><dt>Policy</dt><dd>NEXUS Safe Policy v2.1</dd><dt>Purify</dt><dd>{escape(", ".join(str(item) for item in actions[:2]))}</dd><dt>Export</dt><dd>{escape(export_gate)}</dd></dl>
        <ul class="nw-scan-list">{finding_rows}</ul>
        <ul class="nw-scan-list nw-scan-actions">{action_rows}</ul>
      </div>
      {relay}
    </aside>
    """


def render_drawer(run: GenerationRun | None = None) -> str:
    """
    Renders the bottom drawer panel with outfit wardrobe and story beats.
    
    Returns:
        str: HTML markup for the bottom drawer section.
    """
    if run:
        slots = run.outfit.slots
        beats = run.lore.beats
    else:
        slots = []
        beats = []
    slot_cards = "".join(
        f"""
        <div class="nw-swatch {'is-locked' if slot.locked else ''}">
          <i class="nw-material-{idx % 6}"></i><strong>{escape(slot.name.replace("_", " ").title())}</strong>
          <small>{escape(slot.material.replace("_", " "))}</small>
          <span>{'locked' if slot.locked else 'editable'} / p{slot.edit_priority}</span>
        </div>
        """
        for idx, slot in enumerate(slots[:8])
    )
    if not slot_cards:
        slot_cards = "".join(
            f'<div class="nw-swatch"><i class="nw-material-{idx % 6}"></i><strong>{label}</strong><small>{mat}</small><span>editable / p{5 - idx // 2}</span></div>'
            for idx, (label, mat) in enumerate([
                ("Patent Leather", "jet black"), ("Faux Fur", "ash gray"), ("Lace Mesh", "noir"),
                ("Crimson Hardware", "polished"), ("Platform Boots", "matte black"), ("Long Coat", "wool blend"),
            ])
        )
    beat_cards = "".join(
        f'<div class="nw-beat"><i class="nw-story-{idx % 6}"></i><strong>{escape(beat["id"])} {escape(beat["title"])}</strong><small>{escape(beat["cue"][:80])}</small><span class="nw-mini-chip">checkpointed</span></div>'
        for idx, beat in enumerate(beats[:6])
    )
    if not beat_cards:
        beat_cards = "".join(f'<div class="nw-beat"><i class="nw-story-{i % 6}"></i><strong>0{i} Beat</strong><small>Scene continuity cue</small><span class="nw-mini-chip">checkpointed</span></div>' for i in range(1, 7))
    return f"""
    <section class="nw-bottom">
      <div class="nw-panel nw-wardrobe">
        <div class="nw-panel-head"><div><strong>Outfit Wardrobe</strong><small>Couture slots, locks, LocateAnything regions, and edit priority</small></div><span class="nw-chip">All Categories</span></div>
        <div class="nw-filter-row"><span>All</span><span>Patent</span><span>Lace</span><span>Hardware</span><span>Boots / heels</span><span>Outerwear</span><span>Props</span></div>
        <div class="nw-swatches">{slot_cards}</div>
      </div>
      <div class="nw-panel nw-lore">
        <div class="nw-panel-head"><div><strong>Lore-to-Video Timeline</strong><small>Identity, garment meaning, motion cue, and video checkpoint path</small></div><div class="nw-tools nw-static-tools"><span>6 Beats</span><span>24 FPS</span></div></div>
        <div class="nw-beats">{beat_cards}</div>
      </div>
    </section>
    """


def render_status_bar(operator_state: dict | None = None) -> str:
    space = _space_runtime_status()
    operator_state = operator_state or {}
    raw_provider_state = str(operator_state.get("provider_state", "idle"))
    provider_state = _display_state(raw_provider_state)
    stop_class = (
        "nw-stop-idle"
        if provider_state == "Idle"
        else "nw-stop-pass"
        if raw_provider_state in {"generated", "exported", "export_ready", "checkpointed"}
        else "nw-stop-active"
    )
    return f"""
    <footer class="nw-statusbar">
      {_metric("Runs", "112")}
      {_metric("Queue", "2")}
      {_metric("GPU", "46%", "bar")}
      {_metric("VRAM", "18.2 / 40 GB", "bar")}
      {_metric("Temp", "62 C")}
      {_metric("HF Space", space["hardware"])}
      <div class="nw-autosave"><span class="nw-live-dot"></span><strong>Auto-save</strong><small>On</small></div>
      <div class="nw-stop {stop_class}">{escape(provider_state)}</div>
    </footer>
    """


def render_catalog_table(adult_mode: bool = False) -> str:
    from .catalog import filter_catalog

    models, adapters = filter_catalog(adult_mode)
    model_rows = "".join(
        f"<tr><td>{escape(model.repo_id)}</td><td>{escape(model.role)}</td><td>{model.params_b:.2f}B</td><td>{escape(model.license)}</td><td>{'18+' if model.adult_only else 'General'}</td></tr>"
        for model in models
    )
    adapter_rows = "".join(
        f"<tr><td>{escape(adapter.repo_id)}</td><td>{escape(adapter.adapter_for)}</td><td>{escape(adapter.task)}</td><td>{'18+' if adapter.adult_only else 'General'}</td></tr>"
        for adapter in adapters
    )
    return f"""
    <div class="nw-catalog">
      <h3>HF Model Catalog</h3>
      <table><thead><tr><th>Repo</th><th>Role</th><th>Params</th><th>License</th><th>Scope</th></tr></thead><tbody>{model_rows}</tbody></table>
      <h3>LoRA / Adapter Shelf</h3>
      <table><thead><tr><th>Repo</th><th>Adapter For</th><th>Task</th><th>Scope</th></tr></thead><tbody>{adapter_rows}</tbody></table>
    </div>
    """


def render_dashboard(
    run: GenerationRun | None = None,
    adult_mode: bool = False,
    scan: dict | None = None,
    relay_status: dict | None = None,
    active_section: str = "Forge",
    operator_state: dict | None = None,
) -> str:
    """
    Render the complete Gradio command center dashboard.
    
    Returns:
        str: The full HTML dashboard markup.
    """
    regions = render_dashboard_regions(run, adult_mode, scan, relay_status, active_section, operator_state)
    return f"""
    <div class="nw-app">
      {regions["topbar"]}
      <div class="nw-shell">
        {regions["rail"]}
        <div class="nw-main-stack">
          {regions["workflow"]}
          {regions["operations"]}
          {regions["artifacts"]}
        </div>
        <div class="nw-side-stack">
          {regions["inspector"]}
          {regions["providers"]}
        </div>
        {regions["drawer"]}
      </div>
      {regions["status"]}
    </div>
    """


def render_dashboard_regions(
    run: GenerationRun | None = None,
    adult_mode: bool = False,
    scan: dict | None = None,
    relay_status: dict | None = None,
    active_section: str = "Forge",
    operator_state: dict | None = None,
) -> dict[str, str]:
    """
    Assemble all dashboard UI regions into a dictionary of HTML markup.
    
    Parameters:
        run: A generation run or None.
        adult_mode: Whether to render adult-mode content.
        scan: Scanner status and findings or None.
        relay_status: Model relay configuration or None.
        active_section: The currently active navigation section.
        operator_state: Operator control state or None.
    
    Returns:
        dict[str, str]: HTML markup strings for each dashboard region.
    """
    return {
        "topbar": render_topbar(adult_mode, relay_status, scan, operator_state),
        "rail": render_left_rail(active_section),
        "command_rail": render_command_rail(active_section),
        "workflow": render_workflow(run, operator_state),
        "operations": render_operations_panel(active_section, run, scan, relay_status, adult_mode=adult_mode, operator_state=operator_state),
        "inspector": render_inspector(run, scan, relay_status, operator_state),
        "drawer": render_drawer(run),
        "status": render_status_bar(operator_state),
        "artifacts": render_artifact_lane(run, scan, operator_state),
        "providers": render_provider_cards(relay_status, adult_mode),
    }
