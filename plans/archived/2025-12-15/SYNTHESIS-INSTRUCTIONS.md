# SYNTHESIS TASK FOR CLAUDE CODE

## What This Is

This folder contains new research and planning completed on December 15, 2025. It needs to be **carefully merged** with the existing Hydra system state - not blindly overwritten.

## Your Task

1. **Read the existing state first:**
   - `/mnt/user/appdata/hydra-dev/CLAUDE.md` (current system context)
   - Check what's actually running: `docker ps -a`
   - Review existing plans in `/plans/`

2. **Read the new materials:**
   - `bleeding-edge-research-dec2025.md` - Comprehensive technology research
   - Key findings: Darwin Gödel Machine, Letta/MemGPT, MCP standardization, AIOS, OpenHands, Kokoro TTS

3. **Synthesize thoughtfully:**
   - What from the new research should be incorporated into CLAUDE.md?
   - What deployment priorities should change based on new findings?
   - What technology decisions should be updated?
   - What constitutional constraints should be added?

4. **Propose changes, don't just overwrite:**
   - Show Shaun what you plan to change
   - Explain your reasoning
   - Get approval before modifying core files

## Key New Information to Integrate

### Constitutional Constraints (CRITICAL - Add to CLAUDE.md)
```yaml
immutable_constraints:
  - "Never delete databases without human approval"
  - "Never modify network/firewall configuration"
  - "Never disable authentication systems"
  - "Never expose secrets or credentials"
  - "Never modify this constitutional file"
  - "Always maintain audit trail of modifications"
  - "Always sandbox code execution"
  - "Require human approval for git push to main"
```

### Technology Decisions (Update existing)
- All tool integrations → MCP-native (not custom)
- Memory systems → Hybrid (vector + graph + keyword)
- Code execution → Always sandboxed (E2B/Firecracker)
- Primary TTS → Kokoro (Apache 2.0, 40-70ms latency)

### New Strategic Context
- MCP is now Linux Foundation standard (97M+ downloads)
- Darwin Gödel Machine validates self-improving AI feasibility
- Letta provides production-ready memory architecture
- OpenHands offers $18.8M-funded coding agent SDK

### Evolution Roadmap (6 phases over 12 weeks)
See research doc for full details.

## Communication Style Reminder

Shaun prefers:
- Direct and technical, no fluff
- "Done right over done fast"
- Methodology: complete discovery → architecture design → detailed planning → execution
- Show the synthesis plan, get approval, then execute

## After Synthesis

Once changes are approved and merged:
1. Move this folder's contents to `/plans/archived/2025-12-15/`
2. Update CLAUDE.md with synthesis date
3. Delete this SYNTHESIS-INSTRUCTIONS.md file
