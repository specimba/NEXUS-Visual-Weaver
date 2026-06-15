"""Seeded HF model and adapter catalog for the command center."""

from __future__ import annotations

from .schema import AdapterRecipe, ModelCandidate

MODEL_CATALOG: list[ModelCandidate] = [
    ModelCandidate(
        repo_id="black-forest-labs/FLUX.2-klein-4B",
        role="tiny_titan_sidecar_image_generator",
        task="image-to-image",
        params_b=4.0,
        runtime="diffusers / provider",
        license="apache-2.0",
        source_url="https://hf.co/black-forest-labs/FLUX.2-klein-4B",
    ),
    ModelCandidate(
        repo_id="black-forest-labs/FLUX.2-klein-9B",
        role="quality_image_generator",
        task="image-to-image",
        params_b=9.0,
        runtime="diffusers / gated provider",
        license="other",
        gated=True,
        source_url="https://hf.co/black-forest-labs/FLUX.2-klein-9B",
    ),
    ModelCandidate(
        repo_id="Brunobkr/OFFELLIA_Q4_0_gemma-4-12B-it.gguf",
        role="private_research_multimodal_judge",
        task="image-text-to-text",
        params_b=12.0,
        runtime="llama.cpp GGUF",
        license="apache-2.0",
        public_demo=False,
        source_url="https://hf.co/Brunobkr/OFFELLIA_Q4_0_gemma-4-12B-it.gguf",
    ),
    ModelCandidate(
        repo_id="nvidia/LocateAnything-3B",
        role="visual_grounding",
        task="image-text-to-text",
        params_b=3.83,
        runtime="transformers",
        license="other",
        source_url="https://hf.co/nvidia/LocateAnything-3B",
    ),
    ModelCandidate(
        repo_id="openbmb/MiniCPM-V-4.6",
        role="sponsor_visual_judge",
        task="image-text-to-text",
        params_b=1.30,
        runtime="OpenAI-compatible API / transformers",
        license="apache-2.0",
        source_url="https://hf.co/openbmb/MiniCPM-V-4.6",
    ),
    ModelCandidate(
        repo_id="nvidia/NVIDIA-Nemotron-Parse-v1.2",
        role="sponsor_structured_parse",
        task="image-text-to-text",
        params_b=0.94,
        runtime="provider API / transformers",
        license="other",
        source_url="https://hf.co/nvidia/NVIDIA-Nemotron-Parse-v1.2",
    ),
    ModelCandidate(
        repo_id="openbmb/MiniCPM5-1B",
        role="router",
        task="text-generation / tool-calling",
        params_b=1.08,
        runtime="transformers",
        license="apache-2.0",
        source_url="https://hf.co/openbmb/MiniCPM5-1B",
    ),
    ModelCandidate(
        repo_id="onnx-community/functiongemma-270m-it-ONNX",
        role="fallback_router",
        task="text-generation",
        params_b=0.27,
        runtime="transformers.js / ONNX",
        license="gemma",
        source_url="https://hf.co/onnx-community/functiongemma-270m-it-ONNX",
    ),
    ModelCandidate(
        repo_id="Brunobkr/OFFELLIA_IQ4_XS_gemma-4-12B-it-heretic",
        role="adult_mode_text_judge",
        task="text-generation",
        params_b=12.0,
        runtime="llama.cpp GGUF",
        license="other",
        adult_only=True,
        source_url="https://hf.co/Brunobkr/OFFELLIA_IQ4_XS_gemma-4-12B-it-heretic",
    ),
    ModelCandidate(
        repo_id="Wan-AI/Wan2.2-I2V-A14B-Diffusers",
        role="video_swap_preset",
        task="image-to-video",
        params_b=14.0,
        runtime="diffusers / provider",
        license="apache-2.0",
        source_url="https://hf.co/Wan-AI/Wan2.2-I2V-A14B-Diffusers",
    ),
    ModelCandidate(
        repo_id="Lightricks/LTX-2.3",
        role="video_swap_preset",
        task="image-to-video",
        params_b=22.0,
        runtime="diffusers",
        license="other",
        source_url="https://hf.co/Lightricks/LTX-2.3",
    ),
]

