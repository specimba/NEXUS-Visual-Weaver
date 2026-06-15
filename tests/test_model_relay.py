from __future__ import annotations

from nexus_visual_weaver.model_relay import WeaverModelRelay
from nexus_visual_weaver.render import render_dashboard


def test_pinned_lanes_do_not_rotate() -> None:
    relay = WeaverModelRelay()
    decision = relay.select_lane("image_generation", strategy="private_research")

    assert decision.pinned is True
    assert decision.rotatable is False
    assert decision.primary is not None
    assert decision.primary.repo_id == "black-forest-labs/FLUX.2-klein-9B"
    assert decision.primary.params_b == 9.0
    assert decision.fallbacks == []
    assert "rotation disabled" in decision.reason


def test_tiny_titan_sidecar_keeps_flux_4b_available() -> None:
    relay = WeaverModelRelay()
    decision = relay.select_lane("tiny_titan_sidecar", budget=4.0, public_demo=True, strategy="license_safe_public")

    assert decision.primary is not None
    assert decision.primary.repo_id == "black-forest-labs/FLUX.2-klein-4B"
    assert decision.primary.pinned is False
    assert decision.primary.params_b == 4.0


def test_public_private_taste_judge_respects_license_and_budget() -> None:
    relay = WeaverModelRelay()

    public = relay.select_lane("taste_judge", public_demo=True, strategy="quality_first")
    private = relay.select_lane("taste_judge", budget=12.0, public_demo=False, strategy="private_research")

    assert public.primary is not None
    assert public.primary.params_b <= 5.0
    assert public.primary.public_safe is True
    assert "OFFELLIA" not in public.primary.repo_id
    assert private.primary is not None
    assert private.primary.model_id == "offellia-gemma4-12b-private"


def test_audio_tts_excludes_higgs_and_keeps_one_active_model() -> None:
    relay = WeaverModelRelay()

    decision = relay.select_lane("audio_lore_tts", public_demo=True, strategy="license_safe_public")
    selected_ids = [decision.primary.model_id] + [record.model_id for record in decision.fallbacks]

    assert decision.primary is not None
    assert decision.primary.params_b <= 5.0
    assert decision.primary.model_id != "higgs-audio-v3-excluded"
    assert "higgs-audio-v3-excluded" not in selected_ids
    assert decision.primary.lane == "audio_lore_tts"


def test_quota_exhaustion_enters_cooldown_and_uses_fallback() -> None:
    relay = WeaverModelRelay()
    exhausted = relay.records["hf-api-metadata-cache"]
    exhausted.rpm_limit = 1
    relay.record_success(exhausted.model_id)

    decision = relay.select_lane("hf_catalog_research", public_demo=True, strategy="quota_saver")

    assert exhausted.cooldown_until is not None
    assert decision.primary is not None
    assert decision.primary.model_id != exhausted.model_id
    assert any("quota exhausted" in reason for reason in decision.skipped)


def test_metadata_dedup_prevents_repeated_hf_lookup() -> None:
    relay = WeaverModelRelay()
    calls = {"count": 0}

    def resolver() -> dict[str, int]:
        calls["count"] += 1
        return {"calls": calls["count"]}

    first = relay.metadata_lookup("hf:black-forest-labs/FLUX.2-klein-4B", resolver)
    second = relay.metadata_lookup("hf:black-forest-labs/FLUX.2-klein-4B", resolver)

    assert first == second == {"calls": 1}
    assert calls["count"] == 1
    assert relay.get_rotation_status()["dedup_hits"] == 1


def test_regressions_cost_speed_alias_and_failure_handlers() -> None:
    relay = WeaverModelRelay()
    record = relay.records["minicpm5-1b-router"]
    original_cost_hint = record.cost_hint

    speed_decision = relay.select_lane("router", strategy="speed")
    fast_decision = relay.select_lane("router", strategy="fast")
    relay.record_failure(record.model_id, "temporary provider error")
    relay.record_success(record.model_id, latency_ms=120)

    assert speed_decision.strategy == "latency_first"
    assert fast_decision.strategy == "latency_first"
    assert record.cost_hint == original_cost_hint
    assert record.failure_count == 1
    assert record.success_count == 1
    assert record.health == "healthy"


