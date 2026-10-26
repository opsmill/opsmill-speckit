from support import write

from install_check.checks import HooksRegistered
from install_check.components import Extension

EXTENSION = """\
extension:
  id: opsmill
  version: 1.3.2
"""


class TestExtension:
    def test_checks_hooks_when_the_manifest_declares_some(self, tmp_path, project):
        hooks = "hooks:\n  after_tasks:\n    command: speckit.opsmill.summary\n"
        write(tmp_path / "src" / "extension.yml", EXTENSION + hooks)
        hooks_check = HooksRegistered(
            project, "opsmill", {"after_tasks": {"command": "speckit.opsmill.summary"}}
        )
        assert hooks_check in Extension(tmp_path / "src").install(project)
