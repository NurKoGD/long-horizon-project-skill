# Contributing

## Repository Scope

The canonical portable Skill is:

```text
.agents/skills/long-horizon-project/
```

Do not commit a project's `skilluse/` directory to this repository. That directory belongs to each project using the Skill.

## Local Validation

Run these checks from the repository root before committing:

```bash
python -m unittest discover -s tests -v
python -m py_compile .agents/skills/long-horizon-project/scripts/init_skilluse.py .agents/skills/long-horizon-project/scripts/validate_skilluse.py
git diff --check
```

`tests/test_scripts.py` runs the scripts against throwaway Git repositories and covers the regressions that matter most: non-ASCII project paths and file names, first-run versus repeat initialization, Git checkpoint parsing, placeholder detection, and the `--strict` exit codes. It needs only the standard library and a working `git`.

The same file also guards the document layer: `SKILL.md` must stay within 800 words, every file under `templates/` and `references/` must be referenced from it, and `VERSION` must be semver. Move detail into `references/` rather than growing the always-loaded file.

On Windows, run the tests with a real interpreter: the `python` App Execution Alias in `WindowsApps` is a stub that exits without running anything. Host-specific validators such as Codex's `quick_validate.py` are optional extras, not requirements for this repository.

## Behavioral Testing

Read `tests/README.md` and run the scenarios in an isolated temporary project. The important behaviors are:

- resume from a compact checkpoint;
- preserve project files and existing state;
- keep assistant artifacts under `skilluse/` when paths are configurable;
- avoid starting the next phase automatically, and capture out-of-scope work in `plans/backlog.md`;
- record `blocked` with a reason instead of pretending a phase is complete;
- detect Git checkpoint mismatches, missing phase files, and Skill version drift;
- follow an existing project Git workflow without inventing a new one.

Do not update the Skill solely because an agent produced a preferred wording. Change it when a realistic scenario demonstrates a missing or conflicting behavior.

## Updating

1. Make the smallest focused change under `.agents/skills/long-horizon-project/`.
2. Run structural, syntax, and behavioral checks.
3. Review the complete diff, including templates and references.
4. Commit with a focused message.
5. Push according to the repository's Git workflow.

Host-specific integrations should be added in separate directories such as `.codex/`, `.claude-plugin/`, or `hooks/`, and must not weaken the portable Skill behavior.
