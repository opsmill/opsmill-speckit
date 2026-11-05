from dataclasses import dataclass, field
from pathlib import Path

from support import write

from install_check.checks import HooksRegistered
from install_check.components import ExtensionInstall, RemoteExtension
from install_check.project import Project
from repo.components import Extension

EXTENSION = """\
extension:
  id: opsmill
  version: 1.3.2
"""


class TestExtensionInstall:
    def test_checks_hooks_when_the_manifest_declares_some(self, tmp_path, project):
        hooks = "hooks:\n  after_tasks:\n    command: speckit.opsmill.summary\n"
        manifest = write(tmp_path / "src" / "extension.yml", EXTENSION + hooks)
        hooks_check = HooksRegistered(
            project, "opsmill", {"after_tasks": {"command": "speckit.opsmill.summary"}}
        )
        extension = Extension(tmp_path / "src", manifest)
        assert hooks_check in ExtensionInstall(extension).checks(project)


@dataclass
class RecordingSpecify:
    """A specify that records its arguments."""

    calls: list = field(default_factory=list)

    def run(self, cwd: Path, *args: str, confirm: bool = False) -> str:
        self.calls.append(args)
        return ""


class TestRemoteExtension:
    def test_installs_a_bundled_extension_without_a_url(self, project):
        specify = RecordingSpecify()
        RemoteExtension("git", None).install(Project(project.path, specify))
        assert specify.calls == [("extension", "add", "git")]
