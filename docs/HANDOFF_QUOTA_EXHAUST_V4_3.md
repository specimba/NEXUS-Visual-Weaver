# NEXUS Visual Weaver v4.3 Quota Handoff

Date: 2026-06-15

## Current State

- GitHub code commit: `0ef6d9e3a014a55d1ea1c51da0994ea340581268`
- Hugging Face Space commit: `5090ba8045a0cb3dddb5d55cc8e212f2e9bc3c76`
- Space: `https://build-small-hackathon-nexus-visual-weaver-a107340.hf.space/`
- Runtime: `RUNNING`
- Dev Mode: `false`
- Root endpoint: HTTP 200
- `/gradio_api/info`: HTTP 200

## What Changed in v4.3

The first viewport is now a creator workflow instead of a governance dashboard.

- First screen shows `Create Couture Image`, `Describe the look`, `Generate Image`, and a large `Output` panel.
- Prompt, seed, style strength, aspect, and core wardrobe controls are visible before technical diagnostics.
- `Generate Image` is the primary action.
- Reference upload, adult mode, video preset, provider cards, catalog, model relay, and workflow graph moved below the fold into collapsed technical sections.
- Output panel now says what happened and what to do next instead of foregrounding provider/gate noise.
- Checkpoint/export buttons are stateful:
  - initial: checkpoint/export disabled
  - generated output: checkpoint enabled
  - checkpoint approved: audit export enabled
- Seed, style strength, and aspect are persisted into creator controls and export evidence.

## Verification Completed

Commands passed locally:

```powershell
python -m compileall app.py src tests
$env:NEXUS_DISABLE_REAL_HF='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q tests -p no:cacheprovider --basetemp=C:\tmp\pytest-nvw-full
git grep -n -I -E "hf_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9._-]+|sk-[A-Za-z0-9_-]{20,}|api[_-]?key\s*=" -- .
```

Results:

- Compile: pass
- Tests: `292 passed`
- Secret scan: no matches
- Local Browser QA: pass
- Live Browser QA: pass

Live Browser QA confirmed first viewport contains:

- `Create Couture Image`
- `Describe the look`
- `Generate Image`
- `Output`

Live Browser QA confirmed first viewport does not show:

- `MISSING_SECRET`
- `Provider Handoff`
- `Model Catalog`
- `GMR ModelRelay`

Console errors/warnings during local and live first-viewport QA: none.

## Important Quota Note

No live GPU generation was triggered during final QA. Local dry-run `Generate Image` was clicked with `NEXUS_DISABLE_REAL_HF=1` and returned cleanly. This preserved ZeroGPU quota.

If quota permits, perform exactly one live run:

1. Open the Space.
2. Confirm first viewport shows the creator-first layout.
3. Click `Generate Image` once.
4. If a real image appears, click `Approve Checkpoint`.
5. If ST3GG blocks export, add a short override reason.
6. Click `Prepare Audit Export`.
7. Save the export packet evidence.

## Deferred on Purpose

- Video generation.
- Modal workflows.
- Sponsor judge calls.
- Bulk crawling/vector reference library.
- README/deck polish.

These are not blockers for the v4.3 creator-first path.

## Rollback

If the Space breaks, revert the Space to the previous known GitHub app state:

- Previous pre-v4.3 GitHub commit: `c49ae37`
- Current app code commit: `0ef6d9e`

Recommended rollback method:

```powershell
git checkout c49ae37
git archive --format=tar HEAD -o C:\tmp\nvw-rollback-c49ae37.tar
tar -xf C:\tmp\nvw-rollback-c49ae37.tar -C C:\tmp\nvw-rollback-c49ae37
hf upload build-small-hackathon/NEXUS_Visual_Weaver C:\tmp\nvw-rollback-c49ae37 . --repo-type=space --commit-message "rollback: pre-v4.3 creator cleanup"
hf spaces restart build-small-hackathon/NEXUS_Visual_Weaver --factory-reboot
```

## Immediate Next Owner Action

Do not resume README, image assets, deck, Modal, or video until the live first viewport stays creator-first after refresh and one quota-safe live generation has been captured.
