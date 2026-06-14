from PIL import Image

from nexus_visual_weaver.hf_runtime import generate_flux_image, hf_runtime_enabled
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
