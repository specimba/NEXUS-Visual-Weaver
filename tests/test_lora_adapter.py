from nexus_visual_weaver.lora_adapter import (
    _short_error,
    _status,
    adapter_to_dict,
    is_compatible,
    load_and_apply,
    unload_all,
)
from nexus_visual_weaver.schema import AdapterRecipe


class FakeLoraPipe:
    def __init__(self) -> None:
        self.loaded: list[tuple[str, dict]] = []
        self.adapters: tuple[list[str], list[float]] | None = None
        self.unloaded = False

    def load_lora_weights(self, repo_id: str, **kwargs) -> None:
        """
        Record a call to load LoRA weights for later assertion in tests.
        """
        self.loaded.append((repo_id, kwargs))

    def set_adapters(self, adapter_names: list[str], adapter_weights: list[float]) -> None:
        """
        Store adapter names and their corresponding weights for later inspection.
        """
        self.adapters = (adapter_names, adapter_weights)

    def unload_lora_weights(self) -> None:
        self.unloaded = True


class FailingLoraPipe(FakeLoraPipe):
    def load_lora_weights(self, repo_id: str, **kwargs) -> None:
        raise RuntimeError("adapter load failed")


class UnsupportedPipe:
    pass


def test_load_and_apply_reports_loaded_for_compatible_pipe() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
        weight=0.6,
    )
    pipe = FakeLoraPipe()

    result = load_and_apply(pipe, recipe, "black-forest-labs/FLUX.2-klein-9B")

    assert result["status"] == "loaded"
    assert result["repo_id"] == "example/style-lora"
    assert pipe.loaded == [("example/style-lora", {"adapter_name": "nexus_style"})]
    assert pipe.adapters == (["nexus_style"], [0.6])


def test_load_and_apply_reports_skipped_for_incompatible_adapter() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-4B",
        task="style",
    )

    result = load_and_apply(FakeLoraPipe(), recipe, "black-forest-labs/FLUX.2-klein-9B")

    assert result["status"] == "skipped_incompatible"
    assert "not declared compatible" in result["message"]


def test_load_and_apply_reports_unsupported_pipeline() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
    )

    result = load_and_apply(UnsupportedPipe(), recipe, "black-forest-labs/FLUX.2-klein-9B")

    assert result["status"] == "unsupported_pipeline"


def test_load_and_apply_reports_failed_without_raising() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
    )

    result = load_and_apply(FailingLoraPipe(), recipe, "black-forest-labs/FLUX.2-klein-9B")

    assert result["status"] == "failed"
    assert "RuntimeError" in result["message"]


def test_unload_all_uses_pipeline_unload_hook() -> None:
    pipe = FakeLoraPipe()

    unload_all(pipe)

    assert pipe.unloaded is True


def test_unload_all_handles_pipes_without_unload_method() -> None:
    # UnsupportedPipe has no unload_lora_weights method, should not raise
    pipe = UnsupportedPipe()
    unload_all(pipe)  # Should complete without error


def test_unload_all_silences_exceptions() -> None:
    class RaisingPipe:
        def unload_lora_weights(self) -> None:
            raise RuntimeError("unload failed")

    unload_all(RaisingPipe())  # Should not raise


# --- _status tests ---

def test_status_returns_dict_with_status_field() -> None:
    result = _status("disabled")

    assert result["status"] == "disabled"
    assert result["repo_id"] is None
    assert result["adapter_for"] is None
    assert result["weight"] is None


def test_status_with_recipe_extracts_recipe_fields() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
        weight=0.6,
    )
    result = _status("loaded", recipe)

    assert result["repo_id"] == "example/style-lora"
    assert result["adapter_for"] == "black-forest-labs/FLUX.2-klein-9B"
    assert result["weight"] == 0.6


def test_status_with_extra_kwargs_included() -> None:
    result = _status("loaded", message="Adapter applied.", adapter_name="nexus_style")

    assert result["message"] == "Adapter applied."
    assert result["adapter_name"] == "nexus_style"


# --- _short_error tests ---

def test_lora_short_error_includes_class_name() -> None:
    exc = ValueError("bad input")
    result = _short_error(exc)

    assert result.startswith("ValueError:")
    assert "bad input" in result


def test_lora_short_error_truncates_at_240() -> None:
    exc = RuntimeError("x" * 300)
    result = _short_error(exc)

    # Should be truncated
    assert len(result) <= len("RuntimeError: ") + 240
    assert result.endswith("...")


def test_lora_short_error_collapses_newlines() -> None:
    exc = OSError("line one\nline two")
    result = _short_error(exc)

    assert "\n" not in result
    assert "line one" in result


# --- adapter_to_dict tests ---

def test_adapter_to_dict_returns_complete_dict() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
        weight=0.75,
        license="apache-2.0",
    )
    result = adapter_to_dict(recipe)

    assert result["repo_id"] == "example/style-lora"
    assert result["adapter_for"] == "black-forest-labs/FLUX.2-klein-9B"
    assert result["task"] == "style"
    assert result["weight"] == 0.75
    assert result["license"] == "apache-2.0"
    assert isinstance(result, dict)


