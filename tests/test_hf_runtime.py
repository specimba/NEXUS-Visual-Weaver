import pytest
from PIL import Image

from nexus_visual_weaver.hf_runtime import FLUX_REPO_ID, HFGenerationResult, generate_flux_image, hf_runtime_enabled
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


def test_hf_runtime_enabled_when_nexus_enable_flag_set(monkeypatch) -> None:
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.delenv("HF_SPACE_ID", raising=False)
    monkeypatch.delenv("NEXUS_DISABLE_REAL_HF", raising=False)
    monkeypatch.setenv("NEXUS_ENABLE_REAL_HF", "1")

    assert hf_runtime_enabled() is True


def test_nexus_disable_flag_overrides_space_id(monkeypatch) -> None:
    monkeypatch.setenv("SPACE_ID", "some-org/my-space")
    monkeypatch.setenv("NEXUS_DISABLE_REAL_HF", "1")
    monkeypatch.delenv("NEXUS_ENABLE_REAL_HF", raising=False)

    assert hf_runtime_enabled() is False


def test_hf_runtime_enabled_by_space_id(monkeypatch) -> None:
    monkeypatch.setenv("SPACE_ID", "org/nexus-visual-weaver")
    monkeypatch.delenv("HF_SPACE_ID", raising=False)
    monkeypatch.delenv("NEXUS_ENABLE_REAL_HF", raising=False)
    monkeypatch.delenv("NEXUS_DISABLE_REAL_HF", raising=False)

    assert hf_runtime_enabled() is True


def test_hf_runtime_enabled_by_hf_space_id(monkeypatch) -> None:
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.setenv("HF_SPACE_ID", "org/nexus-visual-weaver")
    monkeypatch.delenv("NEXUS_ENABLE_REAL_HF", raising=False)
    monkeypatch.delenv("NEXUS_DISABLE_REAL_HF", raising=False)

    assert hf_runtime_enabled() is True


def test_hf_generation_result_to_dict_contains_all_fields(monkeypatch) -> None:
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.delenv("HF_SPACE_ID", raising=False)
    monkeypatch.delenv("NEXUS_ENABLE_REAL_HF", raising=False)
    monkeypatch.delenv("NEXUS_DISABLE_REAL_HF", raising=False)

    result = generate_flux_image("test prompt")
    d = result.to_dict()

    assert d["status"] == "disabled"
    assert d["provider_state"] == "dry-run"
    assert d["repo_id"] == FLUX_REPO_ID
    assert d["output_path"] is None
    assert "message" in d
    assert d["latency_seconds"] is None
    assert d["width"] == 1024
    assert d["height"] == 1024
    assert d["steps"] == 4
    assert "hf_token_present" in d


def test_generate_flux_image_passes_custom_dimensions_in_disabled_mode(monkeypatch) -> None:
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.delenv("HF_SPACE_ID", raising=False)
    monkeypatch.delenv("NEXUS_ENABLE_REAL_HF", raising=False)
    monkeypatch.delenv("NEXUS_DISABLE_REAL_HF", raising=False)

    result = generate_flux_image("custom dimensions", width=512, height=768, steps=8)

    assert result.width == 512
    assert result.height == 768
    assert result.steps == 8
    assert result.status == "disabled"


def test_generate_flux_image_reflects_hf_token_presence(monkeypatch) -> None:
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.delenv("HF_SPACE_ID", raising=False)
    monkeypatch.delenv("NEXUS_ENABLE_REAL_HF", raising=False)
    monkeypatch.delenv("NEXUS_DISABLE_REAL_HF", raising=False)
    monkeypatch.setenv("HF_TOKEN", "hf_test_token_value")

    result = generate_flux_image("test prompt with token")

    assert result.hf_token_present is True


def test_generate_flux_image_no_hf_token(monkeypatch) -> None:
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.delenv("HF_SPACE_ID", raising=False)
    monkeypatch.delenv("NEXUS_ENABLE_REAL_HF", raising=False)
    monkeypatch.delenv("NEXUS_DISABLE_REAL_HF", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)

    result = generate_flux_image("test prompt without token")

    assert result.hf_token_present is False
    assert result.status == "disabled"


def test_hf_generation_result_is_frozen() -> None:
    result = HFGenerationResult(
        status="disabled",
        provider_state="dry-run",
        repo_id=FLUX_REPO_ID,
    )
    with pytest.raises((AttributeError, TypeError)):
        result.status = "changed"  # type: ignore[misc]


def test_artifact_lane_shows_placeholder_without_image_path() -> None:
    html = render_artifact_lane(
        operator_state={
            "provider_state": "dry-run",
            "generation": {
                "status": "disabled",
                "output_path": None,
                "message": "dry-run",
            },
        }
    )

    assert "nw-preview-image" in html
    assert "nw-preview-real-image" not in html
    assert "Deterministic Raven Chronicle proof frame" in html


def test_artifact_lane_shows_placeholder_for_missing_image_file() -> None:
    html = render_artifact_lane(
        operator_state={
            "provider_state": "dry-run",
            "generation": {
                "status": "disabled",
                "output_path": "/nonexistent/path/to/image.png",
                "message": "dry-run",
            },
        }
    )

    assert "nw-preview-real-image" not in html
    assert "data:image" not in html
