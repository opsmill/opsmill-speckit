import json

import pytest
from support import write

from install_check.checks import (
    HooksRegistered,
    Override,
    OwnFiles,
    PlanSetup,
    Registered,
    ScriptsExist,
)
from install_check.errors import CheckFailed


def register(project, kind: str, component_id: str, **entry) -> None:
    write(
        project.path / ".specify" / kind / ".registry",
        json.dumps({kind: {component_id: entry}}),
    )


class TestRegistered:
    def check(self, project) -> Registered:
        return Registered(project, "presets", "a", "1.0.0", ("speckit.plan",))

    def test_fails_on_another_version(self, project):
        register(project, "presets", "a", version="0.9.0")
        with pytest.raises(
            CheckFailed, match="registry has version 0.9.0, manifest has 1.0.0"
        ):
            self.check(project).verify()

    def test_fails_when_disabled(self, project):
        register(project, "presets", "a", version="1.0.0", enabled=False)
        with pytest.raises(CheckFailed, match="a is installed but disabled"):
            self.check(project).verify()

    def test_fails_on_commands_missing_for_the_integration(self, project):
        register(
            project,
            "presets",
            "a",
            version="1.0.0",
            registered_commands={"copilot": ["speckit.plan"]},
        )
        with pytest.raises(
            CheckFailed, match="not registered for claude: speckit.plan"
        ):
            self.check(project).verify()


HOOKS = {"after_tasks": {"command": "speckit.opsmill.summary"}}


class TestHooksRegistered:
    def test_fails_when_another_extension_holds_the_hook(self, project):
        write(
            project.path / ".specify" / "extensions.yml",
            "hooks:\n  after_tasks:\n    - extension: other\n      command: speckit.opsmill.summary\n",
        )
        with pytest.raises(
            CheckFailed, match="hook after_tasks -> speckit.opsmill.summary"
        ):
            HooksRegistered(project, "opsmill", HOOKS).verify()


class TestOwnFiles:
    def test_finds_foreign_paths_at_any_depth(self, tmp_path):
        write(tmp_path / "installed" / "presets" / "a" / "preset.yml", "")
        write(tmp_path / "installed" / ".github" / "workflows" / "ci.yml", "")
        check = OwnFiles("opsmill", tmp_path / "src", tmp_path / "installed")
        with pytest.raises(
            CheckFailed, match=r"installed: \.github, presets/a/preset\.yml$"
        ):
            check.verify()

    def test_applies_extensionignore(self, tmp_path):
        write(tmp_path / "src" / ".extensionignore", "docs/\n")
        write(tmp_path / "installed" / "docs" / "a.md", "")
        check = OwnFiles("opsmill", tmp_path / "src", tmp_path / "installed")
        with pytest.raises(CheckFailed, match=r"installed: docs$"):
            check.verify()


class TestOverride:
    source_text = (
        "---\ndescription: a line in the front matter that is long enough\n---\n"
        "This is the first line of the preset's own text.\n"
        "Run {SCRIPT} with $ARGUMENTS, which spec-kit rewrites on install.\n"
        "Read `/memory/constitution.md`, a path that spec-kit rewrites too.\n"
        "short line\n"
        "This is the second line of the preset's own text.\n"
    )

    def override(self, project, tmp_path) -> Override:
        source = write(tmp_path / "preset" / "plan.md", self.source_text)
        return Override(project, "a", "speckit.plan", source)

    def test_fails_with_the_first_missing_line(self, project, tmp_path):
        write(
            project.path / ".claude" / "commands" / "speckit.plan.md",
            "This is the second line of the preset's own text.\n",
        )
        with pytest.raises(
            CheckFailed, match=r"1 of 2 lines missing, first: \"This is the first"
        ):
            self.override(project, tmp_path).verify()

    def test_fails_when_no_line_can_be_checked(self, project, tmp_path):
        source = write(tmp_path / "preset" / "plan.md", "Run {SCRIPT}\nshort line\n")
        write(project.path / ".claude" / "commands" / "speckit.plan.md", "anything\n")
        with pytest.raises(CheckFailed, match="no line of the preset can be checked"):
            Override(project, "a", "speckit.plan", source).verify()

    def test_probes_skip_front_matter_rewritten_and_short_lines(
        self, project, tmp_path
    ):
        assert self.override(project, tmp_path).probes() == [
            "This is the first line of the preset's own text.",
            "This is the second line of the preset's own text.",
        ]


class TestScriptsExist:
    def skill(self, project, text: str) -> None:
        write(
            project.path
            / ".claude"
            / "skills"
            / "speckit-opsmill-summary"
            / "SKILL.md",
            text,
        )

    def check(self, project) -> ScriptsExist:
        return ScriptsExist(project, "opsmill", ("speckit.opsmill.summary",))

    def test_fails_on_a_script_resolved_inside_the_extension(self, project):
        self.skill(
            project,
            "Run `.specify/extensions/opsmill/scripts/bash/check-prerequisites.sh --json`.\n",
        )
        with pytest.raises(
            CheckFailed,
            match=r"do not exist: \.specify/extensions/opsmill/scripts/bash/check-prerequisites\.sh \(speckit\.opsmill\.summary\)",
        ):
            self.check(project).verify()

    def test_fails_on_a_missing_script_outside_specify(self, project):
        self.skill(project, "Run `scripts/bash/check-prerequisites.sh --json`.\n")
        with pytest.raises(
            CheckFailed, match=r"do not exist: scripts/bash/check-prerequisites\.sh"
        ):
            self.check(project).verify()

    def test_fails_when_a_command_that_declares_scripts_runs_none(self, project):
        self.skill(project, "Find the feature directory yourself.\n")
        check = ScriptsExist(
            project,
            "opsmill",
            ("speckit.opsmill.summary",),
            ("speckit.opsmill.summary",),
        )
        with pytest.raises(CheckFailed, match="declares scripts but runs none"):
            check.verify()

    def test_fails_on_an_unresolved_placeholder(self, project):
        self.skill(project, "Run `{SCRIPT}` from repo root.\n")
        with pytest.raises(
            CheckFailed, match=r"still holds the \{SCRIPT\} placeholder"
        ):
            self.check(project).verify()


class TestPlanSetup:
    # A stand-in for spec-kit's setup-plan.sh that, like spec-kit 1.2, needs a
    # Python with PyYAML to read the preset manifests.
    SCRIPT = """\
"$SPECKIT_PYTHON_EXECUTABLE" -c "import yaml" 2>/dev/null || { echo "PyYAML is required" >&2; exit 2; }
echo "# Plan" > "specs/$SPECIFY_FEATURE/plan.md"
"""

    def test_passes_with_a_python_that_has_the_packages(self, project, tmp_path):
        write(
            project.path / ".specify" / "scripts" / "bash" / "setup-plan.sh",
            self.SCRIPT,
        )
        python = write(tmp_path / "python", "#!/bin/sh\nexit 0\n")
        python.chmod(0o755)
        assert "composes the plan template" in PlanSetup(project, python).verify()

    def test_fails_with_the_script_output(self, project, tmp_path):
        write(
            project.path / ".specify" / "scripts" / "bash" / "setup-plan.sh",
            self.SCRIPT,
        )
        python = write(tmp_path / "python", "#!/bin/sh\nexit 1\n")
        python.chmod(0o755)
        with pytest.raises(CheckFailed, match="exit 2\\):\\nPyYAML is required"):
            PlanSetup(project, python).verify()
