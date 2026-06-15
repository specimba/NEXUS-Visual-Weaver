# NEXUS Visual Weaver Final Hackathon Handoff

## Current Target

- GitHub repo: `https://github.com/specimba/NEXUS-Visual-Weaver`
- Working branch: `codex/specimba/ui-polish-command-center`
- HF Space: `build-small-hackathon/NEXUS_Visual_Weaver`
- Public Space URL: `https://build-small-hackathon-nexus-visual-weaver-a107340.hf.space/`
- HF rollback SHA: `410a467c55d11e7308249198bd5fe0b2c190aec6`.
- Branch discipline: use only `main` and `codex/specimba/ui-polish-command-center`; no extra recovery branches.
- Primary goal: finish a countable Build Small submission with real FLUX.2 Klein 9B generation, 4B sidecar fallback, ST3GG scan, optional OpenBMB MiniCPM-V judge evidence, optional NVIDIA Nemotron evidence, checkpointed export packet, README prize mapping, demo video, and social post.

## Secrets Needed

Do not paste these into chat, commits, logs, or export packets.

- `HF_TOKEN`: required when the FLUX.2 Klein 9B Space runtime needs authenticated access; the 4B sidecar remains the public-safe fallback/Tiny Titan lane.
- `MINICPM_BASE_URL`: OpenBMB OpenAI-compatible endpoint base URL.
- `MINICPM_API_KEY`: OpenBMB bearer token.
- `MINICPM_MODEL`: default `MiniCPM-V-4.6`.
- `NEMOTRON_BASE_URL`: OpenAI-compatible Nemotron endpoint if available.
- `NEMOTRON_API_KEY` or `NVIDIA_API_KEY`: Nemotron provider token.
- `NEMOTRON_MODEL`: default `nvidia/NVIDIA-Nemotron-Parse-v1.2`.

## Verification Commands

```powershell
python -m compileall app.py src tests
$env:NEXUS_DISABLE_REAL_HF='1'
python -c "import app; print('app import ok')"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q tests -p no:cacheprovider
hf auth whoami --format json
hf spaces info build-small-hackathon/NEXUS_Visual_Weaver --format json
```

Avoid pytest `--basetemp=C:\tmp` in this Windows sandbox if `tmp_path` fixtures fail with `PermissionError`. The current tests avoid `tmp_path`.

## Runtime Flow

1. `run_active_weave` builds the Raven Chronicle run packet.
2. FLUX.2 Klein 9B generates the image on Space when HF runtime is enabled, with FLUX.2 Klein 4B as the fallback/sidecar lane.
3. Generated artifact is scanned by ST3GG.
4. MiniCPM-V judge runs when OpenBMB secrets are present.
5. Nemotron evidence runs when Nemotron/NVIDIA endpoint secrets are present.
6. `approve_checkpoint` requires a generated artifact and ST3GG clear/pass state.
7. `prepare_export_packet` writes a governed JSON packet to `/data/nexus_visual_weaver/exports` or `outputs/exports`.

## Claim Rules

- OpenBMB prize claim requires `minicpm_judge.status == "success"` in an export packet.
- NVIDIA prize claim requires `nemotron_evidence.status == "success"` in an export packet.
- LocateAnything supports the grounding story but does not replace Nemotron for the NVIDIA prize.
- Tiny Titan can be claimed only from an explicit 4B sidecar export packet where every active model is <=4B.
- Raven Quality Stack uses FLUX.2 Klein 9B by default; OFFELLIA/Gemma remain private research options behind Adult Mode/catalog partitioning.
- Modal is not claimed unless a real Modal job runs and is documented.

## Known Risks

- GitHub CLI may fail behind proxy `127.0.0.1:9`; use local git status and HF verification when blocked.
- Real FLUX generation depends on Space GPU availability and the 9B runtime loading successfully, with a 4B sidecar fallback when configured.
- OpenBMB and Nemotron endpoints are optional and must show `missing secret` rather than fake success when not configured.
- Demo video and social post links must be added before final submission.

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
