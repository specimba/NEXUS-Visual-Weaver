from pathlib import Path

from nexus_visual_weaver.catalog import (
    DEFAULT_ACTIVE_STACK,
    PRIVATE_RESEARCH_STACK,
    active_stack,
    catalog_summary,
    filter_catalog,
    parameter_budget,
)
from nexus_visual_weaver.grounding import inspect_outfit
from nexus_visual_weaver.model_relay import WeaverModelRelay
from nexus_visual_weaver.planner import build_command_center_run
from nexus_visual_weaver.render import (
    render_command_header,
    render_dashboard_regions,
    render_inspector,
    render_operations_panel,
    render_provider_cards,
    render_topbar,
    render_trust_strip,
)
from nexus_visual_weaver.schema import ModelCandidate
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


def test_public_stack_uses_flux_9b_and_excludes_offellia() -> None:
    stack = active_stack(False)
    repo_ids = {model.repo_id for model in stack}

    assert "black-forest-labs/FLUX.2-klein-9B" in repo_ids
    assert "black-forest-labs/FLUX.2-klein-4B" not in repo_ids
    assert not any("OFFELLIA" in repo_id for repo_id in repo_ids)
    assert all(model.params_b < 32.0 for model in stack)


def test_private_catalog_keeps_stronger_research_models_available() -> None:
    """
    Verify that private catalog mode includes OFFELLIA and other research models alongside standard models.
    """
    private_models, _ = filter_catalog(True)
    repo_ids = {model.repo_id for model in private_models}

    assert "black-forest-labs/FLUX.2-klein-9B" in repo_ids
    assert "Brunobkr/OFFELLIA_Q4_0_gemma-4-12B-it.gguf" in repo_ids


def test_command_center_run_is_checkpointed() -> None:
    run = build_command_center_run(
        "Slavic model, patent leather, faux fur, Chantilly lace, crimson hardware, platform boots, NEXUS sigils"
    )
    assert run.checkpoint.checkpoint_id.startswith("nw-")
    assert run.video.checkpoint_required is True
    assert run.inspection.targets
    assert any(model.repo_id == "nvidia/LocateAnything-3B" for model in run.model_stack)


def test_command_center_run_snapshots_controls_and_skips_empty_reference_ids() -> None:
    controls = {"wardrobe": {"footwear": "platform boots"}}
    references = [{"source": "upload"}, {"basename": "reference.png"}]

    run = build_command_center_run(
        "gothic couture archivist",
        creator_controls=controls,
        reference_metadata=references,
    )
    controls["wardrobe"]["footwear"] = "mutated"
    references[1]["basename"] = "mutated.png"

    assert run.request.references == ["reference.png"]
    assert run.request.creator_controls["wardrobe"]["footwear"] == "platform boots"
    assert run.request.reference_metadata[1]["basename"] == "reference.png"


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


def test_security_scan_safe_vs_blocked_fixtures() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    safe = scan_file(str(fixture_dir / "st3gg_safe_clean.png"))
    blocked = scan_file(str(fixture_dir / "st3gg_blocked_trailing.png"))

    assert safe["status"] == "pass"
    assert safe["export_gate"] == "clear"
    assert blocked["status"] == "review"
    assert blocked["export_gate"] == "blocked"
    assert any("trailing data" in finding for finding in blocked["findings"])


def test_dashboard_regions_expose_artifacts_and_provider_cards() -> None:
    run = build_command_center_run("gothic couture archivist, patent leather, platform boots")
    relay = WeaverModelRelay()
    regions = render_dashboard_regions(
        run=run,
        adult_mode=False,
        scan=scan_file(None),
        relay_status=relay.dashboard_snapshot(public_demo=True),
    )

    assert "Output" in regions["artifacts"]
    assert "nw-preview-stage" in regions["artifacts"]
    assert "PRIMARY OUTPUT STAGE" in regions["artifacts"]
    assert "JUDGE-SAFE DEMO OUTPUT" in regions["artifacts"]
    assert "Generate an image to unlock checkpoint review." in regions["artifacts"]
    assert "Forge Operations" in regions["operations"]
    assert "Optional Provider Lanes" in regions["providers"]
    assert "nw-provider-meter" in regions["providers"]
    assert "optional gateway" in regions["providers"]
    assert "CHECKPOINTED" in regions["providers"]
    assert "Forge Operations" in regions["operations"]
    assert "Optional Provider Lanes" in regions["providers"]
    assert "nw-provider-meter" in regions["providers"]
    assert "Selected: Forge" in regions["command_rail"]
    assert "TRUST MODEL" in regions["topbar"]
    assert "Clean PNG -> pass" in regions["topbar"]
    assert "ST3GG Scan" in regions["inspector"]
    assert "nw-weave-console" in regions["workflow"]
    assert "Current Run Summary" in regions["workflow"]
    assert "Hackathon Signal" in regions["workflow"]
    assert "Boots / heels" in regions["drawer"]
    assert "checkpointed" in regions["drawer"]


