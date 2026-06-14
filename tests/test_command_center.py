from pathlib import Path

from nexus_visual_weaver.catalog import active_stack, catalog_summary, filter_catalog, parameter_budget
from nexus_visual_weaver.grounding import inspect_outfit
from nexus_visual_weaver.model_relay import WeaverModelRelay
from nexus_visual_weaver.planner import build_command_center_run
from nexus_visual_weaver.render import render_command_header, render_dashboard_regions, render_operations_panel
from nexus_visual_weaver.security import scan_file
from nexus_visual_weaver.taste import refine_prompt, score_prompt
from nexus_visual_weaver.wardrobe import build_outfit_graph


def test_taste_refinement_adds_locked_features() -> None:
    refined = refine_prompt("Cyberpunk woman in neon rain")
    assert refined.score >= 0.75
    assert "patent leather" in refined.refined.lower()
    assert "crimson hardware" in refined.refined.lower()


def test_wardrobe_slots_have_required_structure() -> None:
    outfit = build_outfit_graph("black patent leather coat, crimson hardware, platform boots")
    slot_names = {slot.name for slot in outfit.slots}
    assert {"outerwear", "upper_body", "footwear", "jewelry", "background_context"} <= slot_names
    assert all(slot.edit_priority >= 1 for slot in outfit.slots)


def test_locateanything_inspection_flags_drift_when_needed() -> None:
    outfit = build_outfit_graph("minimal cyberpunk portrait")
    report = inspect_outfit(outfit)
    assert report.locate_model == "nvidia/LocateAnything-3B"
    assert report.targets
    assert "footwear requires stronger prompt lock" in report.drift_flags


def test_adult_catalog_hidden_by_default_and_visible_when_enabled() -> None:
    models_default, adapters_default = filter_catalog(False)
    models_adult, adapters_adult = filter_catalog(True)
    assert not any(model.adult_only for model in models_default)
    assert not any(adapter.adult_only for adapter in adapters_default)
    assert any(model.adult_only for model in models_adult)
    assert any(adapter.adult_only for adapter in adapters_adult)


def test_active_parameter_budget_passes_default_stack() -> None:
    budget = parameter_budget(active_stack(False))
    assert budget["status"] == "pass"
    assert budget["active_b"] <= 32.0


def test_command_center_run_is_checkpointed() -> None:
    run = build_command_center_run(
        "Slavic model, patent leather, faux fur, Chantilly lace, crimson hardware, platform boots, NEXUS sigils"
    )
    assert run.checkpoint.checkpoint_id.startswith("nw-")
    assert run.video.checkpoint_required is True
    assert run.inspection.targets
    assert run.model_stack[2].repo_id == "nvidia/LocateAnything-3B"


def test_security_scan_does_not_return_payload_excerpt() -> None:
    sample = Path(__file__).parent / "fixtures" / "sample.png"
    scan = scan_file(str(sample))
    assert scan["payload_excerpt"] is None
    assert scan["status"] in {"pass", "review"}
    assert scan["purification_actions"]
    assert scan["export_gate"] in {"clear", "blocked"}


def test_security_scan_flags_extension_magic_mismatch() -> None:
    sample = Path(__file__).parent / "fixtures" / "sample.png"
    scan = scan_file(str(sample))

    assert scan["extension"] == ".png"
    assert scan["magic"] == "unknown"
    assert scan["status"] == "review"
    assert scan["export_gate"] == "blocked"
    assert any("extension does not match" in finding for finding in scan["findings"])


def test_dashboard_regions_expose_artifacts_and_provider_cards() -> None:
    run = build_command_center_run("gothic couture archivist, patent leather, platform boots")
    relay = WeaverModelRelay()
    regions = render_dashboard_regions(
        run=run,
        adult_mode=False,
        scan=scan_file(None),
        relay_status=relay.dashboard_snapshot(public_demo=True),
    )

    assert "Artifact Preview Lane" in regions["artifacts"]
    assert "nw-preview-stage" in regions["artifacts"]
    assert "nw-preview-ribbon" in regions["artifacts"]
    assert "PRIMARY OUTPUT STAGE" in regions["artifacts"]
    assert "JUDGE-SAFE DEMO OUTPUT" in regions["artifacts"]
    assert "state: dry-run / configured / blocked / failed" in regions["artifacts"]
    assert "Forge Operations" in regions["operations"]
    assert "Provider Handoff Cards" in regions["providers"]
    assert "nw-provider-meter" in regions["providers"]
    assert "optional gateway" in regions["providers"]
    assert "CHECKPOINTED" in regions["providers"]
    assert "Forge Operations" in regions["operations"]
    assert "Provider Handoff Cards" in regions["providers"]
    assert "nw-provider-meter" in regions["providers"]
    assert "optional gateway" in regions["providers"]
    assert "CHECKPOINTED" in regions["providers"]
    assert "Selected: Forge" in regions["command_rail"]
    assert "ST3GG Scan" in regions["inspector"]
    assert "nw-weave-console" in regions["workflow"]
    assert "Hackathon Signal" in regions["workflow"]
    assert "Boots / heels" in regions["drawer"]
    assert "checkpointed" in regions["drawer"]


