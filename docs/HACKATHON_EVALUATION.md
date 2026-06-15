# Hackathon Evaluation Snapshot

## Judge-Facing Product Signal

NEXUS Visual Weaver should open as a working command center, not a landing page. The current target is a Gradio dashboard where judges can immediately see:

- a central workflow graph from prompt to human checkpoint
- a contextual operations panel for Forge, Wardrobe, Lore, Models, Security, and Runs
- a right-side inspector with taste, material, ModelRelay, and ST3GG state
- an artifact preview lane that is honest about dry-run/provider handoff status
- wardrobe and lore drawers that make gothic couture, footwear, accessories, and video continuity concrete

## Current Strengths

- Gradio-compatible app shape with `mcp_server=True`.
- Pinned model governance is visible: FLUX.2 Klein 9B, LocateAnything-3B, and ST3GG.
- Real FLUX.2 Klein 9B-first generation is wired for HF Space and falls back to an honest 4B Tiny Titan sidecar when the gated lane is unavailable.
- Generated artifacts are scanned by ST3GG before checkpoint/export.
- Above-fold trust strip makes ST3GG verdict, export gate, fixture evidence, and adult-mode safety boundaries visible immediately.
- OpenBMB MiniCPM-V 4.6, NVIDIA Nemotron, OFFELLIA Q4, LocateAnything, Kokoro TTS, and Modal VOID evidence lanes are represented with missing-secret/deferred/failed/success states.
- Adult Mode starts off and is framed as catalog scope, not a safety bypass.
- ModelRelay/GMR helper rotation is represented without replacing pinned lanes.
- Tests cover catalog scope, workflow planning, ModelRelay behavior, scanner evidence, and dashboard fallback rendering.

## Remaining Gaps

- MiniCPM-V evidence requires `MINICPM_BASE_URL` and `MINICPM_API_KEY` Space secrets.
- Nemotron evidence requires `NEMOTRON_BASE_URL` and `NEMOTRON_API_KEY` or `NVIDIA_API_KEY` Space secrets.
- Visual validation screenshots should be captured after the next UI pass.
- Docstring coverage is repo-wide 0/76 and should be handled separately if we decide to enforce that review gate.
- Demo video and social post links are still required for final hackathon submission.

## Next Implementation Priority

1. Keep Raven Quality Stack as the submission narrative; use Tiny Titan only as a sidecar export.
2. Configure OpenBMB and Nemotron Space secrets if sponsor prize claims are desired.
3. Run one live Space weave and prepare an export packet.
4. Run/document one Modal sidecar job only if it can complete without risking the main Space.
5. Capture demo video, create social post, and add final links to README.

## Prize Claim Evidence Rules

| Prize or badge | Current stance |
| --- | --- |
| Build Small base eligibility | Gradio Space, each active model <32B, and public app path are ready; demo/social links still required. |
| Off Brand | Strong custom command-center UI signal. |
| Best Agent | Multi-step governed workflow is implemented through callbacks and export packet. |
| OpenBMB | Claim only after MiniCPM-V returns `success` in export evidence. |
| NVIDIA | Claim only after Nemotron returns `success` in export evidence. |
| OpenAI Codex | GitHub branch/PR provides Codex development trail. |
| Tiny Titan | Sidecar-only: claim only from an export packet where every active sidecar model is <=4B. |
| Modal | Not claimed unless a real `netflix/void-model` or equivalent Modal job runs and is documented. |
