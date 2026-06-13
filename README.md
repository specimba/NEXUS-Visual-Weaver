# NEXUS Visual Weaver

Dark creative-operations command center for the Hugging Face Build Small Hackathon.

NEXUS Visual Weaver is a Gradio Space prototype for governed image and video creation. It combines a couture-oriented workflow dashboard, outfit and lore planning, model-lane governance, and an always-on defensive export gate.

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
- Active workflow graph and checkpointed run record.
- Taste profile scoring from `assets/taste_profile.json`.
- Wardrobe slot planning for couture, gothic, fantasy, footwear, accessories, and material control.
- HF model and LoRA catalog with Adult Mode hidden by default.
- GMR/ModelRelay-inspired helper model selection.
- ST3GG-inspired scan adapter with magic detection, mismatch review, purification actions, and export-gate state.
- Focused regression tests for catalog scope, workflow planning, ModelRelay behavior, and scanner evidence.

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