def test_dashboard_regions_render_with_empty_relay_and_default_scan() -> None:
    regions = render_dashboard_regions(relay_status={}, scan=None, active_section="Forge")

    assert "Forge Operations" in regions["operations"]
    assert "not-started" in regions["operations"]
    assert "snapshot pending" in regions["providers"]
    assert "Selected: Forge" in regions["command_rail"]
    assert "provider call remains checkpointed" in regions["artifacts"]


def test_dashboard_operations_follow_selected_section() -> None:
    """
    Verify that dashboard operations and command rail update consistently across different active sections.
    
    Asserts that the operations panel displays the active section name and its corresponding marker, while the command rail correctly reflects the selected section.
    """
    relay = WeaverModelRelay()
    sections = {
        "Wardrobe": "Footwear focus",
        "Lore": "Beat budget",
        "Models": "Rotation mode",
        "Security": "ST3GG state",
        "Runs": "Ledger mode",
    }

    for section, marker in sections.items():
        regions = render_dashboard_regions(
            adult_mode=(section == "Models"),
            scan=scan_file(None),
            relay_status=relay.dashboard_snapshot(public_demo=section != "Models"),
            active_section=section,
        )
        assert f"{section} Operations" in regions["operations"]
        assert marker in regions["operations"]
        assert f"Selected: {section}" in regions["command_rail"]


def test_security_operations_distinguish_clean_scan_from_idle() -> None:
    """
    Validate that the Security operations panel distinguishes a clean scan from an unselected state.
    
    When provided a clean scan (status "pass", no findings), the panel displays "No findings."
    but does not display "No upload selected." (the idle-state message).
    """
    clean_scan = {"status": "pass", "export_gate": "clear", "findings": []}
    html = render_operations_panel(active_section="Security", scan=clean_scan)

    assert "No findings." in html
    assert "No upload selected." not in html


def test_command_header_exposes_governed_run_controls() -> None:
    header = render_command_header()

    assert "Raven Chronicle Active Weave" in header
    assert "ST3GG ALWAYS ON" in header
    assert "FLUX.2 PINNED" in header
    assert "HUMAN CHECKPOINT" in header


def test_dashboard_surfaces_hf_space_status_without_secrets(monkeypatch) -> None:
    for name in ["FAL_KEY", "NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID", "OPENAI_BASE_URL", "OPENAI_API_KEY", "MODAL_TOKEN_ID"]:
        monkeypatch.delenv(name, raising=False)

    regions = render_dashboard_regions(relay_status=WeaverModelRelay().dashboard_snapshot(public_demo=True))

    assert "ZeroGPU" in regions["topbar"]
    assert "no provider secrets" in regions["topbar"]
    assert "HF Space" in regions["status"]


def test_catalog_summary_reflects_adult_scope() -> None:
    default_summary = catalog_summary(False)
    adult_summary = catalog_summary(True)
    assert default_summary["adult_catalog"] == "hidden"
    assert adult_summary["adult_catalog"] == "enabled"
    assert adult_summary["models_visible"] > default_summary["models_visible"]


def test_render_status_bar_idle_uses_idle_stop_class() -> None:
    from nexus_visual_weaver.render import render_status_bar

    html = render_status_bar(operator_state={"provider_state": "idle"})

    assert "nw-stop-idle" in html
    assert "nw-stop-active" not in html
    assert "HF Space" in html


def test_render_status_bar_active_state_uses_active_stop_class() -> None:
    from nexus_visual_weaver.render import render_status_bar

    for active_state in ("checkpointed", "export_ready", "exported", "blocked", "stopped"):
        html = render_status_bar(operator_state={"provider_state": active_state})
        assert "nw-stop-active" in html, f"Expected nw-stop-active for provider_state={active_state}"
        assert "nw-stop-idle" not in html


def test_render_status_bar_defaults_without_operator_state() -> None:
    from nexus_visual_weaver.render import render_status_bar

    html = render_status_bar()

    assert "nw-stop-idle" in html
    assert "Idle" in html


def test_render_workflow_approved_checkpoint_changes_action_label() -> None:
    from nexus_visual_weaver.render import render_workflow

    html = render_workflow(operator_state={"checkpoint": "approved", "provider_state": "export_ready"})

    assert "Checkpoint approved" in html
    assert "export packet may be prepared" in html


def test_render_workflow_stopped_provider_changes_action_label() -> None:
    from nexus_visual_weaver.render import render_workflow

    html = render_workflow(operator_state={"checkpoint": "pending", "provider_state": "stopped"})

    assert "Provider handoff stopped" in html
    assert "dry-run evidence remains available" in html


def test_render_workflow_exported_state_uses_pass_badge() -> None:
    from nexus_visual_weaver.render import render_workflow

    html = render_workflow(operator_state={"provider_state": "exported"})

    assert "EXPORTED" in html
    assert 'nw-pass' in html


