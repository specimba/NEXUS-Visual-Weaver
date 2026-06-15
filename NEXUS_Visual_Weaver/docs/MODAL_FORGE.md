# Modal Forge

Modal is used as an offline forge for NEXUS Visual Weaver.

It is not the primary public runtime. The public product remains the Hugging Face Gradio Space.

Modal jobs are reserved for:
- LoRA/adaptor experiments
- prompt/image eval grids
- demo asset generation
- artifact reports
- submission audit generation

The public Space exposes only safe read-only metadata from these jobs.

## Integration Status

- **Primary Runtime**: Hugging Face ZeroGPU (NVIDIA RTX Pro 6000 Blackwell)
- **Modal Role**: Offline computation, training, and artifact generation
- **Credit Usage**: Hackathon Modal credits ($251 allocation)
- **Public Interface**: Read-only status panels in Gradio Space

## Compliance

- Public Space model budget: ≤32B parameters
- Modal usage: Development and runtime support (qualifies for "Best Use of Modal" prize)
- ZeroGPU: Primary inference engine (free tier + PRO quota)
