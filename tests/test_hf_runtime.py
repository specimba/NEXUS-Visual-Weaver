from PIL import Image
from pathlib import Path
import types

import nexus_visual_weaver.hf_runtime as hf_runtime
from nexus_visual_weaver.hf_runtime import (
    FLUX_REPO_ID,
    PRIVATE_RESEARCH_FLUX_REPO_ID,
    TINY_TITAN_FLUX_REPO_ID,
    _PIPELINE_CACHE,
    _adapter_recipe,
    _repo_candidates,
    active_flux_repo_id,
    default_lora_repo_id,
    generate_flux_image,
    hf_runtime_enabled,
)
from nexus_visual_weaver.render import render_artifact_lane


RUNTIME_FIXTURE_DIR = Path("tests/fixtures/runtime")


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
    assert result.lora_status == "disabled"
    assert result.lora_repo_id == "DeverStyle/Flux.2-Klein-Loras"


def test_flux_repo_ids_use_9b_with_4b_sidecar() -> None:
    assert FLUX_REPO_ID == "black-forest-labs/FLUX.2-klein-9B"
    assert PRIVATE_RESEARCH_FLUX_REPO_ID == "black-forest-labs/FLUX.2-klein-9B"
    assert TINY_TITAN_FLUX_REPO_ID == "black-forest-labs/FLUX.2-klein-4B"


def test_default_lora_repo_id_prefers_runtime_enabled_compatible_adapter() -> None:
    assert default_lora_repo_id("black-forest-labs/FLUX.2-klein-9B") == "DeverStyle/Flux.2-Klein-Loras"


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


# --- active_flux_repo_id tests ---

