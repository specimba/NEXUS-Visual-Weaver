import modal
from modal import App, Image, Secret

# Define the App
app = App("nexus-visual-weaver-beast")

# High-performance image with all necessary dependencies
# Using CUDA 12.1 base for maximum compatibility with modern diffusion models
image = (
    Image.debian_slim(python_version="3.10")
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "gradio==4.44.0",
        "diffusers==0.30.0",
        "transformers==4.44.0",
        "accelerate==0.33.0",
        "xformers",
        "opencv-python-headless",
        "pillow",
        "safetensors",
        "huggingface_hub",
        "einops",
        "compel",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install(
        "torch",
        "torchvision",
        "torchaudio",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .add_local_dir(
        "/workspace/NEXUS_Visual_Weaver",
        remote_path="/root/nexus",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1", # Fast downloads
        "CUDA_VISIBLE_DEVICES": "0",
    })
)

# Define the Beast Mode Function
@app.function(
    image=image,
    gpu="A100-80GB",  # THE ROAR: 80GB VRAM A100
    timeout=14400,  # 4 hours (matching your remaining time)
    secrets=[Secret.from_name("huggingface-secret", required_keys=["HF_TOKEN"])],
    max_containers=20,  # High concurrency
)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def run_gradio_app():
    import os
    import sys
    
    # Add the nexus module to path
    sys.path.insert(0, "/root/nexus/src")
    os.chdir("/root/nexus")
    
    # Import the main app file
    # The original repo uses 'app.py' which defines 'demo' as gr.Blocks
    try:
        import app as nexus_app
    except ImportError:
        raise ImportError("Could not import app.py. Ensure NEXUS_Visual_Weaver is mounted correctly.")

    # The NEXUS Visual Weaver app defines the interface as 'demo' (gr.Blocks)
    # We return this object directly for Modal's ASGI handler
    if hasattr(nexus_app, 'demo'):
        return nexus_app.demo
    else:
        raise AttributeError("Could not find Gradio app object 'demo' in app.py")
