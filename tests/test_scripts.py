"""Regression tests for the bundled long-horizon-project scripts.

Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".agents" / "skills" / "long-horizon-project"
INIT = SKILL_DIR / "scripts" / "init_skilluse.py"
VALIDATE = SKILL_DIR / "scripts" / "validate_skilluse.py"
GIT = shutil.which("git")


SKILL_VERSION = (SKILL_DIR / "VERSION").read_text(encoding="utf-8").strip()


def structured(
    project_head: str = "",
    state_head: str = "",
    status: str = "in_progress",
    phase_file: str = "plans/phases/01-alpha.md",
    version: str | None = None,
    blocked_reason: str | None = None,
    verification: str = "- `python -m unittest`: passed (12 tests)",
) -> str:
    lines = [
        "---",
        "phase: 01-alpha",
    ]
    if phase_file:
        lines.append(f"phase_file: {phase_file}")
    lines += [
        f"status: {status}",
        "updated: 2026-11-12T00:40Z",
        f"skill_version: {version if version is not None else SKILL_VERSION}",
    ]
    if blocked_reason is not None:
        lines.append(f"blocked_reason: {blocked_reason}")
    lines += [
        "project_repo:",
        "  branch: main",
        f"  head: {project_head}",
        "  pushed: false",
        "state_repo:",
        "  branch: main",
        f"  head: {state_head}",
        "  pushed: false",
        "---",
        "",
        "# Current State",
        "",
        "## Goal",
        "Parse the configuration file.",
        "",
        "## Verification",
        verification,
        "",
        "## Next Action",
        "Write the tokenizer.",
        "",
    ]
    return "\n".join(lines)


def checkpoint(
    project_head: str = "",
    state_head: str = "",
    verification: str = "- `python -m unittest`: passed",
    next_action: str = "Write the parser.",
    state_first: bool = False,
) -> str:
    project_line = f"Project repository: main; HEAD: {project_head}".rstrip()
    state_line = f"State repository: main; HEAD: {state_head}".rstrip()
    checkpoint_lines = [state_line, project_line] if state_first else [project_line, state_line]
    return "\n".join(
        [
            "# Current State",
            "",
            "## Current Phase",
            "Phase 01: alpha - in_progress",
            "",
            "## Code Checkpoint",
            *checkpoint_lines,
            "",
            "## Verification",
            verification,
            "",
            "## Next Action",
            next_action,
            "",
        ]
    )


class ScriptTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="lhp-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.root = Path(self._tmp)

    # -- helpers ---------------------------------------------------------
    def git(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [GIT, "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )

    def head(self, cwd: Path) -> str:
        return self.git(cwd, "rev-parse", "HEAD").stdout.strip()

    def run_script(self, script: Path, project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        # PYTHONUTF8 is deliberately left unset so the child keeps the platform
        # locale. On a Chinese Windows install that is cp936, which is exactly
        # the condition that used to crash the scripts on non-ASCII paths.
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        env.pop("PYTHONUTF8", None)
        return subprocess.run(
            [sys.executable, str(script), str(project), *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

    def init(self, project: Path) -> subprocess.CompletedProcess[str]:
        return self.run_script(INIT, project)

    def validate(self, project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return self.run_script(VALIDATE, project, *args)

    def make_project(self, name: str = "project", commit: bool = True) -> Path:
        project = self.root / name
        project.mkdir(parents=True, exist_ok=True)
        self.git(project, "init", "-q", ".")
        (project / "README.md").write_text("# demo\n", encoding="utf-8")
        if commit:
            self.git(project, "add", "-A")
            self.git(project, "commit", "-qm", "init")
        return project

    def write_state(self, project: Path, text: str) -> None:
        target = project / "skilluse" / "context" / "current.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def commit_gitignore(self, project: Path) -> None:
        self.git(project, "add", "-A")
        self.git(project, "commit", "-qm", "ignored state")

    def assertNoTraceback(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertNotIn("Traceback", result.stderr, result.stderr)


@unittest.skipUnless(GIT, "git is required for these tests")
class InitTests(ScriptTestCase):
    def test_creates_state_workspace_and_ignores(self) -> None:
        project = self.make_project()

        result = self.init(project)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNoTraceback(result)
        self.assertTrue((project / "skilluse" / "context" / "current.md").is_file())
        self.assertTrue((project / "skilluse" / "context" / "decisions.md").is_file())
        for name in ("plans", "logs", "artifacts", "local"):
            self.assertTrue((project / "skilluse" / name).is_dir(), name)
        self.assertIn("/skilluse/", (project / ".gitignore").read_text(encoding="utf-8").splitlines())
        self.assertIn("local/", (project / "skilluse" / ".gitignore").read_text(encoding="utf-8").splitlines())
        self.assertTrue((project / "skilluse" / "plans" / "backlog.md").is_file())
        current = (project / "skilluse" / "context" / "current.md").read_text(encoding="utf-8")
        self.assertIn(f"skill_version: {SKILL_VERSION}", current)
        self.assertNotIn("{{skill_version}}", current)

    def test_preserves_existing_state(self) -> None:
        project = self.make_project()
        targets = {
            "context/current.md": "# Current State\n\nhand written\n",
            "context/decisions.md": "# Decisions\n\nhand written\n",
            "context/environment.md": "# Environment\n\nhand written\n",
            "plans/backlog.md": "# Backlog\n\nhand written\n",
        }
        for relative, text in targets.items():
            path = project / "skilluse" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        result = self.init(project)

        self.assertEqual(result.returncode, 0, result.stderr)
        for relative, text in targets.items():
            self.assertEqual(
                (project / "skilluse" / relative).read_text(encoding="utf-8"),
                text,
                relative,
            )
        self.assertIn("created: none", result.stdout)

    def test_gitignore_is_idempotent(self) -> None:
        project = self.make_project()

        self.init(project)
        result = self.init(project)

        self.assertEqual(result.returncode, 0, result.stderr)
        lines = (project / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines.count("/skilluse/"), 1)

    def test_recognises_unprefixed_gitignore_entry(self) -> None:
        project = self.make_project()
        (project / ".gitignore").write_text("skilluse/\n", encoding="utf-8")

        result = self.init(project)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((project / ".gitignore").read_text(encoding="utf-8"), "skilluse/\n")

    def test_survives_non_ascii_project_path(self) -> None:
        project = self.make_project("项目目录")

        result = self.init(project)

        self.assertNoTraceback(result)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((project / "skilluse" / "context" / "current.md").is_file())

    def test_clones_state_repository_when_absent(self) -> None:
        seed = self.root / "state-seed"
        (seed / "context").mkdir(parents=True)
        self.git(seed, "init", "-q", ".")
        (seed / "context" / "current.md").write_text("# Current State\n\nseeded\n", encoding="utf-8")
        (seed / "local").mkdir()
        self.git(seed, "add", "-A")
        self.git(seed, "commit", "-qm", "seed state")

        project = self.make_project()
        cloned = self.run_script(INIT, project, "--state-repo", str(seed))

        self.assertEqual(cloned.returncode, 0, cloned.stderr)
        self.assertNoTraceback(cloned)
        self.assertIn("state git: separate repository", cloned.stdout)
        self.assertEqual(
            (project / "skilluse" / "context" / "current.md").read_text(encoding="utf-8"),
            "# Current State\n\nseeded\n",
        )
        self.assertIn("local/", (project / "skilluse" / ".gitignore").read_text(encoding="utf-8"))


@unittest.skipUnless(GIT, "git is required for these tests")
class ValidateTests(ScriptTestCase):
    def test_missing_state_is_an_error(self) -> None:
        project = self.make_project()

        result = self.validate(project)

        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR", result.stdout)

    def test_complete_local_checkpoint_passes_strict(self) -> None:
        project = self.make_project()
        self.init(project)
        self.commit_gitignore(project)
        self.write_state(project, checkpoint(project_head=self.head(project)))

        result = self.validate(project, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("WARN", result.stdout)
        self.assertIn("OK", result.stdout)

    def test_detects_project_head_mismatch(self) -> None:
        project = self.make_project()
        self.init(project)
        self.commit_gitignore(project)
        self.write_state(project, checkpoint(project_head="0" * 40))

        result = self.validate(project, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("recorded project HEAD", result.stdout)

    def test_state_hash_first_does_not_break_project_check(self) -> None:
        project = self.make_project()
        self.init(project)
        self.commit_gitignore(project)
        state = project / "skilluse"
        self.git(state, "init", "-q", ".")
        self.git(state, "add", "-A")
        self.git(state, "commit", "-qm", "state")
        self.write_state(
            project,
            checkpoint(project_head=self.head(project), state_head=self.head(state), state_first=True),
        )

        result = self.validate(project)

        self.assertNotIn("recorded project HEAD", result.stdout)

    def test_detects_state_head_mismatch(self) -> None:
        project = self.make_project()
        self.init(project)
        self.commit_gitignore(project)
        state = project / "skilluse"
        self.git(state, "init", "-q", ".")
        self.git(state, "add", "-A")
        self.git(state, "commit", "-qm", "state")
        self.write_state(
            project,
            checkpoint(project_head=self.head(project), state_head="abc1234"),
        )

        result = self.validate(project)

        self.assertIn("recorded state HEAD", result.stdout)

    def test_generic_angle_brackets_are_not_placeholders(self) -> None:
        project = self.make_project()
        self.init(project)
        self.commit_gitignore(project)
        self.write_state(
            project,
            checkpoint(
                project_head=self.head(project),
                verification="- `dotnet test`: passed; returns `IReadOnlyList<Item>` and emits `<br>`",
                next_action="Wire the `<Item>` serializer into the CLI.",
            ),
        )

        result = self.validate(project)

        self.assertNotIn("current.md still contains template placeholders", result.stdout)

    def test_template_placeholders_are_reported(self) -> None:
        project = self.make_project()
        self.init(project)
        self.commit_gitignore(project)
        self.write_state(project, checkpoint(project_head="<commit or working-tree state>"))

        result = self.validate(project)

        self.assertIn("template placeholders", result.stdout)

    def test_word_budget_is_reported(self) -> None:
        project = self.make_project()
        self.init(project)
        self.commit_gitignore(project)
        verbose = "- " + " ".join(f"item{i}" for i in range(600))
        self.write_state(project, checkpoint(project_head=self.head(project), verification=verbose))

        result = self.validate(project, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("context budget", result.stdout)

    def test_survives_non_ascii_dirty_path(self) -> None:
        project = self.make_project()
        self.git(project, "config", "core.quotepath", "false")
        self.init(project)
        (project / "翻译草稿-🚀.md").write_text("x", encoding="utf-8")

        result = self.validate(project)

        self.assertNoTraceback(result)
        self.assertIn(result.returncode, (0, 1))
        self.assertNotIn("AttributeError", result.stderr)

    def test_toplevel_gitignore_covers_monorepo_subproject(self) -> None:
        mono = self.make_project("mono")
        (mono / ".gitignore").write_text("**/skilluse/\n", encoding="utf-8")
        self.git(mono, "add", "-A")
        self.git(mono, "commit", "-qm", "ignore nested state")
        project = mono / "app"
        project.mkdir()
        self.write_state(project, checkpoint(project_head=self.head(mono)))

        result = self.validate(project)

        self.assertNotIn(".gitignore entry", result.stdout)

    def test_legacy_format_is_reported_as_note(self) -> None:
        project = self.make_project()
        self.init(project)
        self.commit_gitignore(project)
        self.write_state(project, checkpoint(project_head=self.head(project)))

        result = self.validate(project)

        self.assertIn("legacy", result.stdout)
        self.assertNotIn("WARN", result.stdout)


@unittest.skipUnless(GIT, "git is required for these tests")
class StructuredCheckpointTests(ScriptTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.project = self.make_project()
        self.init(self.project)
        self.commit_gitignore(self.project)
        self.phase = self.project / "skilluse" / "plans" / "phases" / "01-alpha.md"
        self.phase.parent.mkdir(parents=True, exist_ok=True)
        self.phase.write_text(
            "# Phase 01: alpha\n\n## Scope\nParse it.\n\n## Acceptance Criteria\n- parses a file\n",
            encoding="utf-8",
        )

    def test_structured_checkpoint_passes_strict(self) -> None:
        self.write_state(
            self.project,
            structured(project_head=self.head(self.project), state_head="local-only"),
        )

        result = self.validate(self.project, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)
        self.assertNotIn("WARN", result.stdout)

    def test_invalid_status_is_an_error(self) -> None:
        self.write_state(
            self.project,
            structured(project_head=self.head(self.project), status="done"),
        )

        result = self.validate(self.project)

        self.assertEqual(result.returncode, 1)
        self.assertIn("status must be one of", result.stdout)

    def test_blocked_requires_a_reason(self) -> None:
        self.write_state(
            self.project,
            structured(project_head=self.head(self.project), status="blocked"),
        )

        result = self.validate(self.project, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked_reason", result.stdout)

    def test_blocked_with_reason_is_clean(self) -> None:
        self.write_state(
            self.project,
            structured(
                project_head=self.head(self.project),
                status="blocked",
                blocked_reason="waiting for API credentials",
            ),
        )

        result = self.validate(self.project, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_phase_file_warns(self) -> None:
        self.write_state(
            self.project,
            structured(
                project_head=self.head(self.project),
                phase_file="plans/phases/99-missing.md",
            ),
        )

        result = self.validate(self.project)

        self.assertIn("phase_file does not exist", result.stdout)

    def test_phase_file_cannot_escape_skilluse(self) -> None:
        self.write_state(
            self.project,
            structured(project_head=self.head(self.project), phase_file="../outside.md"),
        )

        result = self.validate(self.project)

        self.assertEqual(result.returncode, 1)
        self.assertIn("must stay inside skilluse/", result.stdout)

    def test_version_drift_warns(self) -> None:
        self.write_state(
            self.project,
            structured(project_head=self.head(self.project), version="0.0.1"),
        )

        result = self.validate(self.project)

        self.assertIn("skill version 0.0.1", result.stdout)

    def test_complete_requires_acceptance_criteria(self) -> None:
        self.phase.write_text("# Phase 01: alpha\n\n## Scope\nParse it.\n", encoding="utf-8")
        self.write_state(
            self.project,
            structured(project_head=self.head(self.project), status="complete"),
        )

        result = self.validate(self.project)

        self.assertIn("## Acceptance Criteria", result.stdout)

    def test_flow_mapping_heads_are_parsed(self) -> None:
        head = self.head(self.project)
        content = (
            "---\n"
            "phase: 01-alpha\n"
            "status: in_progress\n"
            "updated: 2026-11-12\n"
            f"project_repo: {{ branch: main, head: {head}, pushed: false }}\n"
            "state_repo: { branch: main, head: local-only, pushed: false }\n"
            "---\n\n"
            "# Current State\n\n## Goal\nParse it.\n\n"
            "## Verification\n- `python -m unittest`: passed\n\n"
            "## Next Action\nShip it.\n"
        )
        self.write_state(self.project, content)

        result = self.validate(self.project)

        self.assertNotIn("recorded project HEAD", result.stdout)
        bad = content.replace(head, "0" * 40)
        self.write_state(self.project, bad)
        self.assertIn("recorded project HEAD", self.validate(self.project).stdout)

    def test_utf8_bom_checkpoint_is_accepted(self) -> None:
        # Windows editors and PowerShell 5 write a BOM before the front matter.
        path = self.project / "skilluse" / "context" / "current.md"
        path.write_text(
            structured(project_head=self.head(self.project)), encoding="utf-8-sig"
        )

        result = self.validate(self.project, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("legacy", result.stdout)

    def test_broken_front_matter_is_an_error(self) -> None:
        self.write_state(self.project, "---\nphase: 01-alpha\n\n# Current State\n")

        result = self.validate(self.project)

        self.assertEqual(result.returncode, 1)
        self.assertIn("not terminated", result.stdout)

    def test_missing_goal_heading_is_an_error(self) -> None:
        content = structured(project_head=self.head(self.project)).replace("## Goal\n", "## Aim\n")
        self.write_state(self.project, content)

        result = self.validate(self.project)

        self.assertEqual(result.returncode, 1)
        self.assertIn("## Goal", result.stdout)


def decisions_doc(entries: list[str], index_rows: list[str] | None = None) -> str:
    rows = entries if index_rows is None else index_rows
    lines = [
        "# Decisions",
        "",
        "## Index",
        "",
        "| Date | Decision | Phase | Status |",
        "|---|---|---|---|",
    ]
    lines += [f"| 2026-11-12 | {title} | 01-alpha | active |" for title in rows]
    lines += ["", "## Decision Log", ""]
    for title in entries:
        lines += [f"### 2026-11-12 - {title}", "", "- Decision: x", "- Reason: y", "- Consequence: z", ""]
    return "\n".join(lines)


class StateHygieneTests(ScriptTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.project = self.make_project()
        self.init(self.project)
        self.commit_gitignore(self.project)
        self.state = self.project / "skilluse"
        self.phase = self.state / "plans" / "phases" / "01-alpha.md"
        self.phase.parent.mkdir(parents=True, exist_ok=True)
        self.phase.write_text(
            "# Phase 01: alpha\n\n## Scope\nParse it.\n\n## Acceptance Criteria\n- parses a file\n",
            encoding="utf-8",
        )
        self.write_state(self.project, structured(project_head=self.head(self.project)))

    def write(self, relative: str, content: str) -> None:
        path = self.state / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_decisions_index_in_sync_is_clean(self) -> None:
        self.write("context/decisions.md", decisions_doc(["Use front matter", "Keep backlog"]))

        result = self.validate(self.project)

        self.assertNotIn("decisions.md index", result.stdout)

    def test_decisions_index_missing_entry_warns(self) -> None:
        self.write(
            "context/decisions.md",
            decisions_doc(["Use front matter", "Keep backlog"], index_rows=["Use front matter"]),
        )

        result = self.validate(self.project)

        self.assertIn("index is missing 1 entr", result.stdout)

    def test_decisions_index_extra_entry_warns(self) -> None:
        self.write(
            "context/decisions.md",
            decisions_doc(["Use front matter"], index_rows=["Use front matter", "Ghost decision"]),
        )

        result = self.validate(self.project)

        self.assertIn("absent from the log", result.stdout)

    def test_decisions_without_index_is_noted(self) -> None:
        self.write("context/decisions.md", "# Decisions\n\n### 2026-11-12 - No index\n")

        result = self.validate(self.project)

        self.assertIn("no ## Index", result.stdout)
        self.assertNotIn("WARN", result.stdout)

    def test_decisions_over_cap_warns(self) -> None:
        self.write("context/decisions.md", decisions_doc([f"Decision {i}" for i in range(41)]))

        result = self.validate(self.project)

        self.assertIn("over the 40-entry budget", result.stdout)

    def test_missing_environment_is_noted(self) -> None:
        (self.state / "context" / "environment.md").unlink()

        result = self.validate(self.project)

        self.assertIn("no context/environment.md", result.stdout)

    def test_environment_placeholders_are_advisory(self) -> None:
        self.write("context/environment.md", "# Environment\n\n- test: `<command>`\n")

        result = self.validate(self.project)

        self.assertIn("environment.md still contains template placeholders", result.stdout)
        self.assertNotIn("WARN", result.stdout)

    def test_empty_environment_warns(self) -> None:
        self.write("context/environment.md", "   \n")

        result = self.validate(self.project)

        self.assertIn("environment.md is empty", result.stdout)

    def test_oversized_logs_warn(self) -> None:
        big = self.state / "logs" / "big.log"
        big.parent.mkdir(parents=True, exist_ok=True)
        with big.open("wb") as handle:
            handle.seek(26 * 1024 * 1024)
            handle.write(b"x")

        result = self.validate(self.project)

        self.assertIn("MB", result.stdout)
        self.assertIn("stays cheap to clone", result.stdout)

    def test_json_output_is_a_single_object(self) -> None:
        self.write("context/decisions.md", decisions_doc(["Use front matter"]))

        result = self.validate(self.project, "--json")

        payload = json.loads(result.stdout)
        self.assertIn("ok", payload)
        self.assertIsInstance(payload["errors"], list)
        self.assertIsInstance(payload["warnings"], list)
        self.assertIsInstance(payload["notes"], list)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