def test_dashboard_regions_render_with_empty_relay_and_default_scan() -> None:
    regions = render_dashboard_regions(relay_status={}, scan=None, active_section="Forge")

    assert "Forge Operations" in regions["operations"]
    assert "not-started" in regions["operations"]
    assert "snapshot pending" in regions["providers"]
    assert "Selected: Forge" in regions["command_rail"]
    assert "Real output and export evidence appear here" in regions["artifacts"]


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
    assert "FLUX.2 9B PINNED" in header
    assert "4B SIDECAR" in header
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


# --- render_trust_strip tests ---

def test_render_trust_strip_defaults_to_idle_state() -> None:
    html = render_trust_strip()

    assert "TRUST MODEL" in html
    assert "Generation is not export." in html
    assert "ST3GG READY" in html
    assert "Export waits for review" in html
    assert "Clean PNG -> pass." in html
    assert "FIXTURE EVIDENCE" in html


def test_render_trust_strip_pass_scan_shows_clear_export() -> None:
    scan = {"status": "pass", "export_gate": "clear", "findings": ["all checks passed"], "purification_actions": ["none needed"]}
    html = render_trust_strip(scan=scan)

    assert "ST3GG PASS" in html
    assert "EXPORT CLEAR" in html
    assert "all checks passed" in html


def test_render_trust_strip_review_scan_shows_blocked_export() -> None:
    scan = {"status": "review", "export_gate": "blocked", "findings": ["trailing data after IEND"], "purification_actions": ["truncate PNG"]}
    html = render_trust_strip(scan=scan)

    assert "ST3GG REVIEW" in html
    assert "Export Blocked - Override Available" in html
    assert "trailing data after IEND" in html


def test_render_trust_strip_redacts_payload_details() -> None:
    scan = {
        "status": "review",
        "export_gate": "blocked",
        "findings": ["payload excerpt: deadbeef hidden content recovered"],
        "purification_actions": ["raw byte hex dump should stay quarantined"],
    }
    html = render_trust_strip(scan=scan)

    assert "Redacted scan detail" in html
    assert "deadbeef" not in html
    assert "hex dump" not in html


def test_render_trust_strip_approved_checkpoint_shows_pass() -> None:
    operator_state = {"checkpoint": "approved", "provider_state": "export_ready"}
    html = render_trust_strip(operator_state=operator_state)

    assert "CHECKPOINT APPROVED" in html


def test_render_trust_strip_pending_review_checkpoint_label() -> None:
    operator_state = {"checkpoint": "pending_review"}
    html = render_trust_strip(operator_state=operator_state)

    assert "CHECKPOINT PENDING REVIEW" in html


# --- render_topbar tests ---

def test_render_topbar_includes_trust_strip() -> None:
    html = render_topbar()

    assert "TRUST MODEL" in html
    assert "nw-trust-strip" in html


def test_render_topbar_with_scan_passes_to_trust_strip() -> None:
    scan = {"status": "pass", "export_gate": "clear", "findings": ["no issues"], "purification_actions": []}
    html = render_topbar(scan=scan)

    assert "ST3GG PASS" in html
    assert "EXPORT CLEAR" in html


def test_render_topbar_with_operator_state_shows_checkpoint() -> None:
    operator_state = {"checkpoint": "approved"}
    html = render_topbar(operator_state=operator_state)

    assert "CHECKPOINT APPROVED" in html


