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
- Pinned model governance is visible: FLUX.2 Klein 9B, LocateAnything-3B, and ST3GG, with FLUX.2 Klein 4B kept as a sidecar fallback.
- Real FLUX.2 Klein 9B generation is wired for HF Space, falls back to the 4B sidecar when needed, and reports an honest dry-run state outside Space.
- Generated artifacts are scanned by ST3GG before checkpoint/export.
- Above-fold trust strip makes ST3GG verdict, export gate, fixture evidence, and adult-mode safety boundaries visible immediately.
- OpenBMB MiniCPM-V 4.6 and NVIDIA Nemotron evidence lanes are represented as real optional provider adapters with missing-secret/failed/success states.
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

1. Configure OpenBMB and Nemotron Space secrets if prize claims are desired.
2. Run one live Space weave and prepare an export packet.
3. Capture demo video and create social post.
4. Add final demo/social URLs to README.
5. Add Playwright/browser visual checks for desktop and mobile overflow once CI is unblocked.

## Prize Claim Evidence Rules

| Prize or badge | Current stance |
| --- | --- |
| Build Small base eligibility | Gradio Space, <=32B stack, and public app path are ready; demo/social links still required. |
| Off Brand | Strong custom command-center UI signal. |
| Best Agent | Multi-step governed workflow is implemented through callbacks and export packet. |
| OpenBMB | Claim only after MiniCPM-V returns `success` in export evidence. |
| NVIDIA | Claim only after Nemotron returns `success` in export evidence. |
| OpenAI Codex | GitHub branch/PR provides Codex development trail. |
| Tiny Titan | Sidecar-only: claim only from an explicit 4B export packet where every active model is <=4B. |
| Modal | Not claimed unless a real Modal job runs. |