def test_active_flux_repo_id_defaults_to_9b(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_FLUX_REPO_ID", raising=False)
    monkeypatch.delenv("NEXUS_TINY_TITAN_MODE", raising=False)

    assert active_flux_repo_id() == FLUX_REPO_ID


def test_active_flux_repo_id_returns_tiny_titan_when_mode_set(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_FLUX_REPO_ID", raising=False)
    monkeypatch.setenv("NEXUS_TINY_TITAN_MODE", "1")

    assert active_flux_repo_id() == TINY_TITAN_FLUX_REPO_ID


def test_active_flux_repo_id_returns_configured_repo_id(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_FLUX_REPO_ID", "custom/flux-model")
    monkeypatch.delenv("NEXUS_TINY_TITAN_MODE", raising=False)

    assert active_flux_repo_id() == "custom/flux-model"


def test_active_flux_repo_id_configured_env_overrides_tiny_titan(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_FLUX_REPO_ID", "custom/flux-model")
    monkeypatch.setenv("NEXUS_TINY_TITAN_MODE", "1")

    # Configured env takes precedence over TINY_TITAN_MODE
    assert active_flux_repo_id() == "custom/flux-model"


# --- _repo_candidates tests ---

def test_repo_candidates_includes_primary_and_tiny_titan_fallback(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_DISABLE_TINY_TITAN_FALLBACK", raising=False)

    candidates = _repo_candidates(FLUX_REPO_ID)

    assert candidates[0] == FLUX_REPO_ID
    assert TINY_TITAN_FLUX_REPO_ID in candidates
    assert len(candidates) == 2


def test_repo_candidates_only_primary_when_tiny_titan_is_primary(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_DISABLE_TINY_TITAN_FALLBACK", raising=False)

    candidates = _repo_candidates(TINY_TITAN_FLUX_REPO_ID)

    assert candidates == [TINY_TITAN_FLUX_REPO_ID]


def test_repo_candidates_only_primary_when_fallback_disabled(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_DISABLE_TINY_TITAN_FALLBACK", "1")

    candidates = _repo_candidates(FLUX_REPO_ID)

    assert candidates == [FLUX_REPO_ID]


def test_repo_candidates_first_is_always_primary(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_DISABLE_TINY_TITAN_FALLBACK", raising=False)

    for repo_id in [FLUX_REPO_ID, "other/model"]:
        candidates = _repo_candidates(repo_id)
        assert candidates[0] == repo_id


# --- _adapter_recipe tests ---

def test_adapter_recipe_returns_none_for_none_input() -> None:
    assert _adapter_recipe(None) is None


def test_adapter_recipe_returns_none_for_unknown_repo_id() -> None:
    assert _adapter_recipe("nonexistent/unknown-repo") is None


def test_adapter_recipe_returns_recipe_for_known_repo_id() -> None:
    result = _adapter_recipe("DeverStyle/Flux.2-Klein-Loras")

    assert result is not None
    assert result.repo_id == "DeverStyle/Flux.2-Klein-Loras"


def test_adapter_recipe_returns_recipe_for_4b_outpaint() -> None:
    result = _adapter_recipe("fal/flux-2-klein-4B-outpaint-lora")

    assert result is not None
    assert result.requires_image is True


# --- HFGenerationResult disabled path lora fields tests ---

def test_generate_flux_image_disabled_includes_lora_repo_id(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_DISABLE_REAL_HF", "1")
    monkeypatch.delenv("NEXUS_FLUX_REPO_ID", raising=False)
    monkeypatch.delenv("NEXUS_TINY_TITAN_MODE", raising=False)

    result = generate_flux_image("test prompt")

    assert result.status == "disabled"
    assert result.lora_status == "disabled"
    # Default lora_repo_id should be the DeverStyle adapter for the 9B model
    assert result.lora_repo_id == "DeverStyle/Flux.2-Klein-Loras"


def test_generate_flux_image_disabled_includes_fallback_used_false(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_DISABLE_REAL_HF", "1")

    result = generate_flux_image("test prompt")

    assert result.fallback_used is False
    assert result.primary_error is None


def test_generate_flux_image_tiny_titan_mode_uses_4b_repo_id(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_DISABLE_REAL_HF", "1")
    monkeypatch.setenv("NEXUS_TINY_TITAN_MODE", "1")

    result = generate_flux_image("test prompt")

    assert result.status == "disabled"
    assert result.repo_id == TINY_TITAN_FLUX_REPO_ID


def test_generate_flux_image_disabled_uses_lora_message() -> None:
    import os
    os.environ["NEXUS_DISABLE_REAL_HF"] = "1"
    try:
        result = generate_flux_image("test prompt")
        assert "LoRA loading requires" in result.lora_message
    finally:
        del os.environ["NEXUS_DISABLE_REAL_HF"]


# --- default_lora_repo_id tests ---

def test_default_lora_repo_id_returns_none_for_unknown_model() -> None:
    result = default_lora_repo_id("unknown/nonexistent-model")
    assert result is None


def test_default_lora_repo_id_excludes_requires_image_adapters() -> None:
    # fal/flux-2-klein-4B-outpaint-lora requires_image=True, so it should be excluded
    result = default_lora_repo_id("black-forest-labs/FLUX.2-klein-4B")
    # DeverStyle/Flux.2-Klein-Loras is compatible with 4B via compatible_repo_ids
    assert result is not None
    recipe_result = _adapter_recipe(result)
    assert recipe_result is not None
    assert recipe_result.requires_image is False


def test_generate_flux_image_reports_sidecar_fallback(monkeypatch) -> None:
    class FakeCuda:
        @staticmethod
        def is_available() -> bool:
            return True

    class FakeGenerator:
        def __init__(self, device):
            self.device = device

        def manual_seed(self, seed):
            self.seed = seed
            return self

    fake_torch = types.SimpleNamespace(cuda=FakeCuda(), bfloat16="bfloat16", Generator=FakeGenerator)

    class FakePipeline:
        @classmethod
        def from_pretrained(cls, repo_id, torch_dtype=None, token=None):
            if repo_id == FLUX_REPO_ID:
                raise RuntimeError("primary denied")
            return cls(repo_id)

        def __init__(self, repo_id):
            self.repo_id = repo_id

        def enable_model_cpu_offload(self):
            return None

        def set_progress_bar_config(self, disable):
            self.progress_disabled = disable

        def __call__(self, **kwargs):
            return types.SimpleNamespace(images=[Image.new("RGB", (8, 8), color=(2, 4, 6))])

    fake_diffusers = types.SimpleNamespace(Flux2KleinPipeline=FakePipeline)
    monkeypatch.setitem(__import__("sys").modules, "torch", fake_torch)
    monkeypatch.setitem(__import__("sys").modules, "diffusers", fake_diffusers)
    monkeypatch.setenv("NEXUS_ENABLE_REAL_HF", "1")
    monkeypatch.delenv("NEXUS_DISABLE_REAL_HF", raising=False)
    monkeypatch.delenv("NEXUS_DISABLE_TINY_TITAN_FALLBACK", raising=False)
    output_dir = RUNTIME_FIXTURE_DIR / "hf-output"
    output_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUS_OUTPUT_DIR", str(output_dir))
    monkeypatch.setattr(hf_runtime, "load_and_apply", lambda pipe, recipe, repo_id, adult_mode=False: {"status": "disabled", "repo_id": None, "message": "fake"})
    monkeypatch.setattr(hf_runtime, "unload_all", lambda pipe: None)
    _PIPELINE_CACHE.clear()

    try:
        result = generate_flux_image("prompt", seed=7)
    finally:
        for artifact in output_dir.glob("nexus_flux_*_7.png"):
            artifact.unlink(missing_ok=True)

    assert result.status == "success"
    assert result.repo_id == TINY_TITAN_FLUX_REPO_ID
    assert result.fallback_used is True
    assert result.primary_error is not None
    assert "primary denied" in result.primary_error
    assert result.output_path is not None