def test_adapter_to_dict_includes_all_fields() -> None:
    recipe = AdapterRecipe(
        repo_id="example/adult-lora",
        adapter_for="model/base",
        task="style",
        adult_only=True,
        requires_image=True,
        runtime_enabled=False,
    )
    result = adapter_to_dict(recipe)

    assert result["adult_only"] is True
    assert result["requires_image"] is True
    assert result["runtime_enabled"] is False


# --- is_compatible tests ---

def test_is_compatible_returns_true_for_matching_adapter() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
    )
    pipe = FakeLoraPipe()

    assert is_compatible(pipe, recipe, "black-forest-labs/FLUX.2-klein-9B") is True


def test_is_compatible_returns_false_for_runtime_disabled() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
        runtime_enabled=False,
    )
    pipe = FakeLoraPipe()

    assert is_compatible(pipe, recipe, "black-forest-labs/FLUX.2-klein-9B") is False


def test_is_compatible_returns_false_for_adult_only_without_adult_mode() -> None:
    recipe = AdapterRecipe(
        repo_id="example/adult-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
        adult_only=True,
    )
    pipe = FakeLoraPipe()

    assert is_compatible(pipe, recipe, "black-forest-labs/FLUX.2-klein-9B", adult_mode=False) is False


def test_is_compatible_returns_true_for_adult_only_with_adult_mode() -> None:
    recipe = AdapterRecipe(
        repo_id="example/adult-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
        adult_only=True,
    )
    pipe = FakeLoraPipe()

    assert is_compatible(pipe, recipe, "black-forest-labs/FLUX.2-klein-9B", adult_mode=True) is True


def test_is_compatible_returns_false_for_requires_image() -> None:
    recipe = AdapterRecipe(
        repo_id="example/inpaint-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-4B",
        task="inpaint",
        requires_image=True,
    )
    pipe = FakeLoraPipe()

    assert is_compatible(pipe, recipe, "black-forest-labs/FLUX.2-klein-4B") is False


def test_is_compatible_returns_false_for_pipeline_without_lora_support() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
    )

    assert is_compatible(UnsupportedPipe(), recipe, "black-forest-labs/FLUX.2-klein-9B") is False


def test_is_compatible_returns_false_for_incompatible_target() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
    )
    pipe = FakeLoraPipe()

    assert is_compatible(pipe, recipe, "completely/different-model") is False


def test_is_compatible_returns_true_for_compatible_repo_ids() -> None:
    recipe = AdapterRecipe(
        repo_id="example/style-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
        compatible_repo_ids=["black-forest-labs/FLUX.2-klein-4B"],
    )
    pipe = FakeLoraPipe()

    assert is_compatible(pipe, recipe, "black-forest-labs/FLUX.2-klein-4B") is True


# --- load_and_apply with adult_only recipe tests ---

def test_load_and_apply_skips_adult_only_in_non_adult_mode() -> None:
    recipe = AdapterRecipe(
        repo_id="example/adult-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
        adult_only=True,
    )
    pipe = FakeLoraPipe()

    result = load_and_apply(pipe, recipe, "black-forest-labs/FLUX.2-klein-9B", adult_mode=False)

    assert result["status"] == "skipped_incompatible"
    assert "Adult Mode is off" in result["message"]


def test_load_and_apply_loads_adult_only_in_adult_mode() -> None:
    recipe = AdapterRecipe(
        repo_id="example/adult-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
        adult_only=True,
    )
    pipe = FakeLoraPipe()

    result = load_and_apply(pipe, recipe, "black-forest-labs/FLUX.2-klein-9B", adult_mode=True)

    assert result["status"] == "loaded"


def test_load_and_apply_skips_requires_image_adapter() -> None:
    recipe = AdapterRecipe(
        repo_id="example/inpaint-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-4B",
        task="inpaint",
        requires_image=True,
    )
    pipe = FakeLoraPipe()

    result = load_and_apply(pipe, recipe, "black-forest-labs/FLUX.2-klein-4B")

    assert result["status"] == "skipped_incompatible"
    assert "image-conditioning" in result["message"]


def test_load_and_apply_uses_weight_name_when_present() -> None:
    recipe = AdapterRecipe(
        repo_id="example/weight-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-9B",
        task="style",
        weight_name="style_weights.safetensors",
    )
    pipe = FakeLoraPipe()

    load_and_apply(pipe, recipe, "black-forest-labs/FLUX.2-klein-9B")

    assert len(pipe.loaded) == 1
    _, kwargs = pipe.loaded[0]
    assert kwargs.get("weight_name") == "style_weights.safetensors"


def test_load_and_apply_no_recipe_returns_disabled() -> None:
    pipe = FakeLoraPipe()

    result = load_and_apply(pipe, None, "any/model")

    assert result["status"] == "disabled"
    assert result["repo_id"] is None
