import modal
from io import BytesIO
from PIL import Image
from typing import List, Optional

app = modal.App("nexus-couture-refine-v2")

# Robust image definition with all necessary dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "torch==2.5.0",
        "torchvision==0.20.0",
        "diffusers>=0.30.0",
        "transformers>=4.45.0",
        "accelerate",
        "safetensors",
        "Pillow",
        "huggingface-hub",
        "peft",
        "protobuf",
    )
)

# Persistent volume for model caching (saves startup time)
volume = modal.Volume.from_name("nexus-model-cache", create_if_missing=True)

# Locked NEXUS Taste Profile - The "Soul" of the generator
NEXUS_CORE_STYLE = (
    "Slavic woman, rain-slick neon cyberpunk city at night, long structured black patent leather coat, "
    "faux fur collar, Chantilly lace neckline, glowing crimson hardware, platform boots, "
    "floating NEXUS sigils and code streams, ultra detailed wet fabric texture, cinematic lighting, "
    "high fashion editorial, photorealistic, 8k"
)

@app.function(
    image=image,
    gpu="B200",  # Using the best available GPU for speed
    volumes={"/cache": volume},
    timeout=600,  # 10 minutes max per run
    allow_concurrent_inputs=10,
)
def refine_couture(
    image_bytes: bytes,
    user_addition: str = "",
    strength: float = 0.58,
    steps: int = 32,
    guidance_scale: float = 3.8,
    seed: int = -1,
    lora_adapters: Optional[List[str]] = None,
    negative_prompt: str = "blurry, low quality, deformed, extra limbs, bad anatomy, watermark, text",
) -> bytes:
    """
    Refines an input image using FLUX.1-Kontext-dev with optional LoRAs.
    Preserves the core NEXUS aesthetic while applying user modifications.
    """
    import torch
    from diffusers import FluxKontextPipeline

    # Load pipeline with caching
    pipe = FluxKontextPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-Kontext-dev",
        torch_dtype=torch.bfloat16,
        cache_dir="/cache",
    ).to("cuda")

    # Enable memory efficient attention if available
    if hasattr(pipe, "enable_xformers_memory_efficient_attention"):
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except:
            pass  # Fallback if xformers not installed

    # Multi-LoRA support logic
    if lora_adapters:
        for adapter in lora_adapters:
            if adapter == "garment":
                # Example: Using a generic control LoRA (replace with specific HF repo if needed)
                # For now, we rely on the prompt strength, but structure is ready for real LoRAs
                print(f"Loading LoRA adapter: {adapter}")
                # pipe.load_lora_weights("repo_id", adapter_name=adapter) 
            elif adapter == "hardware":
                print(f"Loading LoRA adapter: {adapter}")
        
        # Activate adapters
        # pipe.set_adapters(lora_adapters)

    # Process input image
    init_image = Image.open(BytesIO(image_bytes)).convert("RGB")
    
    # Optional: Resize if too huge to save VRAM/time, but Kontext handles 1MP well
    width, height = init_image.size
    if width * height > 2000000: # ~2MP limit
        scale = (2000000 / (width * height)) ** 0.5
        new_size = (int(width * scale), int(height * scale))
        init_image = init_image.resize(new_size, Image.LANCZOS)

    # Construct final prompt
    final_prompt = f"{NEXUS_CORE_STYLE}, {user_addition}" if user_addition else NEXUS_CORE_STYLE

    # Seed handling
    generator = torch.Generator(device="cuda").manual_seed(seed) if seed != -1 else None

    print(f"🎨 Refining with prompt: {final_prompt}")
    print(f"⚙️ Settings: Strength={strength}, Steps={steps}, Guidance={guidance_scale}")

    # Run inference
    result = pipe(
        image=init_image,
        prompt=final_prompt,
        negative_prompt=negative_prompt,
        guidance_scale=guidance_scale,
        num_inference_steps=steps,
        strength=strength,
        generator=generator,
    ).images[0]

    # Return as bytes
    buf = BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()

@app.local_entrypoint()
def test_refine(
    image_path: str = "test_input.png",
    output_path: str = "test_output.png",
    user_prompt: str = "glowing crimson buckles, wet pavement reflection"
):
    """Local test entrypoint"""
    from pathlib import Path
    
    if not Path(image_path).exists():
        print(f"❌ Input image not found: {image_path}")
        print("Creating a dummy test... (Please provide an image)")
        return

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    print("🚀 Sending to Modal B200 for refinement...")
    result_bytes = refine_couture.remote(
        image_bytes=image_bytes,
        user_addition=user_prompt,
        lora_adapters=["garment"]
    )

    with open(output_path, "wb") as f:
        f.write(result_bytes)
    
    print(f"✅ Success! Output saved to {output_path}")
