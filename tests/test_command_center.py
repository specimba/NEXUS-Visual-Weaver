from pathlib import Path

from nexus_visual_weaver.catalog import active_stack, catalog_summary, filter_catalog, parameter_budget
from nexus_visual_weaver.grounding import inspect_outfit
from nexus_visual_weaver.planner import build_command_center_run
from nexus_visual_weaver.render import render_dashboard_regions
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
    regions = render_dashboard_regions(run=run, adult_mode=False, scan=scan_file(None))

    assert "Artifact Preview Lane" in regions["artifacts"]
    assert "Provider Handoff Cards" in regions["providers"]
    assert "Selected: Forge" in regions["command_rail"]
    assert "ST3GG Scan" in regions["inspector"]


def test_catalog_summary_reflects_adult_scope() -> None:
    default_summary = catalog_summary(False)
    adult_summary = catalog_summary(True)
    assert default_summary["adult_catalog"] == "hidden"
    assert adult_summary["adult_catalog"] == "enabled"
    assert adult_summary["models_visible"] > default_summary["models_visible"]
