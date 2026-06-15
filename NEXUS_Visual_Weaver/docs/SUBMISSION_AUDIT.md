# Submission Audit

## Canonical Space
**Repository**: `build-small-hackathon/NEXUS_Visual_Weaver`  
**URL**: https://huggingface.co/spaces/build-small-hackathon/NEXUS_Visual_Weaver  
**SDK**: Gradio 6.5.1  
**Hardware**: ZeroGPU (NVIDIA RTX Pro 6000 Blackwell - 104GB VRAM)

## Track Fit
- **Primary**: Thousand Token Wood (Whimsical, delightful AI-native app)
- **Secondary**: Backyard AI (Creator workflow consistency tool)

## Model Stack (Total: ~10B parameters - Well under 32B limit)
| Model | Parameters | Role | Source |
|-------|------------|------|--------|
| FLUX.2-klein-4B | 4B | Image Generation | Black Forest Labs |
| MiniCPM-V-4.6 | 1.30B | Visual Judge | OpenBMB |
| NVIDIA-Nemotron-Parse-v1.2 | 0.94B | Evidence Parser | NVIDIA |
| LocateAnything-3B | 3B | Grounding | NVIDIA |
| ST3GG | <1B | Security Scan | Community |

## Core Loop
1. Text prompt → Wardrobe/Lore planner
2. Visual generation (FLUX.2)
3. ST3GG security scan
4. Dual AI critique (MiniCPM-V + Nemotron-Parse)
5. Checkpoint & export packet

## Bonus Badge Targets
| Badge | Status | Evidence |
|-------|--------|----------|
| Off-Brand | ✅ | Custom Gradio UI with workflow graph |
| Best Agent | ✅ | Multi-step governed agent pipeline |
| Tiny Titan | ✅ | Primary model (FLUX.2-klein-4B) ≤4B |
| Field Notes | ⏳ | Blog post pending |
| Sharing is Caring | ⏳ | Operator state export pending |
| Best Demo | ⏳ | Video recording pending |
| Best Use of Modal | ✅ | Modal Forge for offline artifacts |

## Prize Eligibility
- **Thousand Token Wood**: 1st ($4,000), 2nd ($2,500), 3rd ($1,500), 4th ($1,000), Community Choice ($2,000)
- **Tiny Titan**: $1,000
- **Off-Brand**: $1,500
- **Best Agent**: $1,000
- **Best Use of Modal**: 1st (10k credits), 2nd (7k), 3rd (3k)
- **Bonus Quest Champion**: $2,000 (if 5+ badges achieved)

**Total Potential**: $15,000+ cash + Modal credits + RTX 5080

## Submission Checklist
- [x] Space live in build-small-hackathon org
- [x] Gradio interface deployed
- [x] Models under 32B documented
- [x] Modal integration documented
- [ ] Demo video recorded and linked
- [ ] Social media post with #BuildSmallHackathon
- [ ] Field Notes blog post published
- [ ] Operator state dataset exported

## Audit Timestamp
Generated: $(date -u)
