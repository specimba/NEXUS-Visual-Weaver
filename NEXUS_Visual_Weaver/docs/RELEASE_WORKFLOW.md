# Release Workflow

NEXUS Visual Weaver uses GitHub for rollback-safe development and Hugging Face Spaces for the hackathon demo.

## Branching

- Bootstrap only: first commit can land on `main` because the public repository starts empty.
- Normal work: create `codex/specimba/<short-scope>` branches.
- Big changes: open draft pull requests and let CI plus review bots comment before merge.

## Push Gate

Before pushing:

1. Run `python -m compileall app.py src tests`.
2. Run `python -m pytest -q tests -p no:cacheprovider --basetemp=C:\tmp\pytest-nvw-full`.
3. Run a secret scan over tracked files.
4. Confirm generated outputs, local logs, caches, Space auth folders, and provider tokens are ignored.

## Secrets

Use Hugging Face Space secrets or local `.env` files. Do not commit real values for:

- `HF_TOKEN`
- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`
- `OPENAI_API_KEY`
- Provider-specific API keys or bearer tokens

## Review Automation

- GitHub Actions runs compile and pytest on `main` and pull requests.
- CodeRabbit can review pull requests using `.coderabbit.yaml`.
- Human review should focus on model governance, Adult Mode gates, ST3GG export behavior, and hackathon demo clarity.