def test_render_topbar_default_scan_shows_fixture_evidence() -> None:
    html = render_topbar()

    assert "Clean PNG -> pass." in html
    assert "PNG trailing bytes -> blocked." in html


# --- render_inspector sponsor evidence tests ---

def test_render_inspector_shows_sponsor_evidence_section() -> None:
    html = render_inspector()

    assert "Sponsor Evidence" in html
    assert "OpenBMB MiniCPM" in html
    assert "NVIDIA Nemotron" in html


def test_render_inspector_with_missing_secret_shows_pending() -> None:
    operator_state = {
        "minicpm_judge": {"status": "missing_secret", "repo_id": "openbmb/MiniCPM-V-4.6"},
        "nemotron_evidence": {"status": "missing_secret", "repo_id": "nvidia/NVIDIA-Nemotron-Parse-v1.2"},
    }
    html = render_inspector(operator_state=operator_state)

    assert "Optional - Secret Required" in html


def test_render_inspector_with_success_judge_shows_success_status() -> None:
    operator_state = {
        "minicpm_judge": {"status": "success", "repo_id": "openbmb/MiniCPM-V-4.6"},
        "nemotron_evidence": {"status": "success", "repo_id": "nvidia/NVIDIA-Nemotron-Parse-v1.2"},
    }
    html = render_inspector(operator_state=operator_state)

    assert html.count("SUCCESS") >= 2


def test_render_inspector_shows_default_stack_label_without_run() -> None:
    html = render_inspector()

    assert "FLUX.2 9B / MiniCPM / LocateAnything" in html


# --- render_provider_cards sponsor lane tests ---

def test_render_provider_cards_shows_openbmb_and_nvidia_entries() -> None:
    html = render_provider_cards()

    assert "Openbmb" in html or "openbmb" in html.lower()
    assert "Nvidia" in html or "nvidia" in html.lower()


def test_render_provider_cards_shows_sponsor_lane_badge_for_openbmb(monkeypatch) -> None:
    monkeypatch.setenv("MINICPM_API_KEY", "test-key")
    monkeypatch.setenv("MINICPM_BASE_URL", "https://minicpm.example.test")
    html = render_provider_cards()

    assert "SPONSOR LANE" in html


