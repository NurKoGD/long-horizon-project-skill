# Skill Evaluation Scenarios

Run these scenarios in a temporary Git project. Do not use a real project or a real private state repository for evaluation.

## Resume And Token Discipline

Create `skilluse/context/current.md` with a current phase and one `Next Action`, plus a phase file. Ask the agent to resume. Verify that it reads the checkpoint and only the relevant phase files rather than rereading the entire conversation or repository.

## Phase Boundary

Give the agent a completed Phase 01 with a clearly named Phase 02. Ask it to finish Phase 01. Verify that it updates the checkpoint and does not begin Phase 02 automatically.

## Output Routing

Ask a plan-producing task to create notes and a report. Verify that configurable assistant artifacts are placed under `skilluse/`, while source code and requested project deliverables remain in normal project directories.

## Cross-Device State

Use separate project and `skilluse` repositories. Record a project commit in `current.md`, then test both matching and mismatching HEAD values. The validator should distinguish synchronized state from local-only or stale state.

## Git Policy Neutrality

Test both cases:

1. A README or active Git Skill explicitly requires automatic commit/push after verification. The workflow should be followed and recorded.
2. No Git policy is provided. The long-horizon Skill should not invent one; it should record the observed Git state.

## Existing Conversation Import

Start with no `current.md` but provide a partially completed conversation and an existing working tree. Verify that the agent reconstructs a minimal checkpoint, reports discrepancies, and does not pretend the earlier conversation used this Skill.
