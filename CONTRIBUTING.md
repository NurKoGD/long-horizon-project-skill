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
python <path-to-quick_validate.py> .agents/skills/long-horizon-project
python -m py_compile .agents/skills/long-horizon-project/scripts/init_skilluse.py .agents/skills/long-horizon-project/scripts/validate_skilluse.py
git diff --check
```

The Codex quick validator is normally available from the local Codex installation at `~/.codex/skills/.system/skill-creator/scripts/quick_validate.py`. Claude Code users should use the equivalent Agent Skills validator or inspect the required `SKILL.md` frontmatter manually.

## Behavioral Testing

Read `tests/README.md` and run the scenarios in an isolated temporary project. The important behaviors are:

- resume from a compact checkpoint;
- preserve project files and existing state;
- keep assistant artifacts under `skilluse/` when paths are configurable;
- avoid starting the next phase automatically;
- detect Git checkpoint mismatches;
- follow an existing project Git workflow without inventing a new one.

Do not update the Skill solely because an agent produced a preferred wording. Change it when a realistic scenario demonstrates a missing or conflicting behavior.

## Updating

1. Make the smallest focused change under `.agents/skills/long-horizon-project/`.
2. Run structural, syntax, and behavioral checks.
3. Review the complete diff, including templates and references.
4. Commit with a focused message.
5. Push according to the repository's Git workflow.

Host-specific integrations should be added in separate directories such as `.codex/`, `.claude-plugin/`, or `hooks/`, and must not weaken the portable Skill behavior.