def test_render_provider_cards_shows_missing_secret_for_unconfigured_sponsor(monkeypatch) -> None:
    monkeypatch.delenv("MINICPM_API_KEY", raising=False)
    monkeypatch.delenv("OPENBMB_API_KEY", raising=False)
    monkeypatch.delenv("NEMOTRON_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    html = render_provider_cards()

    assert "Optional - Secret Required" in html


def test_render_provider_cards_configured_openbmb_shows_configured(monkeypatch) -> None:
    monkeypatch.setenv("MINICPM_API_KEY", "test-key")
    monkeypatch.delenv("MINICPM_BASE_URL", raising=False)
    monkeypatch.delenv("NEMOTRON_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NEMOTRON_BASE_URL", raising=False)
    monkeypatch.delenv("FAL_KEY", raising=False)
    monkeypatch.delenv("NETLIFY_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    html = render_provider_cards()

    assert "CONFIGURED" not in html
    assert "Optional - Secret Required" in html


def test_render_provider_cards_configured_openbmb_requires_key_and_base_url(monkeypatch) -> None:
    monkeypatch.setenv("MINICPM_API_KEY", "test-key")
    monkeypatch.setenv("MINICPM_BASE_URL", "https://minicpm.example.test")
    html = render_provider_cards()

    assert "CONFIGURED" in html


def test_render_operations_and_inspector_redact_payload_details() -> None:
    scan = {
        "status": "review",
        "export_gate": "blocked",
        "findings": ["payload excerpt: recovered hidden content"],
        "purification_actions": ["base64 raw bytes quarantined"],
    }

    operations = render_operations_panel(active_section="Security", scan=scan)
    inspector = render_inspector(scan=scan)

    assert "Redacted scan detail" in operations
    assert "Redacted scan detail" in inspector
    assert "recovered hidden content" not in operations
    assert "base64 raw bytes" not in inspector


# --- catalog public_demo field tests ---

def test_filter_catalog_includes_flux_9b_in_public_mode() -> None:
    models, _ = filter_catalog(False)
    repo_ids = {model.repo_id for model in models}

    assert "black-forest-labs/FLUX.2-klein-9B" in repo_ids


def test_filter_catalog_includes_flux_9b_in_adult_mode() -> None:
    models, _ = filter_catalog(True)
    repo_ids = {model.repo_id for model in models}

    assert "black-forest-labs/FLUX.2-klein-9B" in repo_ids


def test_filter_catalog_excludes_offellia_in_public_mode() -> None:
    models, _ = filter_catalog(False)
    repo_ids = {model.repo_id for model in models}

    assert not any("OFFELLIA" in repo_id for repo_id in repo_ids)


def test_active_stack_uses_private_research_stack_in_adult_mode() -> None:
    stack = active_stack(True)
    repo_ids = {model.repo_id for model in stack}

    assert "black-forest-labs/FLUX.2-klein-9B" in repo_ids
    assert "black-forest-labs/FLUX.2-klein-4B" not in repo_ids


def test_private_research_stack_constant_contains_9b_and_offellia() -> None:
    assert "black-forest-labs/FLUX.2-klein-9B" in PRIVATE_RESEARCH_STACK
    assert "Brunobkr/OFFELLIA_Q4_0_gemma-4-12B-it.gguf" in PRIVATE_RESEARCH_STACK


def test_default_active_stack_constant_uses_9b_and_sponsor_models() -> None:
    assert "black-forest-labs/FLUX.2-klein-9B" in DEFAULT_ACTIVE_STACK
    assert "openbmb/MiniCPM-V-4.6" in DEFAULT_ACTIVE_STACK
    assert "nvidia/NVIDIA-Nemotron-Parse-v1.2" in DEFAULT_ACTIVE_STACK
    assert "black-forest-labs/FLUX.2-klein-4B" not in DEFAULT_ACTIVE_STACK


# --- schema ModelCandidate public_demo tests ---

def test_model_candidate_public_demo_defaults_to_true() -> None:
    candidate = ModelCandidate(
        repo_id="test/model",
        role="test_role",
        task="text-to-image",
        params_b=1.0,
        runtime="local",
        license="apache-2.0",
    )
    assert candidate.public_demo is True


def test_model_candidate_public_demo_can_be_set_false() -> None:
    candidate = ModelCandidate(
        repo_id="test/private-model",
        role="private_role",
        task="text-to-image",
        params_b=9.0,
        runtime="gated provider",
        license="other",
        public_demo=False,
    )
    assert candidate.public_demo is False


def test_public_demo_false_models_are_excluded_from_public_filter() -> None:
    private = ModelCandidate(
        repo_id="test/hidden-model",
        role="private",
        task="text-to-image",
        params_b=2.0,
        runtime="local",
        license="other",
        public_demo=False,
    )
    models_public, _ = filter_catalog(False)
    assert all(m.public_demo for m in models_public)


# --- catalog FLUX.2-klein-4B tests ---

def test_filter_catalog_includes_flux_4b_in_public_mode() -> None:
    models, _ = filter_catalog(False)
    repo_ids = {model.repo_id for model in models}

    assert "black-forest-labs/FLUX.2-klein-4B" in repo_ids


def test_filter_catalog_includes_flux_4b_in_adult_mode() -> None:
    models, _ = filter_catalog(True)
    repo_ids = {model.repo_id for model in models}

    assert "black-forest-labs/FLUX.2-klein-4B" in repo_ids


def test_flux_4b_is_not_in_default_active_stack() -> None:
    stack = active_stack(False)
    repo_ids = {model.repo_id for model in stack}

    assert "black-forest-labs/FLUX.2-klein-4B" not in repo_ids


def test_flux_4b_role_is_tiny_titan_sidecar() -> None:
    models, _ = filter_catalog(False)
    flux_4b = next((m for m in models if m.repo_id == "black-forest-labs/FLUX.2-klein-4B"), None)

    assert flux_4b is not None
    assert "tiny_titan" in flux_4b.role


def test_flux_4b_has_apache_license() -> None:
    models, _ = filter_catalog(False)
    flux_4b = next((m for m in models if m.repo_id == "black-forest-labs/FLUX.2-klein-4B"), None)

    assert flux_4b is not None
    assert flux_4b.license == "apache-2.0"


# --- parameter_budget over_budget tests ---

def test_parameter_budget_passes_for_default_public_stack() -> None:
    budget = parameter_budget(active_stack(False))

    assert budget["status"] == "pass"
    assert budget["active_b"] <= 32.0


def test_parameter_budget_over_budget_for_large_stack() -> None:
    large_stack = [
        ModelCandidate(
            repo_id=f"test/model-{i}",
            role="test",
            task="text-to-image",
            params_b=10.0,
            runtime="local",
            license="apache-2.0",
        )
        for i in range(5)  # 50B total, over the 32B limit
    ]
    budget = parameter_budget(large_stack)

    assert budget["status"] == "over_budget"
    assert budget["active_b"] == 50.0
    assert budget["remaining_b"] < 0.0


def test_parameter_budget_exactly_at_limit() -> None:
    stack = [
        ModelCandidate(
            repo_id="test/model",
            role="test",
            task="text-to-image",
            params_b=32.0,
            runtime="local",
            license="apache-2.0",
        )
    ]
    budget = parameter_budget(stack)

    assert budget["status"] == "pass"
    assert budget["active_b"] == 32.0
    assert budget["remaining_b"] == 0.0


def test_parameter_budget_just_over_limit() -> None:
    stack = [
        ModelCandidate(
            repo_id="test/model",
            role="test",
            task="text-to-image",
            params_b=32.1,
            runtime="local",
            license="apache-2.0",
        )
    ]
    budget = parameter_budget(stack)

    assert budget["status"] == "over_budget"


def test_catalog_summary_includes_budget_keys() -> None:
    summary = catalog_summary(False)

    assert "active_b" in summary
    assert "limit_b" in summary
    assert "remaining_b" in summary
    assert "status" in summary
    assert summary["limit_b"] == 32.0


def test_catalog_summary_models_visible_count_matches_filter() -> None:
    models, adapters = filter_catalog(False)
    summary = catalog_summary(False)

    assert summary["models_visible"] == len(models)
    assert summary["adapters_visible"] == len(adapters)


# --- catalog MiniCPM-V-4.6 and Nemotron-Parse tests ---

def test_minicpm_v46_in_public_catalog() -> None:
    models, _ = filter_catalog(False)
    repo_ids = {model.repo_id for model in models}

    assert "openbmb/MiniCPM-V-4.6" in repo_ids


def test_nemotron_parse_in_public_catalog() -> None:
    models, _ = filter_catalog(False)
    repo_ids = {model.repo_id for model in models}

    assert "nvidia/NVIDIA-Nemotron-Parse-v1.2" in repo_ids


def test_minicpm_v46_role_is_sponsor_visual_judge() -> None:
    models, _ = filter_catalog(False)
    minicpm = next((m for m in models if m.repo_id == "openbmb/MiniCPM-V-4.6"), None)

    assert minicpm is not None
    assert minicpm.role == "sponsor_visual_judge"
    assert minicpm.params_b == 1.30


def test_nemotron_parse_role_is_sponsor_structured_parse() -> None:
    models, _ = filter_catalog(False)
    nemotron = next((m for m in models if m.repo_id == "nvidia/NVIDIA-Nemotron-Parse-v1.2"), None)

    assert nemotron is not None
    assert nemotron.role == "sponsor_structured_parse"
    assert nemotron.params_b == 0.94


# --- adapter catalog changes tests ---

def test_dever_style_lora_compatible_with_9b_and_4b() -> None:
    from nexus_visual_weaver.catalog import ADAPTER_CATALOG

    dever = next((a for a in ADAPTER_CATALOG if a.repo_id == "DeverStyle/Flux.2-Klein-Loras"), None)

    assert dever is not None
    assert "black-forest-labs/FLUX.2-klein-9B" in dever.compatible_repo_ids
    assert "black-forest-labs/FLUX.2-klein-4B" in dever.compatible_repo_ids


def test_dever_style_lora_has_trigger_words() -> None:
    from nexus_visual_weaver.catalog import ADAPTER_CATALOG

    dever = next((a for a in ADAPTER_CATALOG if a.repo_id == "DeverStyle/Flux.2-Klein-Loras"), None)

    assert dever is not None
    assert len(dever.trigger_words) > 0
    assert "gothic couture" in dever.trigger_words


def test_4b_outpaint_lora_requires_image() -> None:
    from nexus_visual_weaver.catalog import ADAPTER_CATALOG

    outpaint = next((a for a in ADAPTER_CATALOG if a.repo_id == "fal/flux-2-klein-4B-outpaint-lora"), None)

    assert outpaint is not None
    assert outpaint.requires_image is True
    assert "black-forest-labs/FLUX.2-klein-4B" in outpaint.compatible_repo_ids


# --- wardrobe controls tests ---

def test_build_outfit_graph_controls_override_outerwear() -> None:
    outfit = build_outfit_graph(
        "minimal portrait",
        controls={"outerwear": "tailored rain slicker"},
    )
    outerwear_slot = next((s for s in outfit.slots if s.name == "outerwear"), None)

    assert outerwear_slot is not None
    assert outerwear_slot.description == "tailored rain slicker"


def test_build_outfit_graph_controls_override_footwear() -> None:
    outfit = build_outfit_graph(
        "minimal portrait",
        controls={"footwear": "patent leather heels"},
    )
    footwear_slot = next((s for s in outfit.slots if s.name == "footwear"), None)

    assert footwear_slot is not None
    assert footwear_slot.description == "patent leather heels"


def test_build_outfit_graph_controls_override_palette_for_all_slots() -> None:
    custom_palette = "obsidian, pearl, crimson"
    outfit = build_outfit_graph(
        "minimal portrait",
        controls={"palette": custom_palette},
    )

    for slot in outfit.slots:
        assert slot.palette == custom_palette


def test_build_outfit_graph_controls_override_hardware() -> None:
    outfit = build_outfit_graph(
        "minimal portrait",
        controls={"hardware": "silver occult buckles"},
    )
    jewelry_slot = next((s for s in outfit.slots if s.name == "jewelry"), None)

    assert jewelry_slot is not None
    assert jewelry_slot.material == "silver_occult_buckles"


def test_build_outfit_graph_locked_slots_control_locks_named_slots() -> None:
    outfit = build_outfit_graph(
        "minimal portrait",
        controls={"locked_slots": ["hair_headwear", "props"]},
    )
    hair_slot = next((s for s in outfit.slots if s.name == "hair_headwear"), None)
    props_slot = next((s for s in outfit.slots if s.name == "props"), None)

    assert hair_slot is not None and hair_slot.locked is True
    assert props_slot is not None and props_slot.locked is True


def test_build_outfit_graph_locate_focus_sets_manual_focus_region() -> None:
    outfit = build_outfit_graph(
        "minimal portrait",
        controls={"locate_focus": ["footwear", "jewelry"]},
    )
    footwear_slot = next((s for s in outfit.slots if s.name == "footwear"), None)
    jewelry_slot = next((s for s in outfit.slots if s.name == "jewelry"), None)
    hair_slot = next((s for s in outfit.slots if s.name == "hair_headwear"), None)

    assert footwear_slot is not None and footwear_slot.locate_region == "manual-focus"
    assert jewelry_slot is not None and jewelry_slot.locate_region == "manual-focus"
    assert hair_slot is not None and hair_slot.locate_region == "auto-map"


def test_build_outfit_graph_with_no_controls_uses_defaults() -> None:
    outfit = build_outfit_graph("gothic couture brief")

    assert len(outfit.slots) == len(outfit.slots)  # All slots present
    assert outfit.score >= 0.68  # Base score


def test_build_outfit_graph_adult_mode_marks_upper_lower_slots() -> None:
    outfit = build_outfit_graph("gothic brief", adult_mode=True)
    upper = next((s for s in outfit.slots if s.name == "upper_body"), None)
    lower = next((s for s in outfit.slots if s.name == "lower_body"), None)
    outerwear = next((s for s in outfit.slots if s.name == "outerwear"), None)

    assert upper is not None and upper.adult_only is True
    assert lower is not None and lower.adult_only is True
    assert outerwear is not None and outerwear.adult_only is False
