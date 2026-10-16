#!/usr/bin/env python3
"""Validate project-side long-horizon state and report synchronization risks."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_HEADINGS = (
    "# Current State",
    "## Current Phase",
    "## Code Checkpoint",
    "## Verification",
    "## Next Action",
)
HASH_RE = re.compile(r"\bHEAD:\s*([0-9a-f]{7,40})\b", re.IGNORECASE)


def git(path: Path, *args: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, result.stderr.strip() or "git command failed"
    return True, result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".", help="project directory")
    parser.add_argument("--strict", action="store_true", help="return failure for warnings")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    state = project / "skilluse"
    errors: list[str] = []
    warnings: list[str] = []

    if not project.is_dir():
        print(f"error: project directory does not exist: {project}", file=sys.stderr)
        return 2
    if not state.is_dir():
        errors.append("skilluse/ directory is missing")
    current = state / "context" / "current.md"
    if not current.is_file():
        errors.append("skilluse/context/current.md is missing")
        content = ""
    else:
        content = current.read_text(encoding="utf-8")
        for heading in REQUIRED_HEADINGS:
            if heading not in content:
                errors.append(f"current.md is missing: {heading}")
        if len(content.split()) > 500:
            warnings.append("current.md exceeds the recommended 500-word context budget")
        if re.search(r"<[^>]+>", content):
            warnings.append("current.md still contains template placeholders")

    project_ok, project_root = git(project, "rev-parse", "--show-toplevel")
    if not project_ok:
        warnings.append("project is not a Git repository")
        project_head = None
    else:
        project_root_path = Path(project_root).resolve()
        if project_root_path != project:
            warnings.append(f"project path is inside Git root {project_root_path}")
        _, project_head = git(project, "rev-parse", "HEAD")
        _, status = git(project, "status", "--porcelain")
        if status:
            warnings.append("project working tree has uncommitted changes")
        _, remotes = git(project, "remote")
        if not remotes:
            warnings.append("project repository has no remote; code checkpoint is local-only")
        gitignore = project / ".gitignore"
        ignore_lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
        if "/skilluse/" not in ignore_lines:
            warnings.append("project .gitignore does not contain root entry /skilluse/")

    state_ok, state_root = git(state, "rev-parse", "--show-toplevel") if state.is_dir() else (False, "")
    if state_ok:
        state_root_path = Path(state_root).resolve()
        if state_root_path != state:
            warnings.append(f"skilluse is inside another Git root {state_root_path}")
        _, state_status = git(state, "status", "--porcelain")
        if state_status:
            warnings.append("skilluse state repository has uncommitted changes")
        _, state_remotes = git(state, "remote")
        if not state_remotes:
            warnings.append("skilluse repository has no remote; state checkpoint is local-only")
    else:
        warnings.append("skilluse is not a separate Git repository")

    recorded = HASH_RE.search(content)
    if recorded and project_head and recorded.group(1).lower() != project_head.lower():
        warnings.append(
            f"recorded project HEAD {recorded.group(1)} does not match current HEAD {project_head}"
        )

    for item in errors:
        print(f"ERROR: {item}")
    for item in warnings:
        print(f"WARN: {item}")
    if not errors and not warnings:
        print("OK: skilluse state is structurally valid and synchronized")
    else:
        print(f"SUMMARY: {len(errors)} error(s), {len(warnings)} warning(s)")

    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