def test_context_packet_survives_video_repair_fallback() -> None:
    relay = WeaverModelRelay()
    first = relay.select_lane("video_repair", public_demo=False, strategy="private_research")
    assert first.primary is not None

    for _ in range(3):
        relay.record_failure(first.primary.model_id, "modal batch unavailable")

    fallback = relay.select_lane("video_repair", public_demo=False, strategy="private_research")

    assert fallback.primary is not None
    assert fallback.primary.model_id != first.primary.model_id
    assert fallback.context_packet.lane == "video_repair"
    assert fallback.context_packet.task == "video_repair"
    assert any("health=unhealthy" in reason for reason in fallback.skipped)


def test_dashboard_surfaces_gmr_pinned_models_and_fallbacks() -> None:
    relay = WeaverModelRelay()
    html = render_dashboard(relay_status=relay.dashboard_snapshot(public_demo=True))

    assert "GMR ModelRelay" in html
    assert "FLUX.2 9B pinned" in html
    assert "4B sidecar" in html
    assert "LocateAnything pinned" in html
    assert "fallback:" in html
    assert "Rotation Safe" in html


def test_optional_external_gateways_are_registered_but_excluded_by_default() -> None:
    relay = WeaverModelRelay()

    assert relay.records["netlify-ai-gateway-helper"].provider == "netlify"
    assert relay.records["cloudflare-agent-helper"].provider == "cloudflare"
    assert relay.records["fal-media-adapter"].provider == "fal"
    assert relay.records["netflix-void-modal"].repo_id == "netflix/void-model"
    assert relay.records["netflix-void-modal"].params_b == 5.0
    assert relay.records["netflix-void-modal"].health == "healthy"
    assert relay.records["netlify-ai-gateway-helper"].health == "excluded"
    assert relay.records["fal-media-adapter"].health == "excluded"


def test_minicpm_v46_is_registered_in_taste_judge_lane() -> None:
    relay = WeaverModelRelay()

    record = relay.records["minicpm-v46-visual-judge"]

    assert record.lane == "taste_judge"
    assert record.repo_id == "openbmb/MiniCPM-V-4.6"
    assert record.provider == "openbmb"
    assert record.params_b == 1.30
    assert record.license_gate == "apache-2.0"
    assert record.health == "healthy"


def test_nemotron_parse_is_registered_in_taste_judge_lane() -> None:
    relay = WeaverModelRelay()

    record = relay.records["nemotron-parse-v12-evidence"]

    assert record.lane == "taste_judge"
    assert record.repo_id == "nvidia/NVIDIA-Nemotron-Parse-v1.2"
    assert record.provider == "hf_nvidia"
    assert record.params_b == 0.94
    assert record.health == "healthy"


def test_nemotron_nano_is_registered_as_fallback_for_parse() -> None:
    relay = WeaverModelRelay()

    parse_record = relay.records["nemotron-parse-v12-evidence"]
    nano_record = relay.records["nemotron-nano-4b-gguf-evidence"]

    assert "nemotron-nano-4b-gguf-evidence" in (parse_record.fallback_chain or ())
    assert nano_record.repo_id == "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF"
    assert nano_record.lane == "taste_judge"
    assert nano_record.params_b == 3.97


def test_private_image_research_lane_is_rotatable() -> None:
    from nexus_visual_weaver.model_relay import PINNED_LANES, ROTATABLE_LANES

    assert "private_image_research" not in PINNED_LANES
    assert "private_image_research" in ROTATABLE_LANES


def test_flux2_klein_9b_is_pinned_quality_lane() -> None:
    relay = WeaverModelRelay()

    record = relay.records["flux2-klein-9b-quality"]

    assert record.lane == "image_generation"
    assert record.pinned is True
    assert record.params_b == 9.0
    assert record.license_gate == "review_required"
    assert record.repo_id == "black-forest-labs/FLUX.2-klein-9B"


def test_flux2_klein_4b_is_tiny_titan_sidecar() -> None:
    relay = WeaverModelRelay()

    record = relay.records["flux2-klein-4b-tiny-sidecar"]

    assert record.lane == "tiny_titan_sidecar"
    assert record.pinned is False
    assert record.params_b == 4.0
    assert record.license_gate == "apache-2.0"


def test_minicpm_has_fallback_chain_configured() -> None:
    relay = WeaverModelRelay()

    record = relay.records["minicpm-v46-visual-judge"]

    assert record.fallback_chain is not None
    assert len(record.fallback_chain) > 0