ADAPTER_CATALOG: list[AdapterRecipe] = [
    AdapterRecipe(
        repo_id="DeverStyle/Flux.2-Klein-Loras",
        adapter_for="black-forest-labs/FLUX.2-klein-4B",
        task="text-to-image style stack",
        license="apache-2.0",
    ),
    AdapterRecipe(
        repo_id="fal/flux-2-klein-4B-outpaint-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-4B",
        task="outpaint/inpaint public demo helper",
        license="apache-2.0",
    ),
    AdapterRecipe(
        repo_id="thedeoxen/refcontrol-FLUX.2-klein-4B-reference-depth-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-base-4B",
        task="reference-depth control for garment layout",
        license="apache-2.0",
    ),
    AdapterRecipe(
        repo_id="nomadoor/flux-2-klein-9B-schematic-lora",
        adapter_for="black-forest-labs/FLUX.2-klein-base-9B",
        task="pose/depth/segmentation schematic control",
        license="other",
    ),
    AdapterRecipe(
        repo_id="fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA",
        adapter_for="Qwen/Qwen-Image-Edit-2511",
        task="camera-angle edit",
        license="apache-2.0",
    ),
    AdapterRecipe(
        repo_id="joyfox/LTX-2.3-Transition-LORA",
        adapter_for="Lightricks/LTX-2.3",
        task="image-to-video transition",
        license="apache-2.0",
    ),
    AdapterRecipe(
        repo_id="LiconStudio/Ltx2.3-VBVR-lora-I2V",
        adapter_for="Lightricks/LTX-2.3",
        task="video reasoning / I2V",
        license="other",
    ),
    AdapterRecipe(
        repo_id="ScottzillaSystems/qwen-image-edit-plus-nsfw-lora",
        adapter_for="Qwen/Qwen-Image-Edit-2511",
        task="adult image edit catalog entry",
        license="openrail++",
        adult_only=True,
    ),
    AdapterRecipe(
        repo_id="lopi999/Wan2.2-I2V_General-NSFW-LoRA",
        adapter_for="Wan-AI/Wan2.2-I2V-A14B",
        task="adult video adapter catalog entry",
        license="unknown",
        adult_only=True,
    ),
]

DEFAULT_ACTIVE_STACK = [
    "black-forest-labs/FLUX.2-klein-9B",
    "nvidia/LocateAnything-3B",
    "openbmb/MiniCPM-V-4.6",
    "nvidia/NVIDIA-Nemotron-Parse-v1.2",
    "openbmb/MiniCPM5-1B",
    "onnx-community/functiongemma-270m-it-ONNX",
]

PRIVATE_RESEARCH_STACK = [
    "black-forest-labs/FLUX.2-klein-9B",
    "Brunobkr/OFFELLIA_Q4_0_gemma-4-12B-it.gguf",
    "nvidia/LocateAnything-3B",
    "openbmb/MiniCPM-V-4.6",
    "nvidia/NVIDIA-Nemotron-Parse-v1.2",
    "openbmb/MiniCPM5-1B",
]


def filter_catalog(adult_mode: bool = False) -> tuple[list[ModelCandidate], list[AdapterRecipe]]:
    models = [
        model
        for model in MODEL_CATALOG
        if (adult_mode or not model.adult_only) and (adult_mode or model.public_demo)
    ]
    adapters = [adapter for adapter in ADAPTER_CATALOG if adult_mode or not adapter.adult_only]
    return models, adapters


def active_stack(adult_mode: bool = False) -> list[ModelCandidate]:
    allowed, _ = filter_catalog(adult_mode)
    by_id = {model.repo_id: model for model in allowed}
    stack_ids = PRIVATE_RESEARCH_STACK if adult_mode else DEFAULT_ACTIVE_STACK
    return [by_id[repo_id] for repo_id in stack_ids if repo_id in by_id]


def parameter_budget(stack: list[ModelCandidate] | None = None) -> dict[str, float | str]:
    chosen = stack or active_stack(False)
    total = round(sum(model.params_b for model in chosen), 2)
    return {
        "active_b": total,
        "limit_b": 32.0,
        "remaining_b": round(32.0 - total, 2),
        "status": "pass" if total <= 32.0 else "over_budget",
    }


def catalog_summary(adult_mode: bool = False) -> dict[str, int | float | str]:
    models, adapters = filter_catalog(adult_mode)
    budget = parameter_budget(active_stack(adult_mode))
    return {
        "models_visible": len(models),
        "adapters_visible": len(adapters),
        "adult_catalog": "enabled" if adult_mode else "hidden",
        **budget,
    }
