# NEXUS Visual Weaver Final Hackathon Handoff

## Current Target

- GitHub repo: `https://github.com/specimba/NEXUS-Visual-Weaver`
- Working branch: `main`
- HF Space: `build-small-hackathon/NEXUS_Visual_Weaver`
- Public Space URL: `https://build-small-hackathon-nexus-visual-weaver-a107340.hf.space/`
- HF rollback SHA: `410a467c55d11e7308249198bd5fe0b2c190aec6`.
- Stable rollback tag: `stable-raven-quality-20260615` -> `aa37d4d`.
- Last verified code commit: `aa37d4d` (`fix: load flux2 klein pipeline`).
- Last verified HF Space commit: `effbdb4c6a1ea98410165310caea10097ffa0ca6`.
- Last verified HF runtime: `RUNNING`, ZeroGPU, dev mode disabled, `/data` bucket mounted.
- Branch discipline: use only `main` and `codex/specimba/ui-polish-command-center`; no extra recovery branches.
- Primary goal: finish a countable Build Small submission with Raven Quality Stack generation, ST3GG scan, LocateAnything grounding, optional OpenBMB MiniCPM-V judge evidence, optional NVIDIA Nemotron evidence, optional Modal VOID sidecar evidence, checkpointed export packet, README prize mapping, demo video, and social post.

## Secrets Needed

Do not paste these into chat, commits, logs, or export packets.

- `HF_TOKEN`: required for gated FLUX.2 Klein 9B access after license acceptance; the app can honestly fall back to the 4B Tiny Titan sidecar if the 9B lane is unavailable.
- `MINICPM_BASE_URL`: OpenBMB OpenAI-compatible endpoint base URL.
- `MINICPM_API_KEY`: OpenBMB bearer token.
- `MINICPM_MODEL`: default `MiniCPM-V-4.6`.
- `NEMOTRON_BASE_URL`: OpenAI-compatible Nemotron endpoint if available.
- `NEMOTRON_API_KEY` or `NVIDIA_API_KEY`: Nemotron provider token.
- `NEMOTRON_MODEL`: default `nvidia/NVIDIA-Nemotron-Parse-v1.2`.
- `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`: optional for a documented `netflix/void-model` video repair sidecar job.

## Verification Commands

```powershell
python -m compileall app.py src tests
$env:NEXUS_DISABLE_REAL_HF='1'
python -c "import app; print('app import ok')"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q tests -p no:cacheprovider --basetemp=C:\tmp\pytest-nvw-full
hf auth whoami --format json
hf spaces info build-small-hackathon/NEXUS_Visual_Weaver --format json
```

If local proxy settings cause HF CLI connection refusal, use a no-proxy Python `urllib` probe with the cached local HF token. Do not print the token.

## HF Space Log Observation

Use the authenticated Hugging Face SSE log APIs for final runtime/build evidence. Do not paste tokens into chat or files; use a local environment variable or the local `huggingface_hub` token cache.

```powershell
# Container logs
curl.exe -N -H "Authorization: Bearer $env:HF_TOKEN" `
  "https://huggingface.co/api/spaces/build-small-hackathon/NEXUS_Visual_Weaver/logs/run"

# Build logs
curl.exe -N -H "Authorization: Bearer $env:HF_TOKEN" `
  "https://huggingface.co/api/spaces/build-small-hackathon/NEXUS_Visual_Weaver/logs/build"
```

If local proxy/TLS settings break PowerShell or `curl`, use a bounded Python/httpx stream with `trust_env=False`, loaded from the local HF token cache. Redact the token from any printed output.

Current evidence from the SSE API:

- `logs/run` returns HTTP 200 and shows the Gradio/MCP startup stream.
- `logs/build` returns HTTP 200 and shows Build Queued for Space commit `dc6756e`.
- During the final sprint, HF CLI logs hit local Windows proxy/Unicode issues. Public no-proxy probes verified root HTTP 200 and `/gradio_api/info` callback exposure.

## Runtime Flow

1. `run_active_weave` builds the Raven Chronicle run packet from prompt, wardrobe, lore, model stack, and LocateAnything region plan.
2. FLUX.2 Klein 9B generates the flagship image on Space when HF runtime and gated access are configured; FLUX.2 Klein 4B is an honest sidecar fallback.
3. Generated artifact is scanned by ST3GG.
4. MiniCPM-V judge runs when OpenBMB secrets are present.
5. Nemotron evidence runs when Nemotron/NVIDIA endpoint secrets are present.
6. Modal VOID repair remains a sidecar evidence lane until a real job is documented.
7. `approve_checkpoint` requires a generated artifact and ST3GG clear/pass state.
8. `prepare_export_packet` writes a governed JSON packet to `/data/nexus_visual_weaver/exports` or `outputs/exports`.

## Claim Rules

- OpenBMB prize claim requires `minicpm_judge.status == "success"` in an export packet.
- NVIDIA prize claim requires `nemotron_evidence.status == "success"` in an export packet.
- LocateAnything supports the grounding story but does not replace Nemotron for the NVIDIA prize.
- Tiny Titan can be claimed only from a successful sidecar export packet because each active sidecar model is <=4B.
- Raven Quality Stack is the primary story: FLUX.2 Klein 9B, OFFELLIA Q4, LocateAnything, MiniCPM-V, Nemotron, MiniCPM5, FunctionGemma, and Kokoro are individually under 32B.
- Modal is not claimed unless a real `netflix/void-model` or equivalent Modal job runs and is documented.

## Known Risks

- GitHub CLI may fail behind proxy `127.0.0.1:9`; use local git status and HF verification when blocked.
- Real FLUX generation depends on Space GPU availability and gated 9B access; the 4B sidecar exists to keep the demo useful without mislabeling the flagship lane.
- OpenBMB and Nemotron endpoints are optional and must show `missing secret` rather than fake success when not configured.
- Demo video and social post links must be added before final submission.
- Dev mode served stale `dc6756e` until disabled through the HF API. Keep dev mode off for final judging unless you immediately verify `/config` after re-enabling.

## Last Verified Checks

- Local compile: `python -m compileall app.py src tests` passed.
- Local import: `NEXUS_DISABLE_REAL_HF=1 python -c "import app; print('app import ok')"` passed.
- Local tests: `123 passed, 1 warning`.
- Secret scan: no `hf_`, `Bearer`, `sk-`, or obvious API-key literals in tracked files.
- Public Space: root HTTP 200.
- Public Space API: `/gradio_api/info` exposed `run_active_weave`, `scan_reference`, `approve_checkpoint`, `prepare_export_packet`, and `toggle_adult_catalog`.
- Public Space config: `Raven Quality Stack` and `FLUX.2 9B PINNED` present; old `Dark Couture v2.4` and `FLUX.2 4B PINNED` absent.
- Live weave: real FLUX image generated after switching to `Flux2KleinPipeline`; ST3GG marked the generated PNG `review` and blocked export due high entropy review, proving the export gate is active.

## Last-Step Checklist

- Run full tests locally.
- Secret-scan tracked files.
- Commit and push GitHub branch.
- Upload the same snapshot to HF Space.
- Verify Space SHA and public endpoint.
- Run one live Space weave.
- Prepare export packet.
- Add demo and social links to README.
- Tag final release after merge/deploy.
