#!/usr/bin/env python3
"""Validate project-side long-horizon state and report synchronization risks."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

LEGACY_HEADINGS = (
    "# Current State",
    "## Current Phase",
    "## Code Checkpoint",
    "## Verification",
    "## Next Action",
)
STRUCTURED_HEADINGS = (
    "# Current State",
    "## Goal",
    "## Verification",
    "## Next Action",
)
FRONT_MATTER_REQUIRED = ("phase", "status", "updated")
STATUS_VALUES = ("in_progress", "blocked", "complete")
CHECKPOINT_HEADING = "## Code Checkpoint"
HEAD_LINE_RE = re.compile(r"HEAD:\s*([0-9a-f]{7,40})", re.IGNORECASE)
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)
UPDATED_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:?\d{2})?)?$"
)
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
    # utf-8-sig accepts files written with or without a BOM; Windows editors add one.
    return path.read_text(encoding="utf-8-sig", errors="replace")


def extract_section(text: str, heading: str) -> str:
    """Return the body of one heading section, stopping at the next heading."""
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


def clean_scalar(value: str) -> str:
    value = value.strip()
    if " #" in value and not value.startswith(("\"", "'")):
        value = value.split(" #", 1)[0].rstrip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def parse_flow_map(value: str) -> dict[str, str] | None:
    """Parse the inline ``{ branch: main, head: abc1234 }`` form for convenience."""
    if not (value.startswith("{") and value.endswith("}")):
        return None
    parsed: dict[str, str] = {}
    for part in value[1:-1].split(","):
        if ":" not in part:
            continue
        key, _, item = part.partition(":")
        parsed[key.strip()] = clean_scalar(item)
    return parsed


def parse_front_matter_block(lines: list[str]) -> dict[str, object]:
    """Parse the small YAML subset the checkpoint uses: scalars, nested maps, flow maps."""
    data: dict[str, object] = {}
    current: str | None = None
    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key, value = key.strip(), clean_scalar(value)
        if raw[:1] in (" ", "\t"):
            if current is None:
                continue
            nested = data.get(current)
            if not isinstance(nested, dict):
                continue
            nested[key] = value
            continue
        if value == "":
            data[key] = {}
            current = key
        elif value.startswith("{"):
            data[key] = parse_flow_map(value) or value
            current = None
        else:
            data[key] = value
            current = None
    return data


def parse_front_matter(text: str) -> tuple[bool, dict[str, object] | None]:
    """Return (has_marker, metadata). metadata is None when the block is broken."""
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return False, None
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return False, None
    closing = next((index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if closing is None:
        return True, None
    return True, parse_front_matter_block(lines[1:closing])


def checkpoint_heads(text: str) -> tuple[str | None, str | None]:
    """Read project and state hashes from the legacy labelled checkpoint lines."""
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


def metadata_head(meta: dict[str, object], key: str) -> str:
    group = meta.get(key)
    if not isinstance(group, dict):
        return ""
    value = str(group.get("head") or "").strip()
    return value if SHA_RE.match(value) else ""


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


def installed_version(skill_dir: Path) -> str:
    version_file = skill_dir / "VERSION"
    if not version_file.is_file():
        return ""
    return read_text(version_file).strip()


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


def resolve_inside(root: Path, relative: str) -> Path | None:
    try:
        candidate = (root / relative).resolve()
        candidate.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return candidate


def check_state_content(
    content: str, skilluse: Path, skill_dir: Path, report: Report
) -> tuple[str | None, str | None]:
    """Validate current.md and return the recorded (project, state) commit hashes."""
    if not content:
        return None, None

    has_marker, meta = parse_front_matter(content)
    if has_marker and meta is None:
        report.errors.append("current.md front matter is not terminated by a closing ---")
        return None, None

    if meta is None:
        for heading in LEGACY_HEADINGS:
            if heading not in content:
                report.errors.append(f"current.md is missing: {heading}")
        report.notes.append(
            "checkpoint uses the legacy prose format; migrate it to the structured front matter "
            "in templates/current.md"
        )
        return checkpoint_heads(content)

    for heading in STRUCTURED_HEADINGS:
        if heading not in content:
            report.errors.append(f"current.md is missing: {heading}")

    for key in FRONT_MATTER_REQUIRED:
        if not str(meta.get(key) or "").strip():
            report.errors.append(f"current.md front matter is missing: {key}")

    status = str(meta.get("status") or "").strip()
    if status and status not in STATUS_VALUES:
        report.errors.append(
            "current.md status must be one of: " + ", ".join(STATUS_VALUES) + f" (found '{status}')"
        )

    updated = str(meta.get("updated") or "").strip()
    if updated and not UPDATED_RE.match(updated):
        report.warnings.append(f"current.md updated is not an ISO 8601 date or datetime: {updated}")

    if status == "blocked" and not str(meta.get("blocked_reason") or "").strip():
        report.warnings.append("status is blocked but front matter has no blocked_reason")
    if status == "complete" and not extract_section(content, "## Verification").strip():
        report.warnings.append("status is complete but ## Verification has no evidence")

    phase_file = str(meta.get("phase_file") or "").strip()
    if not phase_file:
        report.notes.append("no phase_file recorded; the validator cannot check the phase file")
    else:
        resolved = resolve_inside(skilluse, phase_file)
        if resolved is None:
            report.errors.append(f"phase_file must stay inside skilluse/: {phase_file}")
        elif not resolved.is_file():
            report.warnings.append(f"phase_file does not exist: {phase_file}")
        elif status == "complete" and "## Acceptance Criteria" not in read_text(resolved):
            report.warnings.append(
                f"status is complete but {phase_file} has no ## Acceptance Criteria"
            )

    recorded_version = str(meta.get("skill_version") or "").strip()
    installed = installed_version(skill_dir)
    if recorded_version and installed and recorded_version != installed:
        report.warnings.append(
            f"checkpoint was written by skill version {recorded_version}, "
            f"installed is {installed}; update the Skill on this device"
        )
    elif not recorded_version:
        report.notes.append("no skill_version recorded; cross-device version drift cannot be detected")

    return metadata_head(meta, "project_repo") or None, metadata_head(meta, "state_repo") or None


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
    content = ""
    if not current.is_file():
        report.errors.append("skilluse/context/current.md is missing")
    else:
        content = read_text(current)
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

    recorded_project, recorded_state = check_state_content(content, state, skill_dir, report)

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
        _, status_lines = git(project, "status", "--porcelain")
        if status_lines:
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
