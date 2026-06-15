from PIL import Image

from nexus_visual_weaver.hf_runtime import (
    FLUX_REPO_ID,
    PRIVATE_RESEARCH_FLUX_REPO_ID,
    TINY_TITAN_FLUX_REPO_ID,
    active_flux_repo_id,
    generate_flux_image,
    hf_runtime_enabled,
)
from nexus_visual_weaver.render import render_artifact_lane


def test_hf_runtime_is_disabled_locally_by_default(monkeypatch) -> None:
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.delenv("HF_SPACE_ID", raising=False)
    monkeypatch.delenv("NEXUS_ENABLE_REAL_HF", raising=False)
    monkeypatch.delenv("NEXUS_DISABLE_REAL_HF", raising=False)

    assert hf_runtime_enabled() is False
    result = generate_flux_image("test prompt")
    assert result.status == "disabled"
    assert result.provider_state == "dry-run"
    assert result.repo_id == "black-forest-labs/FLUX.2-klein-9B"


def test_quality_and_sidecar_flux_repo_ids_are_split(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_FLUX_REPO_ID", raising=False)
    monkeypatch.delenv("NEXUS_TINY_TITAN_MODE", raising=False)

    assert FLUX_REPO_ID == "black-forest-labs/FLUX.2-klein-9B"
    assert PRIVATE_RESEARCH_FLUX_REPO_ID == "black-forest-labs/FLUX.2-klein-9B"
    assert TINY_TITAN_FLUX_REPO_ID == "black-forest-labs/FLUX.2-klein-4B"
    assert active_flux_repo_id() == FLUX_REPO_ID

    monkeypatch.setenv("NEXUS_TINY_TITAN_MODE", "1")
    assert active_flux_repo_id() == TINY_TITAN_FLUX_REPO_ID


def test_artifact_lane_embeds_generated_image() -> None:
    image_path = "outputs/test-generated-artifact.png"
    Image.new("RGB", (16, 16), color=(12, 16, 20)).save(image_path)

    html = render_artifact_lane(
        operator_state={
            "provider_state": "generated",
            "generation": {
                "status": "success",
                "output_path": str(image_path),
                "message": "FLUX.2 generated a real artifact.",
            },
        }
    )

    assert "nw-preview-real-image" in html
    assert "data:image/png;base64" in html
    assert "Real FLUX.2 Klein artifact" in html
