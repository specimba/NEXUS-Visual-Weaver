# Security Policy

## Supported Scope

This repository is an active hackathon prototype. Security-sensitive changes include:

- provider authentication
- file upload handling
- ST3GG scan/export behavior
- Adult Mode catalog gating
- model relay and provider routing
- generated artifact handling

## Secret Handling

Never commit real tokens, API keys, bearer tokens, private keys, OAuth material, or provider credentials.

Use:

- Hugging Face Space secrets for deployment
- local `.env` files for development
- `.env.example` for placeholder names only

Ignored local paths include `.env*`, `.huggingface/`, `.modal.toml`, `.codex-home/`, logs, caches, and generated `outputs/`.

## Required Review Gates

Before merging or deploying:

1. Run compile and pytest.
2. Run a secret-pattern scan over tracked files.
3. Confirm Adult Mode remains opt-in.
4. Confirm ST3GG, consent, provenance, export, and dataset-partition gates remain active in every mode.
5. Confirm generated outputs and local auth folders are not committed.

## Reporting

Open a private issue or contact the repository owner if you find a credential leak, unsafe export path, or bypass of Adult Mode/ST3GG behavior.

