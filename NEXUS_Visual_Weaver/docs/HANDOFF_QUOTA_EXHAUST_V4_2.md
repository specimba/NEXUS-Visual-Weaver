# NEXUS Visual Weaver v4.2 Handoff - Quota Exhaustion Coverage

Date: 2026-06-15

This handoff captures the current live state after the practical UX recovery pass. Use it if the current Codex session or quota expires.

## Current State

- GitHub branch: `main`
- Latest GitHub commit: `4b9ab3f fix: make creation path practical and visible`
- Latest HF Space commit: `4c4521d9e88aedcbf2bd01d1394fe9fa683a01b5`
- HF Space: `build-small-hackathon/NEXUS_Visual_Weaver`
- Live URL: <https://build-small-hackathon-nexus-visual-weaver-a107340.hf.space/>
- HF runtime verified after deploy:
  - `dev_mode=false`
  - runtime stage `RUNNING`
  - domain stage `READY`
  - runtime SHA equals Space SHA: `4c4521d9e88aedcbf2bd01d1394fe9fa683a01b5`

## Important Discovery

The live UI was stale because Hugging Face Dev Mode kept an older container running. The repository already had newer code, but the visible Space did not reflect it.

Fixed with:

```powershell
$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:ALL_PROXY=''; $env:NO_PROXY='*'
hf spaces dev-mode build-small-hackathon/NEXUS_Visual_Weaver --stop
hf spaces restart build-small-hackathon/NEXUS_Visual_Weaver --factory-reboot
```

If future screenshots show old labels again, check `runtime.dev_mode` and `runtime.raw.sha` before editing more code.

## Practical UX Fixes Shipped

Commit `4b9ab3f` changes:

- Moves `Artifact Preview Lane` above the workflow graph so real output is visible sooner.
- Collapses provider lanes by default under `Optional provider lanes`.
- Moves file upload into a collapsed `Optional ST3GG file/reference scan` section.
- Makes `Run Active Weave` the primary action.
- Keeps checkpoint/export/reset as immediate operator actions.
- Changes generated/export-ready states in the footer from red failure styling to green success styling.
- Enlarges the artifact preview frame so the generated image reads as the product outcome.

Files changed:

- `app.py`
- `src/nexus_visual_weaver/render.py`
- `src/nexus_visual_weaver/styles.py`
- `.gitignore` now ignores `.hf-upload-cache/`

## What "Missing Secret" Means

`MISSING_SECRET` was not asking for more Hugging Face access. It referred to optional sponsor/provider lanes, mainly:

- OpenBMB/MiniCPM: `MINICPM_BASE_URL` plus `MINICPM_API_KEY` or `OPENBMB_API_KEY`
- NVIDIA/Nemotron: `NEMOTRON_BASE_URL` plus `NEMOTRON_API_KEY` or `NVIDIA_API_KEY`
- Other optional gateways: `FAL_KEY`, Netlify, Cloudflare

Those lanes are not the P0 demo. They should remain collapsed or framed as optional. Do not make the main flow depend on them.

## Verification Already Run Locally

Before commit:

```powershell
python -m compileall app.py src tests
$env:NEXUS_DISABLE_REAL_HF='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q tests -p no:cacheprovider --basetemp=C:\tmp\pytest-nvw-full
git grep -n -I -E "hf_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9._-]+|sk-[A-Za-z0-9_-]{20,}|api[_-]?key\s*=" -- .
```

Result:

- Compile clean
- `288 passed, 1 warning`
- Secret scan clean

After deploy:

```powershell
$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:ALL_PROXY=''; $env:NO_PROXY='*'
hf spaces info build-small-hackathon/NEXUS_Visual_Weaver --format json
Invoke-WebRequest -UseBasicParsing https://build-small-hackathon-nexus-visual-weaver-a107340.hf.space/
Invoke-WebRequest -UseBasicParsing https://build-small-hackathon-nexus-visual-weaver-a107340.hf.space/gradio_api/info
```

Result:

- Space SHA and runtime SHA both `4c4521d9e88aedcbf2bd01d1394fe9fa683a01b5`
- Root returned HTTP 200
- `/gradio_api/info` returned HTTP 200

## Deployment Commands Used

The standard upload failed once because Hugging Face Xet tried to write into a locked local cache. The successful upload disabled Xet while keeping the existing auth token:

```powershell
$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:ALL_PROXY=''; $env:NO_PROXY='*'
$env:HF_HUB_DISABLE_XET='1'
Remove-Item Env:\HF_HOME -ErrorAction SilentlyContinue
hf upload build-small-hackathon/NEXUS_Visual_Weaver C:\tmp\nvw-v422-4b9ab3f . --repo-type=space --commit-message "fix: practical creation path layout"
hf spaces restart build-small-hackathon/NEXUS_Visual_Weaver --factory-reboot
```

## Next Visual QA Checklist

Open the Space in a browser and verify:

- Provider cards are collapsed by default.
- Upload is inside `Optional ST3GG file/reference scan`, not dominating the main screen.
- `Artifact Preview Lane` appears before the workflow graph.
- Footer state after generation reads as success/green, not a red `Generated` block.
- The main visible path is: controls -> `Run Active Weave` -> artifact preview -> checkpoint/export.
- Optional provider lanes do not visually dominate with missing-secret labels.

If any of these fail, first confirm the browser is not cached and HF runtime SHA is still `4c4521d9e88aedcbf2bd01d1394fe9fa683a01b5`.

## Remaining Work

P0 next:

- Browser visual inspection of the live Space after rebuild.
- One live run through `Run Active Weave`.
- Confirm export packet after checkpoint/override.

Do not spend more time on generated README images, Gamma deck polish, Modal, or video until the practical live UI is confirmed usable.

## Demo Framing

Main proof line:

> NEXUS Visual Weaver generates a real FLUX.2 Klein artifact, keeps ST3GG review and human checkpoint visible, and writes audit evidence instead of silently exporting.

Avoid claiming:

- Sponsor judge success unless secrets are configured and a real call returns evidence.
- Video success unless a real `.mp4` is produced by the Space.
- Dynamic LoRA success unless export evidence reports `loaded`.

