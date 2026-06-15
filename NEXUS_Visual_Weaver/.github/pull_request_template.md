## What Changed
- 

## Why
- 

## Safety Gates
- [ ] No secrets, tokens, generated auth folders, or provider credentials are committed.
- [ ] Adult catalog behavior remains opt-in and does not disable ST3GG, consent, provenance, export, or dataset gates.
- [ ] Pinned lanes remain pinned: FLUX.2 image generation, LocateAnything grounding, ST3GG security.
- [ ] Generated outputs, moodboards, logs, caches, and local previews stay untracked.

## Verification
- [ ] `python -m compileall app.py src tests`
- [ ] `python -m pytest -q tests -p no:cacheprovider --basetemp=C:\tmp\pytest-nvw-full`

## Screenshots / Notes
- 

