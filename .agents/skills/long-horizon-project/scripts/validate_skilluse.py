#!/usr/bin/env python3
"""Validate project-side long-horizon state and report synchronization risks."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_HEADINGS = (
    "# Current State",
    "## Current Phase",
    "## Code Checkpoint",
    "## Verification",
    "## Next Action",
)
CHECKPOINT_HEADING = "## Code Checkpoint"
HEAD_LINE_RE = re.compile(r"HEAD:\s*([0-9a-f]{7,40})", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"<[^<>\n]+>")
WORD_BUDGET = 500

# Git writes paths as UTF-8 bytes. Decoding with the platform locale (for
# example cp936 on a Chinese Windows install) raises UnicodeDecodeError inside
# the subprocess reader thread and leaves stdout as None, so both the encoding
# and the None case are handled explicitly.
GIT_ENCODING = "utf-8"
GIT_ERRORS = "replace"


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def git(path: Path, *args: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            check=False,
            capture_output=True,
            encoding=GIT_ENCODING,
            errors=GIT_ERRORS,
        )
    except (OSError, ValueError) as exc:
        return False, str(exc)
    output = (result.stdout or "").strip()
    if result.returncode != 0:
        return False, (result.stderr or "").strip() or "git command failed"
    return True, output


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_section(text: str, heading: str) -> str:
    """Return the body of one '## Heading' section, stopping at the next heading."""
    body: list[str] = []
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if inside:
                break
            if stripped == heading:
                inside = True
            continue
        if inside:
            body.append(line)
    return "\n".join(body)


def checkpoint_heads(text: str) -> tuple[str | None, str | None]:
    """Read the project and state commit hashes from labelled lines.

    Label-first parsing is required because the checkpoint records two hashes
    and their order is not fixed by the template.
    """
    section = extract_section(text, CHECKPOINT_HEADING)
    project: str | None = None
    state: str | None = None
    unlabelled: list[str] = []
    for line in section.splitlines():
        match = HEAD_LINE_RE.search(line)
        if not match:
            continue
        sha = match.group(1)
        lowered = line.lower()
        if "state" in lowered:
            state = state or sha
        elif "project" in lowered or "code" in lowered:
            project = project or sha
        else:
            unlabelled.append(sha)
    if project is None and len(unlabelled) == 1:
        project = unlabelled[0]
    return project, state


def normalise(token: str) -> str:
    return " ".join(token.strip().lower().split())


def template_placeholders(skill_dir: Path) -> set[str]:
    """Collect the placeholder tokens the shipped template uses.

    Deriving the set from the template keeps this check accurate: angle
    brackets in real content such as ``IReadOnlyList<Item>`` are not flagged.
    """
    template = skill_dir / "templates" / "current.md"
    if not template.is_file():
        return set()
    text = read_text(template)
    return {normalise(match.group(0)) for match in PLACEHOLDER_RE.finditer(text)}


def same_commit(recorded: str, actual: str) -> bool:
    recorded, actual = recorded.lower(), actual.lower()
    if not recorded or not actual:
        return True
    return actual.startswith(recorded) or recorded.startswith(actual)


def ignore_covered(gitignore: Path) -> bool:
    if not gitignore.is_file():
        return False
    lines = {line.strip() for line in read_text(gitignore).splitlines()}
    return bool(lines & {"/skilluse/", "skilluse/", "/skilluse", "**/skilluse/"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".", help="project directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return failure for warnings as well; errors always return failure",
    )
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    state = project / "skilluse"
    skill_dir = Path(__file__).resolve().parents[1]
    report = Report()

    if not project.is_dir():
        print(f"error: project directory does not exist: {project}", file=sys.stderr)
        return 2
    if not state.is_dir():
        report.errors.append("skilluse/ directory is missing")
    current = state / "context" / "current.md"
    if not current.is_file():
        report.errors.append("skilluse/context/current.md is missing")
        content = ""
    else:
        content = read_text(current)
        for heading in REQUIRED_HEADINGS:
            if heading not in content:
                report.errors.append(f"current.md is missing: {heading}")
        words = len(content.split())
        if words > WORD_BUDGET:
            report.warnings.append(
                f"current.md is {words} words, over the {WORD_BUDGET}-word context budget; "
                "move finished items into the phase file"
            )
        placeholders = template_placeholders(skill_dir)
        found = sorted(
            {
                match.group(0)
                for match in PLACEHOLDER_RE.finditer(content)
                if normalise(match.group(0)) in placeholders
            }
        )
        if found:
            preview = ", ".join(found[:5])
            report.warnings.append(f"current.md still contains template placeholders: {preview}")

    project_ok, project_root = git(project, "rev-parse", "--show-toplevel")
    project_head = ""
    if not project_ok:
        report.notes.append("project is not a Git repository; the code checkpoint cannot be verified")
    else:
        project_root_path = Path(project_root).resolve()
        if project_root_path != project:
            report.notes.append(f"project path is inside Git root {project_root_path}")
        ok, project_head = git(project, "rev-parse", "HEAD")
        if not ok:
            project_head = ""
            report.notes.append("project repository has no commits yet")
        _, status = git(project, "status", "--porcelain")
        if status:
            report.warnings.append("project working tree has uncommitted changes")
        _, remotes = git(project, "remote")
        if not remotes:
            report.notes.append("project repository has no remote; the code checkpoint is local-only")
        if not ignore_covered(project / ".gitignore") and not ignore_covered(
            project_root_path / ".gitignore"
        ):
            report.warnings.append("no .gitignore entry ignores the root skilluse/ directory")

    state_ok, state_root = git(state, "rev-parse", "--show-toplevel") if state.is_dir() else (False, "")
    state_separate = False
    state_head = ""
    if state_ok:
        try:
            state_separate = Path(state_root).resolve() == state.resolve()
        except OSError:
            state_separate = False
    if not state_separate:
        report.notes.append("skilluse is not a separate Git repository; the state checkpoint is local-only")
    else:
        _, state_status = git(state, "status", "--porcelain")
        if state_status:
            report.warnings.append("skilluse state repository has uncommitted changes")
        _, state_remotes = git(state, "remote")
        if not state_remotes:
            report.notes.append("skilluse repository has no remote; the state checkpoint is local-only")
        ok, state_head = git(state, "rev-parse", "HEAD")
        state_head = state_head if ok else ""

    recorded_project, recorded_state = checkpoint_heads(content)
    if recorded_project and project_head and not same_commit(recorded_project, project_head):
        report.warnings.append(
            f"recorded project HEAD {recorded_project} does not match current HEAD {project_head}"
        )
    if recorded_state and state_head and not same_commit(recorded_state, state_head):
        report.warnings.append(
            f"recorded state HEAD {recorded_state} does not match current HEAD {state_head}"
        )

    for item in report.errors:
        print(f"ERROR: {item}")
    for item in report.warnings:
        print(f"WARN: {item}")
    for item in report.notes:
        print(f"NOTE: {item}")
    if not report.errors and not report.warnings:
        suffix = f" ({len(report.notes)} note(s))" if report.notes else ""
        print(f"OK: skilluse state is structurally valid and synchronized{suffix}")
    else:
        print(
            f"SUMMARY: {len(report.errors)} error(s), {len(report.warnings)} warning(s), "
            f"{len(report.notes)} note(s)"
        )

    return 1 if report.errors or (args.strict and report.warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