def test_render_workflow_blocked_state_uses_warn_badge() -> None:
    from nexus_visual_weaver.render import render_workflow

    html = render_workflow(operator_state={"provider_state": "blocked"})

    assert "BLOCKED" in html
    assert 'nw-warn' in html


def test_render_artifact_lane_blocked_when_provider_blocked() -> None:
    from nexus_visual_weaver.render import render_artifact_lane

    html = render_artifact_lane(
        scan={"status": "idle", "export_gate": "pending"},
        operator_state={"provider_state": "blocked"},
    )

    # The video artifact card should be blocked when provider is blocked
    assert "BLOCKED" in html


def test_render_artifact_lane_blocked_when_export_gate_blocked() -> None:
    from nexus_visual_weaver.render import render_artifact_lane

    html = render_artifact_lane(
        scan={"status": "review", "export_gate": "blocked"},
        operator_state={"provider_state": "checkpointed"},
    )

    assert "BLOCKED" in html


def test_render_artifact_lane_preview_mode_labels() -> None:
    from nexus_visual_weaver.render import render_artifact_lane

    state_to_label = {
        "idle": "Idle",
        "dry-run": "Dry Run",
        "checkpointed": "Checkpointed",
        "export_ready": "Export Ready",
        "exported": "Exported",
        "blocked": "Blocked",
        "stopped": "Stopped",
    }
    for provider_state, expected_label in state_to_label.items():
        html = render_artifact_lane(operator_state={"provider_state": provider_state})
        assert expected_label in html, f"Expected preview mode label '{expected_label}' for state '{provider_state}'"


def test_render_operations_panel_invalid_section_defaults_to_forge() -> None:
    html = render_operations_panel(active_section="NonExistentSection")

    assert "Forge Operations" in html
    assert "Prompt contract" in html


def test_render_operations_panel_adult_mode_shows_private_scope() -> None:
    html = render_operations_panel(active_section="Models", adult_mode=True)

    assert "Private research scope" in html


def test_render_operations_panel_public_mode_shows_public_scope() -> None:
    html = render_operations_panel(active_section="Models", adult_mode=False)

    assert "Public demo scope" in html


def test_render_operations_panel_security_with_multiple_findings() -> None:
    scan_with_findings = {
        "status": "review",
        "export_gate": "blocked",
        "findings": ["extension does not match magic bytes", "LSB anomaly detected"],
    }
    html = render_operations_panel(active_section="Security", scan=scan_with_findings)

    assert "extension does not match magic bytes" in html
    assert "No findings." not in html


def test_render_operations_panel_security_idle_shows_no_upload_message() -> None:
    html = render_operations_panel(active_section="Security", scan=None)

    assert "No upload selected." in html


def test_render_operations_panel_forge_shows_operator_message() -> None:
    html = render_operations_panel(
        active_section="Forge",
        operator_state={"provider_state": "checkpointed", "message": "Run packet generated."},
    )

    assert "Run packet generated." in html
    assert "CHECKPOINTED" in html


def test_render_provider_cards_optional_providers_configured_with_fal_key(monkeypatch) -> None:
    from nexus_visual_weaver.render import render_provider_cards

    monkeypatch.setenv("FAL_KEY", "test-fal-key")
    monkeypatch.delenv("NETLIFY_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CF_ACCOUNT_ID", raising=False)

    html = render_provider_cards()

    # fal should show as configured
    assert "CONFIGURED" in html


def test_render_provider_cards_optional_providers_blocked_without_secrets(monkeypatch) -> None:
    from nexus_visual_weaver.render import render_provider_cards

    monkeypatch.delenv("FAL_KEY", raising=False)
    monkeypatch.delenv("NETLIFY_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("NETLIFY_SITE_ID", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CF_ACCOUNT_ID", raising=False)

    html = render_provider_cards()

    # All three optional gateways should appear as blocked
    assert html.count("NOT MVP DEFAULT") == 3
    assert "Fal" in html
    assert "Netlify" in html
    assert "Cloudflare" in html


def test_render_provider_cards_adult_mode_label() -> None:
    from nexus_visual_weaver.render import render_provider_cards

    public_html = render_provider_cards(adult_mode=False)
    private_html = render_provider_cards(adult_mode=True)

    assert "PUBLIC DEMO SAFE" in public_html
    assert "PRIVATE RESEARCH" in private_html


def test_render_dashboard_regions_returns_operations_key() -> None:
    regions = render_dashboard_regions()

    assert "operations" in regions
    assert isinstance(regions["operations"], str)
    assert len(regions["operations"]) > 0


def test_render_dashboard_regions_operator_state_propagates_to_workflow_and_status() -> None:
    operator_state = {
        "provider_state": "exported",
        "checkpoint": "approved",
        "export": "clear",
        "message": "Export complete.",
    }
    regions = render_dashboard_regions(operator_state=operator_state)

    assert "EXPORTED" in regions["workflow"]
    assert "nw-stop-active" in regions["status"]
