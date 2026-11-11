#!/usr/bin/env python3
"""Create the minimal project-side state workspace without overwriting files."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Git writes paths as UTF-8 bytes. Decoding with the platform locale (for
# example cp936 on a Chinese Windows install) raises UnicodeDecodeError inside
# the subprocess reader thread and leaves stdout as None, so both the encoding
# and the None case are handled explicitly.
GIT_ENCODING = "utf-8"
GIT_ERRORS = "replace"

IGNORE_LINES = {"/skilluse/", "skilluse/", "/skilluse"}
STATE_IGNORE = "local/\n"


def run_git(path: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            check=False,
            capture_output=True,
            encoding=GIT_ENCODING,
            errors=GIT_ERRORS,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def append_bytes(path: Path, data: bytes) -> None:
    existing = path.read_bytes() if path.exists() else b""
    with path.open("ab") as handle:
        if existing and not existing.endswith((b"\n", b"\r")):
            handle.write(b"\n")
        handle.write(data)


def ensure_ignore(project: Path) -> str:
    gitignore = project / ".gitignore"
    existing = read_text(gitignore) if gitignore.exists() else ""
    lines = {line.strip() for line in existing.splitlines()}
    if lines & IGNORE_LINES:
        return "/skilluse/ already present in .gitignore"
    append_bytes(gitignore, b"/skilluse/\n")
    return "added /skilluse/ to .gitignore"


def ensure_state_ignore(state: Path) -> str:
    """Keep machine-specific state out of the private state repository."""
    gitignore = state / ".gitignore"
    existing = read_text(gitignore) if gitignore.exists() else ""
    lines = {line.strip() for line in existing.splitlines()}
    if lines & {"local/", "/local/", "/local"}:
        return "local/ already ignored"
    append_bytes(gitignore, STATE_IGNORE.encode("utf-8"))
    return "added local/ to skilluse/.gitignore"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".", help="project directory")
    parser.add_argument(
        "--state-repo",
        help="optional private Git URL to clone into skilluse when the target is absent or empty",
    )
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print(f"error: project directory does not exist: {project}", file=sys.stderr)
        return 2

    skill_dir = Path(__file__).resolve().parents[1]
    state = project / "skilluse"

    if args.state_repo:
        state_exists = state.exists()
        state_empty = state_exists and state.is_dir() and not any(state.iterdir())
        if not state_exists or state_empty:
            try:
                result = subprocess.run(
                    ["git", "clone", args.state_repo, str(state)],
                    check=False,
                    capture_output=True,
                    encoding=GIT_ENCODING,
                    errors=GIT_ERRORS,
                )
            except (OSError, ValueError):
                print("error: could not run git clone", file=sys.stderr)
                return 2
            if result.returncode != 0:
                print("error: private state repository clone failed", file=sys.stderr)
                return 2
        elif not state.is_dir():
            print("error: skilluse exists but is not a directory; it was not changed", file=sys.stderr)
            return 2

    for directory in (
        state / "context",
        state / "plans" / "phases",
        state / "logs",
        state / "artifacts",
        state / "local",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    skipped: list[str] = []
    for source_name, destination in (
        ("current.md", state / "context" / "current.md"),
        ("decisions.md", state / "context" / "decisions.md"),
    ):
        if destination.exists():
            skipped.append(str(destination.relative_to(project)))
            continue
        shutil.copyfile(skill_dir / "templates" / source_name, destination)
        created.append(str(destination.relative_to(project)))

    project_root = run_git(project, "rev-parse", "--show-toplevel")
    ignore_result = "not a Git repository"
    ignore_added = False
    if project_root:
        ignore_result = ensure_ignore(project)
        ignore_added = ignore_result.startswith("added")
    state_ignore_result = ensure_state_ignore(state)

    state_root = run_git(state, "rev-parse", "--show-toplevel")
    separate_state_repo = False
    if state_root:
        try:
            separate_state_repo = Path(state_root).resolve() == state.resolve()
        except OSError:
            separate_state_repo = False
    print(f"project: {project}")
    print(f"created: {', '.join(created) if created else 'none'}")
    print(f"preserved: {', '.join(skipped) if skipped else 'none'}")
    print(f"project git: {'available' if project_root else 'unavailable'}")
    print(f"gitignore: {ignore_result}")
    print(f"state gitignore: {state_ignore_result}")
    print(f"state git: {'separate repository' if separate_state_repo else 'not a separate repository'}")
    if args.state_repo and state_exists and not state_empty:
        print("state repo URL: existing skilluse content preserved; clone skipped")
    if ignore_added:
        print("note: commit .gitignore so the validator stops reporting uncommitted changes")
    print("next: review skilluse/context/current.md and create the current phase file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
