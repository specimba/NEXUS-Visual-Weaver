from nexus_visual_weaver.lora_adapter import load_and_apply, unload_all
from nexus_visual_weaver.schema import AdapterRecipe


class FakeLoraPipe:
    def __init__(self) -> None:
        self.loaded: list[tuple[str, dict]] = []
        self.adapters: tuple[list[str], list[float]] | None = None
        self.unloaded = False

    def load_lora_weights(self, repo_id: str, **kwargs) -> None:
        self.loaded.append((repo_id, kwargs))

    def set_adapters(self, adapter_names: list[str], adapter_weights: list[float]) -> None:
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
