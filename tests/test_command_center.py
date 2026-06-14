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
