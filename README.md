# long-horizon-project

[English](README.md) | [简体中文](README.zh-CN.md)

A cross-agent skill for long-running coding projects. It keeps durable project state outside the conversation so an agent can resume work across conversations, context resets, and devices with a smaller context load.

This repository is the distributable source package. The reusable skill lives under `.agents/skills/`; the repository root contains documentation and maintenance material.

## What It Does

- Keeps a compact checkpoint in `skilluse/context/current.md`.
- Organizes phase plans, decisions, logs, and other assistant artifacts under `skilluse/`.
- Loads only the current phase and relevant project files when resuming.
- Keeps one phase per conversation and does not start the next phase automatically.
- Supports a separate private Git repository for `skilluse/`.
- Records actual Git state without imposing a commit or push policy.
- Handles importing an existing conversation that started without the skill.

The skill does not migrate chat transcripts, create conversations, choose a Git commit policy, or force third-party skills with hard-coded output paths to use `skilluse/`.

## Repository Layout

```text
.
├── .agents/
│   └── skills/
│       └── long-horizon-project/
│           ├── SKILL.md
│           ├── agents/openai.yaml
│           ├── references/
│           ├── scripts/
│           └── templates/
├── tests/
│   └── README.md
├── CONTRIBUTING.md
├── README.md
└── .gitignore
```

The repository intentionally does not include Codex or Claude lifecycle hooks yet. The standard Skill works in hosts that support the Agent Skills format. Host-specific plugins and hooks can be added later without changing the portable skill.

## Install

### Skills CLI

After publishing this repository to GitHub:

```bash
npx skills add <owner>/long-horizon-project-skill --skill long-horizon-project -g
```

Use `--copy` when the installer supports it and you want an independent local copy instead of a link.

### Codex

Codex discovers user skills under `~/.agents/skills/`. Clone this repository to a temporary directory, then copy the nested skill directory:

```bash
git clone https://github.com/<owner>/long-horizon-project-skill.git /tmp/long-horizon-project-skill
mkdir -p ~/.agents/skills
cp -R /tmp/long-horizon-project-skill/.agents/skills/long-horizon-project ~/.agents/skills/
```

On Windows PowerShell:

```powershell
git clone https://github.com/<owner>/long-horizon-project-skill.git "$env:TEMP\long-horizon-project-skill"
New-Item -ItemType Directory -Force "$env:USERPROFILE\.agents\skills" | Out-Null
Copy-Item -Recurse -Force `
  "$env:TEMP\long-horizon-project-skill\.agents\skills\long-horizon-project" `
  "$env:USERPROFILE\.agents\skills\long-horizon-project"
```

Restart the host if the skill does not appear immediately. Invoke it explicitly with `$long-horizon-project`; implicit discovery remains enabled.

### Claude Code

Claude Code discovers personal skills under `~/.claude/skills/`:

```bash
git clone https://github.com/<owner>/long-horizon-project-skill.git /tmp/long-horizon-project-skill
mkdir -p ~/.claude/skills
cp -R /tmp/long-horizon-project-skill/.agents/skills/long-horizon-project ~/.claude/skills/
```

Invoke it with `/long-horizon-project`.

The shared `SKILL.md`, scripts, templates, and references are portable. `agents/openai.yaml` is optional host metadata primarily used by Codex.

## Use In A Project

Start a new conversation with:

```text
$long-horizon-project

Initialize or inspect the project state. Work only on the current phase and keep assistant artifacts under skilluse/.
```

For an existing project:

```text
$long-horizon-project

Resume from skilluse/context/current.md. Check the project repository and the skilluse repository, then continue only the current phase's Next Action.
```

Initialize the project-side state workspace with the bundled script. Resolve `<skill-directory>` to the installed skill directory:

```text
python "<skill-directory>/scripts/init_skilluse.py" <project-path>
```

To clone a private state repository only when `skilluse/` is absent or empty:

```text
python "<skill-directory>/scripts/init_skilluse.py" <project-path> --state-repo <private-repository-url>
```

Validate the state before handoff:

```text
python "<skill-directory>/scripts/validate_skilluse.py" <project-path> --strict
```

## Project State

The recommended project arrangement is:

```text
project/
├── src/                 # project functionality
├── tests/               # project tests
├── README.md            # human-facing setup and usage
├── .gitignore           # includes /skilluse/
└── skilluse/            # usually a separate private Git repository
    ├── context/
    │   ├── current.md
    │   └── decisions.md
    ├── plans/phases/
    ├── logs/
    ├── artifacts/
    └── local/
```

Keep project deliverables in normal project paths. Put controllable plans, handoffs, reports, screenshots, and logs under `skilluse/`. Do not put secrets or machine-specific absolute paths in state files.

## Cross-Device Workflow

Use separate repositories when the project code is public but the assistant state is private:

```text
public-project-repository
private-skilluse-repository -> cloned as project/skilluse/
```

At the end of a device session, follow the project's documented Git workflow or the active Git-specific skill. Record the resulting project branch, commit, and push status in `skilluse/context/current.md`. The next device pulls both repositories and checks that the recorded project commit matches the current project commit before changing code.

## Development Status

This package currently provides the portable Skill layer. It does not install host lifecycle hooks. See `CONTRIBUTING.md` for the validation and update workflow.
