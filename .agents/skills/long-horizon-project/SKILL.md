---
name: long-horizon-project
description: Use when starting or continuing a multi-phase coding project across conversations, especially when project state must survive context resets or move between devices.
---

# Long Horizon Project

Use repository files and Git state as durable project memory. Treat the conversation as a short-lived working buffer, not the project record.

## Scope

Use this workflow for multi-phase work, long-running projects, or an explicit `$long-horizon-project` request. Work on one phase at a time. Never start the next phase automatically.

Do not impose this ceremony on a small self-contained fix when the Skill was not invoked.

## Initialize Or Resume

At the beginning of a project, run the bundled initializer by resolving `<skill-directory>` to the actual directory containing this `SKILL.md`. Do not resolve `scripts/` relative to the project working directory:

```text
python "<skill-directory>/scripts/init_skilluse.py" <project-path>
```

If a private state-repository URL is available and `skilluse/` is absent or empty, pass `--state-repo <url>` to clone it. Never clone over a non-empty directory; preserve it and inspect its Git state.

The initializer creates only missing state files and directories. It does not overwrite existing state, initialize or push a remote repository, or discard user files. It adds only `/skilluse/` to the project `.gitignore` when the project is a Git repository.

If Python is unavailable, do the same by hand: create `skilluse/{context,plans/phases,logs,artifacts,local}`, copy `templates/current.md`, `templates/decisions.md`, and `templates/backlog.md`, replace `{{skill_version}}` with the contents of `VERSION`, and add `/skilluse/` to `.gitignore`. Do not skip the checkpoint because a script could not run.

Read the smallest useful context in this order:

1. `skilluse/context/current.md` (normally under 500 words).
2. The phase file named by its `phase_file` field, for example `skilluse/plans/phases/01-parse.md`, created from [templates/phase.md](templates/phase.md).
3. `skilluse/context/environment.md` for build, test, and run commands instead of rediscovering them.
4. `skilluse/context/decisions.md`, starting from its `## Index`, only when relevant.
5. Relevant setup material from `README.md`.
6. Project Git status and HEAD; also `git -C skilluse status` and HEAD when `skilluse/` is a Git repository.
7. Only source files and tests required by the current phase.

Do not reread the full conversation, old logs, or unrelated directories unless the checkpoint is missing or contradicted by observable project state.

Then run the validator before changing code. It reports a stale checkpoint, a missing phase file, decision-index drift, and Skill version drift in one command. Pass `--json` when you need to parse the result instead of reading prose.

If `current.md` is missing, reconstruct only the minimum durable facts from the current conversation and repository evidence, then create a checkpoint before changing business code. Trust code and Git state over an outdated note and record discrepancies.

## State And File Ownership

Put assistant-work artifacts whose path is controllable under `skilluse/`:

```text
skilluse/context/       durable checkpoint, decisions, environment facts
skilluse/plans/phases/  phase scope and acceptance criteria
skilluse/plans/backlog.md  work discovered outside the current phase
skilluse/logs/          verbose logs, named YYYY-MM-DD-<topic>.log
skilluse/artifacts/     reports, screenshots, exports
skilluse/local/         machine-specific data; never secrets; ignored by the state repository
```

Keep `logs/` and `artifacts/` small: delete or archive files from finished phases, because the state repository is cloned on every device.

Keep project deliverables in normal locations such as `src/`, `app/`, `tests/`, configuration directories, and user-requested documentation. Before using another Skill, classify each output as a deliverable or assistant artifact. Read [references/output-routing.md](references/output-routing.md) when the distinction is unclear.

A third-party Skill with a configurable output path should be routed into `skilluse/<category>/<skill-name>/`. A script with a hard-coded path cannot be forced to comply by prompt text alone; record the exception in `skilluse/context/decisions.md` and do not claim complete centralization.

## During A Phase

- Follow the current phase scope and acceptance criteria.
- Keep context compact; summarize durable discoveries in state files instead of repeating them in chat.
- Run focused verification before broad checks. A successful exit code with zero tests discovered, zero files checked, or no meaningful assertions is not verification evidence; record it as inconclusive and choose a check that exercises the phase.
- Do not silently broaden scope because the next phase is obvious.
- Record out-of-scope discoveries in `skilluse/plans/backlog.md` instead of widening the phase or losing them.
- Keep `current.md` inside its word budget: move finished items to the phase file and keep only this phase's state.
- When context becomes large or costly, checkpoint and start a fresh conversation using the next action.

## Handoff And Cross-Device Checkpoint

Before handing work to another conversation or device:

1. Run the phase verification, or record why it could not run.
2. Update `skilluse/context/current.md` using [templates/current.md](templates/current.md), including `status`, `updated`, `skill_version`, and both repository heads.
3. Record important decisions in `skilluse/context/decisions.md` using [templates/decisions.md](templates/decisions.md), and add the same title to its `## Index` so later conversations can scan it cheaply.
4. Run the validator using the same Skill-directory path resolution:

```text
python "<skill-directory>/scripts/validate_skilluse.py" <project-path>
```

5. Confirm `status` is `in_progress`, `blocked`, or `complete`. `blocked` needs `blocked_reason`; `complete` needs acceptance criteria and verification evidence.

For a cross-device checkpoint, the project working tree must be clean. If it is dirty, state exactly what will not transfer and do not call the checkpoint synchronized. Follow the project's documented Git workflow, the user's explicit Git instructions, and any active Git-specific Skill when deciding whether and how to commit or push. This Skill neither requires nor forbids `commit`, `push`, `reset`, or other Git operations. It only requires that the actual Git result be recorded in `current.md`.

When the applicable Git workflow calls for a synchronized remote checkpoint:

1. Apply that workflow; commit and push project code when it requires that step.
2. Record the actual code commit and push result in `current.md`.
3. Commit and push the separate `skilluse` repository when the applicable Git workflow calls for it.

The next device pulls both repositories and compares the recorded code commit before continuing. If either repository has no remote, label the checkpoint local-only. Do not invent a Git policy when none is provided; leave the decision to the user or the applicable Git workflow. Read [references/cross-device.md](references/cross-device.md) for the detailed procedure.

## Completion Boundary

Stop after updating the checkpoint at the end of a phase. Provide the continuation prompt from [templates/handoff-prompt.md](templates/handoff-prompt.md):

```text
Use $long-horizon-project. Resume from skilluse/context/current.md, verify the recorded code checkpoint against both repositories, and continue only the current phase's Next Action.
```

When invoked in an already-running conversation, reconstruct and report the recovered phase, discrepancies, and next action before continuing. The old transcript is not the durable memory.
