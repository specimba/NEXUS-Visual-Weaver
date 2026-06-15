# AGENTS.md

## Operating Rules

- Keep changes scoped and verifiable.
- Prefer focused tests over broad, slow runs.
- Do not launch long-running local servers unless the user asks for visual validation.
- Do not commit generated outputs, local logs, caches, preview artifacts, or credentials.
- Use Hugging Face Space secrets and local `.env` files for provider credentials.
- Preserve the pinned lanes unless the user explicitly approves a model-governance change:
  - FLUX.2 for image generation
  - LocateAnything-3B for grounding
  - ST3GG for security/export review

## Verification

Use these gates before claiming completion:

```powershell
python -m compileall app.py src tests
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q tests -p no:cacheprovider --basetemp=C:\tmp\pytest-nvw-full
```

## Review Focus

- Gradio callback wiring and region updates.
- Adult Mode starts off and never disables safety gates.
- ModelRelay respects parameter, license, quota, cooldown, and pinned-lane rules.
- ST3GG scan results do not expose payload bytes or raw hidden content.

