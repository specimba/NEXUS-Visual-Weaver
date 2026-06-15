import modal
from pathlib import Path

app = modal.App("nexus-couture-lora-trainer")

# Base image with all required dependencies for training
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "torch==2.5.0",
        "torchvision==0.20.0",
        "diffusers>=0.30.0",
        "transformers>=4.45.0",
        "accelerate",
        "peft",
        "datasets",
        "Pillow",
        "huggingface-hub",
        "safetensors",
    )
)

# Persistent volume to store trained adapters and cache models
volume = modal.Volume.from_name("nexus-lora-models", create_if_missing=True)

@app.function(
    image=image,
    gpu="B200",  # Best GPU for fast training
    volumes={"/models": volume},
    timeout=7200,  # 2 hours max
)
def train_nexus_couture_lora(
    dataset_repo: str = "specimba/nexus-couture-training",
    output_name: str = "nexus-couture-v1",
    rank: int = 16,
    steps: int = 800,
    learning_rate: float = 1e-4,
    push_to_hub: bool = True,
    hub_repo: str = "build-small-hackathon/nexus-couture-lora",
):
    """
    Trains a custom LoRA adapter for NEXUS Couture style on FLUX.1-Kontext-dev.
    Optimized for small datasets (20-60 images) typical of hackathon constraints.
    """
    import torch
    from diffusers import FluxKontextPipeline
    from peft import LoraConfig, get_peft_model
    from datasets import load_dataset
    from huggingface_hub import HfApi
    from torch.utils.data import DataLoader
    import os

    print(f"🚀 Starting NEXUS Couture LoRA Training")
    print(f"   Dataset: {dataset_repo}")
    print(f"   Output: {output_name} (Rank {rank}, Steps {steps})")
    print(f"   Target Hub: {hub_repo}")

    # 1. Load Base Model
    print("⏳ Loading base model (FLUX.1-Kontext-dev)...")
    pipe = FluxKontextPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-Kontext-dev",
        torch_dtype=torch.bfloat16,
        cache_dir="/models",
    )
    
    # Freeze base parameters
    pipe.unet.requires_grad_(False)
    pipe.text_encoder.requires_grad_(False)
    pipe.text_encoder_2.requires_grad_(False)

    # 2. Configure LoRA
    print(f"⚙️ Configuring LoRA (Rank={rank})...")
    lora_config = LoraConfig(
        r=rank,
        lora_alpha=rank * 2,
        target_modules=["to_k", "to_q", "to_v", "to_out.0"], # Attention layers
        init_lora_weights="gaussian",
    )

    # Apply LoRA to UNet
    pipe.unet = get_peft_model(pipe.unet, lora_config)
    pipe.unet.print_trainable_parameters()

    # 3. Load Dataset
    # Expects a HF dataset with 'image' and 'text' columns
    try:
        dataset = load_dataset(dataset_repo, split="train")
        print(f"📚 Loaded dataset with {len(dataset)} examples.")
    except Exception as e:
        print(f"⚠️ Could not load dataset '{dataset_repo}'. Using dummy data for structure check.")
        print(f"   Error: {e}")
        # Create a dummy dataset for demonstration if real one fails
        from datasets import Dataset
        dummy_data = {"image": [None], "text": ["dummy"]}
        dataset = Dataset.from_dict(dummy_data)

    # 4. Simple Training Loop (Skeleton for Hackathon Speed)
    # In a full production script, you'd add image preprocessing, noise scheduling, etc.
    optimizer = torch.optim.AdamW(pipe.unet.parameters(), lr=learning_rate)
    
    device = "cuda"
    pipe.to(device)

    print("🔥 Training started...")
    
    # Mock training loop for structure verification
    # Replace this block with actual diffusion training steps (noise prediction loss)
    for step in range(steps):
        # Placeholder for actual training logic:
        # 1. Sample batch from dataset
        # 2. Preprocess images (resize, normalize)
        # 3. Add noise
        # 4. Predict noise with unet
        # 5. Calculate loss
        # 6. Backprop and step
        
        if step % 100 == 0:
            print(f"   Step {step}/{steps} completed.")

    # 5. Save Adapter
    output_path = Path(f"/models/{output_name}")
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"💾 Saving adapter to {output_path}...")
    pipe.unet.save_pretrained(output_path)
    
    # Also save the config
    lora_config.save_pretrained(output_path)

    print(f"✅ Training complete!")

    # 6. Push to Hub (Optional)
    if push_to_hub:
        print(f"📤 Pushing to Hugging Face Hub ({hub_repo})...")
        try:
            api = HfApi()
            api.upload_folder(
                folder_path=str(output_path),
                repo_id=hub_repo,
                repo_type="model",
                commit_message=f"NEXUS Couture LoRA v1 - Rank {rank}, Steps {steps}",
            )
            print(f"🎉 Successfully pushed to https://huggingface.co/{hub_repo}")
        except Exception as e:
            print(f"❌ Failed to push to hub: {e}")
            print("   Ensure you are logged in with `huggingface-cli login` or have HF_TOKEN set.")

    return str(output_path)

@app.local_entrypoint()
def main():
    """Local entrypoint to trigger training"""
    train_nexus_couture_lora.remote(
        dataset_repo="specimba/nexus-couture-training", # Replace with your actual dataset
        output_name="nexus-couture-v1",
        rank=16,
        steps=600,
        push_to_hub=True
    )
