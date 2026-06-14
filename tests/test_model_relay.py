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
    assert decision.fallbacks == []
    assert "rotation disabled" in decision.reason


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

    first = relay.metadata_lookup("hf:black-forest-labs/FLUX.2-klein-9B", resolver)
    second = relay.metadata_lookup("hf:black-forest-labs/FLUX.2-klein-9B", resolver)

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
    assert "FLUX.2 pinned" in html
    assert "LocateAnything pinned" in html
    assert "fallback:" in html
    assert "Rotation Safe" in html


def test_optional_external_gateways_are_registered_but_excluded_by_default() -> None:
    relay = WeaverModelRelay()

    assert relay.records["netlify-ai-gateway-helper"].provider == "netlify"
    assert relay.records["cloudflare-agent-helper"].provider == "cloudflare"
    assert relay.records["fal-media-adapter"].provider == "fal"
    assert relay.records["netflix-void-modal"].health == "healthy"
    assert relay.records["netlify-ai-gateway-helper"].health == "excluded"
    assert relay.records["fal-media-adapter"].health == "excluded"
