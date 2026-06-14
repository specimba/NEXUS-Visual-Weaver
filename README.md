---
title: NEXUS Visual Weaver
emoji: 🧵
colorFrom: red
colorTo: gray
sdk: gradio
sdk_version: 6.12.0
app_file: app.py
pinned: false
license: apache-2.0
short_description: Governed gothic couture visual creation command center
models:
  - black-forest-labs/FLUX.2-klein-9B
  - nvidia/LocateAnything-3B
  - openbmb/MiniCPM-V-4.6
  - nvidia/NVIDIA-Nemotron-Parse-v1.2
tags:
  - gradio
  - mcp-server
  - build-small
  - visual-creation
  - hackathon
  - off-brand
  - best-agent
  - best-demo
  - openbmb
  - codex
---

# NEXUS Visual Weaver

Dark creative-operations command center for the Hugging Face Build Small Hackathon.

NEXUS Visual Weaver is a Gradio Space prototype for governed image and video creation. It combines a couture-oriented workflow dashboard, outfit and lore planning, model-lane governance, and an always-on defensive export gate.

The current Space path is intentionally direct for judges: enter a creative brief, run the active weave, inspect the generated FLUX.2 artifact, review ST3GG evidence, approve the human checkpoint, and prepare a governed export packet.

## Direction

The interface is built around a command-center surface:

- workflow graph for `Seed Prompt -> Refine -> Judge -> Locate -> Generate -> Video Path -> Human Checkpoint`
- contextual inspector with taste rings, material checks, model stack, relay status, and ST3GG evidence
- wardrobe drawer for garments, materials, footwear, accessories, locks, and reference-region intent
- lore-to-video timeline for compact cinematic beats
- provider handoff cards for dry-run visibility before any paid, gated, or quota-limited call

## Model Governance

Pinned lanes do not rotate:

- `image_generation`: FLUX.2 primary image lane
- `grounding`: NVIDIA LocateAnything-3B grounding anchor
- `security`: ST3GG defensive scanner/export gate

Sponsor/evidence lanes are optional but first-class when secrets are configured:

- `openbmb/MiniCPM-V-4.6` (1.30B): visual judge for wardrobe, footwear, material drift, lore continuity, and export notes.
- `nvidia/NVIDIA-Nemotron-Parse-v1.2` (0.94B): structured evidence/parser lane for NVIDIA/Nemotron claim support.

Helper lanes may rotate with quota, license, health, and parameter-budget checks:

- prompt routing
- taste judging
- audio lore TTS
- video repair
- HF catalog research
- Modal job runner

Public demo mode excludes private, commercial-uncleared, and research-only helper models. Private research mode can expose more candidates, but it never disables consent, provenance, ST3GG, export, or dataset-partition gates.

## Current Features

- Gradio Blocks dashboard with split update regions.
- Real FLUX.2 Klein image generation on Hugging Face ZeroGPU when `HF_TOKEN` is configured.
- Generated artifact ST3GG scan and checkpoint/export state.
- Optional MiniCPM-V and Nemotron provider evidence lanes with explicit configured/missing-secret status.
- Active workflow graph and checkpointed run record.
- Taste profile scoring from `assets/taste_profile.json`.
- Wardrobe slot planning for couture, gothic, fantasy, footwear, accessories, and material control.
- HF model and LoRA catalog with Adult Mode hidden by default.
- GMR/ModelRelay-inspired helper model selection.
- ST3GG-inspired scan adapter with magic detection, mismatch review, purification actions, and export-gate state.
- Focused regression tests for catalog scope, workflow planning, ModelRelay behavior, and scanner evidence.

## Build Small Prize Mapping

| Target | Evidence status |
| --- | --- |
| Gradio Space | App runs as a public Hugging Face Gradio Space with `mcp_server=True`. |
| <=32B models | Active stack is 28.15B: FLUX.2 9B + OFFELLIA 12B + LocateAnything 3.83B + MiniCPM-V 1.30B + Nemotron Parse 0.94B + MiniCPM5 1.08B. |
| Off Brand | Custom command-center UI, dense inspector, workflow graph, wardrobe/lore drawer, and provider cards. |
| Best Agent | Multi-step prompt, generation, scan, judge, checkpoint, export workflow. |
| OpenBMB | Claimed only when MiniCPM-V returns judge evidence in an export packet. |
| NVIDIA | Claimed only when Nemotron returns evidence in an export packet. LocateAnything remains visible but is not the Nemotron claim by itself. |
| OpenAI Codex | Development branch and PR include Codex-authored implementation commits. |
| Demo / social | Add final links here before submission: `DEMO_VIDEO_URL` and `SOCIAL_POST_URL`. |

Tiny Titan is not claimed in the default demo because FLUX.2 Klein 9B is retained for image quality.

## Local Setup

```powershell
python -m pip install -r requirements.txt
python app.py
```

The app reads `NEXUS_PORT` or `PORT` when present, otherwise it launches on `7860`.

## Verification

```powershell
python -m compileall app.py src tests
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q tests -p no:cacheprovider --basetemp=C:\tmp\pytest-nvw-full
```

## Secret Policy

Do not commit provider credentials. Use Hugging Face Space secrets or local `.env` files for:

- `HF_TOKEN`
- `MINICPM_BASE_URL`
- `MINICPM_API_KEY`
- `MINICPM_MODEL`
- `NEMOTRON_BASE_URL`
- `NEMOTRON_API_KEY` or `NVIDIA_API_KEY`
- `NEMOTRON_MODEL`
- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`
- `OPENAI_API_KEY`
- provider-specific API keys or bearer tokens

Generated outputs, local moodboards, logs, caches, auth folders, and preview artifacts are intentionally ignored.

## Review Workflow

- Bootstrap commit establishes the public GitHub repository baseline.
- Future substantial changes should use `codex/specimba/<scope>` branches and draft pull requests.
- GitHub Actions runs compile and pytest.
- CodeRabbit is configured to focus review on Gradio runtime correctness, model governance, security gates, Adult Mode behavior, and regression coverage.

See [docs/RELEASE_WORKFLOW.md](docs/RELEASE_WORKFLOW.md) for the push and review gate.

## License

Apache-2.0. See [LICENSE](LICENSE).
