import json

import pytest
from support import write

from install_check.checks import HooksRegistered, Override, OwnFiles, Registered
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
