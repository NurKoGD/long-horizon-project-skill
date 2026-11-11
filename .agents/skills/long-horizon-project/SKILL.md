---
name: long-horizon-project
description: Use when starting or continuing a multi-phase coding project across conversations, when work must survive a context reset or a move between devices, or when resuming from a checkpoint. Not for a single self-contained change.
---

# Long Horizon Project

Use repository files and Git state as durable project memory; treat the conversation as a short-lived buffer, not the project record.

## Scope

Use this workflow for multi-phase or long-running work and for explicit `$long-horizon-project` requests. Work on one phase at a time and never start the next phase automatically. Do not impose this ceremony on a small self-contained fix when the Skill was not invoked.

## Initialize Or Resume

Resolve `<skill-directory>` to the directory containing this `SKILL.md`, never to the project:

```text
python "<skill-directory>/scripts/init_skilluse.py" <project-path>
```

Pass `--state-repo <url>` only when `skilluse/` is absent or empty; never clone over existing state. The initializer creates only missing files, overwrites nothing, and adds `/skilluse/` to the project `.gitignore`. If Python is unavailable, do the same by hand from `templates/`: create `skilluse/{context,plans/phases,logs,artifacts,local}`, copy the context templates and `backlog.md`, replace `{{skill_version}}` with `VERSION`, and ignore `/skilluse/`. Never skip the checkpoint because a script would not run.

Read the smallest useful context, in this order:

1. `skilluse/context/current.md` (under 500 words).
2. The phase file named in its `phase_file` field, created from [templates/phase.md](templates/phase.md).
3. `skilluse/context/environment.md` for build, test, and run commands.
4. `skilluse/context/decisions.md`, from its `## Index`, only when relevant.
5. The setup section of `README.md`.
6. Project Git status and HEAD; add `git -C skilluse` when it is a separate repository.
7. Only the source files and tests the current phase needs.

Then run the validator before changing code; it reports a stale checkpoint, a missing phase file, decision-index drift, and Skill version drift in one command. Pass `--json` to parse the result instead of reading prose.

If `current.md` is missing, rebuild only the minimum durable facts from the conversation and repository evidence, create the checkpoint, and record discrepancies. Trust code and Git state over stale notes.

## State And File Ownership

```text
skilluse/context/          checkpoint, decisions, environment facts
skilluse/plans/phases/     phase scope and acceptance criteria
skilluse/plans/backlog.md  work discovered outside the current phase
skilluse/logs/             logs named YYYY-MM-DD-<topic>.log
skilluse/artifacts/        reports, screenshots, exports
skilluse/local/            machine-specific data; never secrets; ignored by Git
```

Keep `logs/` and `artifacts/` small: delete or archive finished phases, because every device clones the state repository.

Project deliverables stay in `src/`, `app/`, `tests/`, configuration, and requested documentation. Classify each output before creating it and read [references/output-routing.md](references/output-routing.md) when the line is unclear. Route a controllable third-party Skill into `skilluse/<category>/<skill-name>/`; a hard-coded path cannot be redirected by prompt text, so record the exception in `decisions.md` and do not claim full centralization.

## During A Phase

- Follow the phase scope and acceptance criteria.
- Summarize durable discoveries into state files instead of repeating them in chat.
- Run focused verification first. An exit code with zero tests discovered, zero files checked, or no meaningful assertions is inconclusive, not evidence.
- Do not widen scope because the next phase looks obvious; record such work in `plans/backlog.md`.
- Keep `current.md` inside its budget by moving finished items into the phase file.
- When context grows costly, checkpoint and continue in a fresh conversation.

## Handoff

1. Run phase verification, or record why it could not run.
2. Update `skilluse/context/current.md` from [templates/current.md](templates/current.md): `status`, `updated`, `skill_version`, and both repository heads.
3. Record durable decisions with [templates/decisions.md](templates/decisions.md) and add each title to its `## Index`.
4. Run `validate_skilluse.py` as described above.
5. Confirm `status` is `in_progress`, `blocked`, or `complete`: `blocked` needs `blocked_reason`; `complete` needs acceptance criteria and verification evidence.

Never invent a Git policy: follow the project's documented workflow, the user's instructions, or the active Git Skill, then record the actual commit and push result in `current.md`. A checkpoint is not synchronized while required changes stay uncommitted or unpushed; label it local-only instead. Read [references/cross-device.md](references/cross-device.md) for the cross-device procedure.

## Completion Boundary

Stop after updating the checkpoint. Give the continuation prompt from [templates/handoff-prompt.md](templates/handoff-prompt.md):

```text
Use $long-horizon-project. Resume from skilluse/context/current.md, verify the recorded code checkpoint against both repositories, and continue only the current phase's Next Action.
```

When the Skill is invoked mid-conversation, report the recovered phase, discrepancies, and next action before continuing. The old transcript is not the durable memory.
